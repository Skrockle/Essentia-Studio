import os
from pathlib import Path

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult

_backend: EssentiaBackend | None = None


def initialize_worker(model_dir: str, compute: str) -> None:
    global _backend
    os.environ["CUDA_VISIBLE_DEVICES"] = "" if compute == "cpu" else os.environ.get(
        "CUDA_VISIBLE_DEVICES", "0"
    )
    _backend = EssentiaBackend(Path(model_dir), "cuda" if compute == "cuda" else "cpu")


def analyze_in_worker(path: str, options: AnalysisOptions) -> AnalysisResult:
    if _backend is None:
        raise RuntimeError("Analysis worker is not initialized")
    return _backend.analyze(Path(path), options)
