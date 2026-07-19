from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import CancelledError, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Semaphore, Thread
from typing import Any

from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.errors import AppError

PreparedAnalysisInput = Any
PrepareAnalysisInput = Callable[[Path, AnalysisOptions], PreparedAnalysisInput]
InferBatch = Callable[[list[PreparedAnalysisInput], AnalysisOptions], list[AnalysisResult]]


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
    prepared: PreparedAnalysisInput | None
    options: AnalysisOptions
    cancellation: Event | None
    completed: Event
    result: AnalysisResult | None = None
    error: BaseException | None = None
    queue_slot_held: bool = False
    lock: Lock = field(default_factory=Lock)


class CudaInferencePipeline:
    def __init__(
        self,
        settings: CudaPipelineSettings,
        *,
        prepare: PrepareAnalysisInput,
        infer: InferBatch,
    ) -> None:
        self.settings = settings
        self._prepare = prepare
        self._infer = infer
        self._requests: Queue[_Request | None] = Queue()
        self._preparation_slots = Semaphore(settings.cpu_workers)
        self._queue_slots = Semaphore(settings.queue_size)
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

        request = self._prepare_request(path, options, cancellation)
        while not request.completed.wait(timeout=0.1):
            interruption = self._interruption_error(cancellation)
            if interruption is not None:
                self._finish(request, error=interruption)
        if request.error is not None:
            raise request.error
        if request.result is None:
            raise AppError(
                "analysis_pipeline_failed",
                "Die CUDA-Analyse lieferte kein Ergebnis.",
                500,
            )
        return request.result

    def _prepare_request(
        self,
        path: Path,
        options: AnalysisOptions,
        cancellation: Event | None,
    ) -> _Request:
        self._acquire_capacity(self._preparation_slots, cancellation)
        release_preparation = True
        try:
            future = self._preprocessors.submit(self._prepare, path, options)
            while True:
                try:
                    prepared = future.result(timeout=0.1)
                    break
                except CancelledError:
                    raise self._cancelled_future_error(cancellation) from None
                except FutureTimeoutError:
                    interruption = self._interruption_error(cancellation)
                    if interruption is None:
                        continue
                    if not future.cancel():
                        future.add_done_callback(
                            lambda _future: self._preparation_slots.release()
                        )
                        release_preparation = False
                    raise interruption from None
            request = _Request(prepared, options, cancellation, Event())
            self._enqueue(request)
            return request
        finally:
            if release_preparation:
                self._preparation_slots.release()

    def close(self) -> None:
        self._stop(wait_for_preparation=True)

    def cancel(self) -> None:
        self._stop(wait_for_preparation=False)

    def _stop(self, *, wait_for_preparation: bool) -> None:
        if self._stopped.is_set():
            return
        self._stopped.set()
        self._cancel_queued()
        self._dispatcher.join(timeout=5)
        self._preprocessors.shutdown(
            wait=wait_for_preparation,
            cancel_futures=True,
        )

    def _enqueue(self, request: _Request) -> None:
        self._acquire_capacity(self._queue_slots, request.cancellation)
        enqueued = False
        try:
            interruption = self._interruption_error(request.cancellation)
            if interruption is not None:
                raise interruption
            with request.lock:
                request.queue_slot_held = True
            self._requests.put(request)
            enqueued = True
            if self._stopped.is_set():
                self._cancel_queued()
        finally:
            if not enqueued:
                self._queue_slots.release()

    def _acquire_capacity(
        self,
        capacity: Semaphore,
        cancellation: Event | None,
    ) -> None:
        while True:
            interruption = self._interruption_error(cancellation)
            if interruption is not None:
                raise interruption
            if not capacity.acquire(timeout=0.1):
                continue
            interruption = self._interruption_error(cancellation)
            if interruption is not None:
                capacity.release()
                raise interruption
            return

    def _interruption_error(self, cancellation: Event | None) -> AppError | None:
        if cancellation is not None and cancellation.is_set():
            return self._cancellation_error()
        if self._stopped.is_set():
            return AppError(
                "analysis_pipeline_stopped",
                "Die CUDA-Analysepipeline wurde beendet.",
                503,
            )
        return None

    def _cancelled_future_error(self, cancellation: Event | None) -> AppError:
        interruption = self._interruption_error(cancellation)
        if interruption is not None:
            return interruption
        return AppError(
            "analysis_pipeline_stopped",
            "Die CUDA-Analysepipeline wurde beendet.",
            503,
        )

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
        if request is None:
            return _STOP
        self._release_queue_slot(request)
        return request

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
            self._release_queue_slot(request)
            batch.append(request)
        return batch

    def _process_batch(self, batch: list[_Request]) -> None:
        active = self._active_dispatches(batch)
        if not active:
            for request in batch:
                self._finish(request, error=self._cancellation_error())
            return
        try:
            prepared = [value for _request, value in active]
            results = self._infer(prepared, active[0][0].options)
            if len(results) != len(active):
                raise RuntimeError("CUDA-Inferenz lieferte eine inkonsistente Batchgröße.")
            self._finish_batch(batch, active, results)
        except BaseException as error:
            for request in batch:
                request_error = self._cancellation_error() if self._cancelled(request) else error
                self._finish(request, error=request_error)

    def _active_dispatches(
        self, batch: list[_Request]
    ) -> list[tuple[_Request, PreparedAnalysisInput]]:
        active = []
        for request in batch:
            dispatch = self._start_dispatch(request)
            if dispatch is not None:
                active.append(dispatch)
        return active

    def _finish_batch(
        self,
        batch: list[_Request],
        active: list[tuple[_Request, PreparedAnalysisInput]],
        results: list[AnalysisResult],
    ) -> None:
        for (request, _prepared), result in zip(active, results, strict=True):
            self._finish(request, result=result)
        active_ids = {id(request) for request, _prepared in active}
        for request in batch:
            if id(request) not in active_ids:
                self._finish(request, error=self._cancellation_error())

    def _finish(
        self,
        request: _Request,
        *,
        result: AnalysisResult | None = None,
        error: BaseException | None = None,
    ) -> None:
        release_queue_slot = False
        with request.lock:
            if request.completed.is_set():
                return
            request.result = result
            request.error = error
            request.prepared = None
            if request.queue_slot_held:
                request.queue_slot_held = False
                release_queue_slot = True
            request.completed.set()
        if release_queue_slot:
            self._queue_slots.release()

    def _release_queue_slot(self, request: _Request) -> None:
        release_queue_slot = False
        with request.lock:
            if request.queue_slot_held:
                request.queue_slot_held = False
                release_queue_slot = True
        if release_queue_slot:
            self._queue_slots.release()

    def _start_dispatch(
        self, request: _Request
    ) -> tuple[_Request, PreparedAnalysisInput] | None:
        with request.lock:
            if request.completed.is_set() or self._cancelled(request):
                return None
            return request, request.prepared

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
