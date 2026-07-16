from pathlib import Path
from typing import Protocol

from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


class AnalysisBackend(Protocol):
    def model_inventory(self) -> list[dict[str, str]]: ...

    def available_compute(self) -> list[str]: ...

    def analyze(self, path: Path, options: AnalysisOptions) -> AnalysisResult: ...
