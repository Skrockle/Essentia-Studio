from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.analysis.worker import analyze_in_worker, initialize_worker
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


class ProcessAnalysisBackend:
    def __init__(
        self,
        model_dir: Path,
        compute: str,
        worker_count: int,
        image_variant: str,
    ) -> None:
        self._inventory = EssentiaBackend(model_dir, image_variant)
        self._model_dir = model_dir
        self._compute = compute
        self._worker_count = worker_count
        self._executor: ProcessPoolExecutor | None = None

    def model_inventory(self) -> list[dict[str, str]]:
        return self._inventory.model_inventory()

    def available_compute(self) -> list[str]:
        return self._inventory.available_compute()

    def analyze(self, path: Path, options: AnalysisOptions) -> AnalysisResult:
        return self._get_executor().submit(analyze_in_worker, str(path), options).result()

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)

    def _get_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=self._worker_count,
                initializer=initialize_worker,
                initargs=(str(self._model_dir), self._compute),
            )
        return self._executor
