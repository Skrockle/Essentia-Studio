import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from threading import Event, RLock

from essentia_studio.analysis.cuda_pipeline import CudaInferencePipeline, CudaPipelineSettings
from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.analysis.worker import (
    analyze_in_worker,
    analyze_prepared_batch_in_worker,
    initialize_worker,
)
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
        cpu_workers: int | None = None,
        gpu_batch_size: int = 1,
        gpu_queue_size: int = 8,
    ) -> None:
        self._inventory = EssentiaBackend(model_dir, image_variant)
        self._model_dir = model_dir
        self._compute = compute
        self._worker_count = worker_count
        self._cpu_workers = cpu_workers or worker_count
        self._gpu_batch_size = gpu_batch_size
        self._gpu_queue_size = gpu_queue_size
        self._available_compute = available_compute or ["cpu"]
        self._executor: ProcessPoolExecutor | None = None
        self._pipeline: CudaInferencePipeline | None = None
        self.cuda_oom_fallbacks = 0
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
        if self._compute == "cuda":
            return self._get_pipeline().analyze(path, options, cancellation)
        result = self._get_executor().submit(analyze_in_worker, str(path), options).result()
        if cancellation is not None and cancellation.is_set():
            raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
        return result

    def cancel(self) -> None:
        with self._lock:
            pipeline = self._pipeline
            self._pipeline = None
            executor = self._executor
            self._executor = None
        if pipeline is not None:
            pipeline.cancel()
        if executor is None:
            return
        for process in getattr(executor, "_processes", {}).values():
            is_alive = getattr(process, "is_alive", lambda: True)
            if is_alive():
                process.terminate()
        executor.shutdown(wait=False, cancel_futures=True)

    def close(self) -> None:
        with self._lock:
            pipeline = self._pipeline
            self._pipeline = None
            executor = self._executor
            self._executor = None
        if pipeline is not None:
            pipeline.close()
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

    def _get_pipeline(self) -> CudaInferencePipeline:
        with self._lock:
            if self._pipeline is None:
                self._pipeline = CudaInferencePipeline(
                    CudaPipelineSettings(
                        cpu_workers=self._cpu_workers,
                        batch_size=self._gpu_batch_size,
                        queue_size=self._gpu_queue_size,
                    ),
                    prepare=self._inventory.prepare,
                    infer=self._infer_batch,
                )
            return self._pipeline

    def _infer_batch(
        self,
        prepared: list[object],
        options: AnalysisOptions,
    ) -> list[AnalysisResult]:
        batch_size = len(prepared)
        while True:
            try:
                return self._get_executor().submit(
                    analyze_prepared_batch_in_worker,
                    prepared,
                    options,
                ).result()
            except Exception as error:
                if not _is_cuda_out_of_memory(error) or batch_size == 1:
                    if not _is_cuda_out_of_memory(error):
                        raise
                    raise AppError(
                        "analysis_cuda_oom",
                        "Die CUDA-Inferenz ist auch mit Batchgröße 1 zu groß für den "
                        "verfügbaren GPU-Speicher.",
                        503,
                    ) from error
                self.cuda_oom_fallbacks += 1
                batch_size = max(1, batch_size // 2)
                results: list[AnalysisResult] = []
                for start in range(0, len(prepared), batch_size):
                    results.extend(self._infer_batch(prepared[start : start + batch_size], options))
                return results

    def _get_executor(self) -> ProcessPoolExecutor:
        with self._lock:
            if self._executor is None:
                executor_options: dict[str, object] = {
                    "max_workers": 1 if self._compute == "cuda" else self._worker_count,
                    "initializer": initialize_worker,
                    "initargs": (
                        str(self._model_dir),
                        self._compute,
                        1 if self._compute == "cuda" else self._worker_count,
                    ),
                }
                if self._compute == "cuda":
                    executor_options["mp_context"] = multiprocessing.get_context("spawn")
                self._executor = ProcessPoolExecutor(**executor_options)
            return self._executor


def _is_cuda_out_of_memory(error: RuntimeError) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in ("out of memory", "resourceexhausted", "cudnn_status_not_initialized")
    )
