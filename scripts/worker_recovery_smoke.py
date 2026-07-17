"""Verify bounded process-pool recovery inside a production image."""

from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

from essentia_studio.analysis.pool_manager import WorkerPoolManager
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.schemas.settings import AnalysisSettings


class SmokeBackend:
    def __init__(self, should_crash: bool):
        self._should_crash = should_crash

    def analyze(self, _path: Path, _options: AnalysisOptions) -> AnalysisResult:
        if self._should_crash:
            raise BrokenProcessPool("intentional smoke failure")
        return AnalysisResult(model_ids=["recovered"])

    def close(self) -> None:
        pass

    def model_inventory(self) -> list[dict[str, str]]:
        return []

    def available_compute(self) -> list[str]:
        return ["cpu"]


def main() -> int:
    generation = 0

    def factory(_settings: AnalysisSettings) -> SmokeBackend:
        nonlocal generation
        generation += 1
        return SmokeBackend(should_crash=generation == 1)

    manager = WorkerPoolManager(factory, AnalysisSettings(workers=1))
    result = manager.analyze(Path("smoke.wav"), AnalysisOptions())
    if result.model_ids != ["recovered"] or generation != 2:
        raise RuntimeError("Analysis worker recovery smoke failed")
    print("Analysis worker recovery smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
