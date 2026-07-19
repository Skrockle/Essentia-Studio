from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Semaphore, Thread
from typing import Any

from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.errors import AppError

PreparedAudio = Any
PrepareAudio = Callable[[Path, AnalysisOptions], PreparedAudio]
InferBatch = Callable[[list[PreparedAudio], AnalysisOptions], list[AnalysisResult]]


@dataclass(frozen=True, slots=True)
class CudaPipelineSettings:
    cpu_workers: int
    batch_size: int
    queue_size: int

    def __post_init__(self) -> None:
        if self.cpu_workers < 1:
            raise ValueError("CPU-Worker müssen mindestens 1 sein.")
        if self.batch_size not in {1, 2, 4, 8}:
            raise ValueError("Batchgröße muss 1, 2, 4 oder 8 sein.")
        if self.queue_size < 1:
            raise ValueError("Die CUDA-Queue muss mindestens ein Element aufnehmen.")


@dataclass(slots=True)
class _Request:
    prepared: PreparedAudio
    options: AnalysisOptions
    cancellation: Event | None
    completed: Event
    result: AnalysisResult | None = None
    error: BaseException | None = None


class CudaInferencePipeline:
    def __init__(
        self,
        settings: CudaPipelineSettings,
        *,
        prepare: PrepareAudio,
        infer: InferBatch,
    ) -> None:
        self.settings = settings
        self._prepare = prepare
        self._infer = infer
        self._requests: Queue[_Request | None] = Queue(maxsize=settings.queue_size)
        self._slots = Semaphore(settings.queue_size)
        self._preprocessors = ThreadPoolExecutor(
            max_workers=settings.cpu_workers,
            thread_name_prefix="essentia-cpu-preprocess",
        )
        self._stopped = Event()
        self._dispatcher = Thread(
            target=self._dispatch,
            name="essentia-cuda-dispatcher",
            daemon=True,
        )
        self._dispatcher.start()

    def analyze(
        self,
        path: Path,
        options: AnalysisOptions,
        cancellation: Event | None = None,
    ) -> AnalysisResult:
        if cancellation is not None and cancellation.is_set():
            raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
        if self._stopped.is_set():
            raise AppError(
                "analysis_pipeline_stopped",
                "Die CUDA-Analysepipeline wurde beendet.",
                503,
            )

        self._acquire_slot(cancellation)
        try:
            prepared = self._preprocessors.submit(self._prepare, path, options).result()
            request = _Request(prepared, options, cancellation, Event())
            while True:
                if cancellation is not None and cancellation.is_set():
                    raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
                try:
                    self._requests.put(request, timeout=0.1)
                    break
                except Full:
                    if self._stopped.is_set():
                        raise AppError(
                            "analysis_pipeline_stopped",
                            "Die CUDA-Analysepipeline wurde beendet.",
                            503,
                        ) from None
            request.completed.wait()
            if request.error is not None:
                raise request.error
            if request.result is None:
                raise AppError(
                    "analysis_pipeline_failed",
                    "Die CUDA-Analyse lieferte kein Ergebnis.",
                    500,
                )
            return request.result
        finally:
            if "request" not in locals() or not request.completed.is_set():
                self._slots.release()

    def close(self) -> None:
        if self._stopped.is_set():
            return
        self._stopped.set()
        self._cancel_queued()
        self._dispatcher.join(timeout=5)
        self._preprocessors.shutdown(wait=True, cancel_futures=True)

    def cancel(self) -> None:
        self.close()

    def _acquire_slot(self, cancellation: Event | None) -> None:
        while True:
            if self._stopped.is_set():
                raise AppError(
                    "analysis_pipeline_stopped",
                    "Die CUDA-Analysepipeline wurde beendet.",
                    503,
                )
            if cancellation is not None and cancellation.is_set():
                raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
            if self._slots.acquire(timeout=0.1):
                return

    def _dispatch(self) -> None:
        while not self._stopped.is_set():
            first = self._get_first_request()
            if first is None:
                continue
            if first is _STOP:
                return
            self._process_batch(self._collect_batch(first))

    def _get_first_request(self) -> _Request | object | None:
        try:
            request = self._requests.get(timeout=0.1)
        except Empty:
            return None
        return _STOP if request is None else request

    def _collect_batch(self, first: _Request) -> list[_Request]:
        batch = [first]
        while len(batch) < self.settings.batch_size:
            try:
                request = self._requests.get(timeout=0.01)
            except Empty:
                break
            if request is None:
                self._stopped.set()
                break
            batch.append(request)
        return batch

    def _process_batch(self, batch: list[_Request]) -> None:
        active = [request for request in batch if not self._cancelled(request)]
        if not active:
            for request in batch:
                self._finish(request, error=self._cancellation_error())
            return
        try:
            results = self._infer([request.prepared for request in active], active[0].options)
            if len(results) != len(active):
                raise RuntimeError("CUDA-Inferenz lieferte eine inkonsistente Batchgröße.")
            for request, result in zip(active, results, strict=True):
                self._finish(request, result=result)
            active_ids = {id(request) for request in active}
            for request in batch:
                if id(request) not in active_ids:
                    self._finish(request, error=self._cancellation_error())
        except BaseException as error:
            for request in batch:
                request_error = self._cancellation_error() if self._cancelled(request) else error
                self._finish(request, error=request_error)

    def _finish(
        self,
        request: _Request,
        *,
        result: AnalysisResult | None = None,
        error: BaseException | None = None,
    ) -> None:
        request.result = result
        request.error = error
        request.completed.set()
        self._slots.release()

    @staticmethod
    def _cancelled(request: _Request) -> bool:
        return request.cancellation is not None and request.cancellation.is_set()

    @staticmethod
    def _cancellation_error() -> AppError:
        return AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)

    def _cancel_queued(self) -> None:
        while True:
            try:
                request = self._requests.get_nowait()
            except Empty:
                return
            if request is not None:
                self._finish(
                    request,
                    error=self._cancellation_error(),
                )


_STOP = object()
