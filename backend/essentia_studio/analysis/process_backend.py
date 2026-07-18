from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from threading import Event, RLock

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.analysis.worker import analyze_in_worker, initialize_worker
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.errors import AppError


class ProcessAnalysisBackend:
    def __init__(
        self,
        model_dir: Path,
        compute: str,
        worker_count: int,
        image_variant: str,
        available_compute: list[str] | None = None,
    ) -> None:
        self._inventory = EssentiaBackend(model_dir, image_variant)
        self._model_dir = model_dir
        self._compute = compute
        self._worker_count = worker_count
        self._available_compute = available_compute or ["cpu"]
        self._executor: ProcessPoolExecutor | None = None
        self._lock = RLock()

    def model_inventory(self) -> list[dict[str, str]]:
        return self._inventory.model_inventory()

    def available_compute(self) -> list[str]:
        return self._available_compute.copy()

    def analyze(
        self,
        path: Path,
        options: AnalysisOptions,
        cancellation: Event | None = None,
    ) -> AnalysisResult:
        if cancellation is not None and cancellation.is_set():
            raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
        result = self._get_executor().submit(analyze_in_worker, str(path), options).result()
        if cancellation is not None and cancellation.is_set():
            raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
        return result

    def cancel(self) -> None:
        with self._lock:
            executor = self._executor
            self._executor = None
        if executor is None:
            return
        for process in getattr(executor, "_processes", {}).values():
            is_alive = getattr(process, "is_alive", lambda: True)
            if is_alive():
                process.terminate()
        executor.shutdown(wait=False, cancel_futures=True)

    def close(self) -> None:
        with self._lock:
            executor = self._executor
            self._executor = None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

    def _get_executor(self) -> ProcessPoolExecutor:
        with self._lock:
            if self._executor is None:
                self._executor = ProcessPoolExecutor(
                    max_workers=self._worker_count,
                    initializer=initialize_worker,
                    initargs=(str(self._model_dir), self._compute, self._worker_count),
                )
            return self._executor
