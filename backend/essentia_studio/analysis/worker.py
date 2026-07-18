import os
from pathlib import Path

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult

_backend: EssentiaBackend | None = None


def initialize_worker(model_dir: str, compute: str, worker_count: int) -> None:
    global _backend
    cpu_count = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    threads_per_worker = max(1, ((cpu_count or 1) + worker_count - 1) // worker_count)
    for variable in (
        "TF_NUM_INTRAOP_THREADS",
        "TF_NUM_INTEROP_THREADS",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
    ):
        os.environ[variable] = str(threads_per_worker)
    os.environ["CUDA_VISIBLE_DEVICES"] = "" if compute == "cpu" else os.environ.get(
        "CUDA_VISIBLE_DEVICES", "0"
    )
    _backend = EssentiaBackend(Path(model_dir), "cuda" if compute == "cuda" else "cpu")


def analyze_in_worker(path: str, options: AnalysisOptions) -> AnalysisResult:
    if _backend is None:
        raise RuntimeError("Analysis worker is not initialized")
    return _backend.analyze(Path(path), options)
