from pathlib import Path
from threading import Event

from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult, Prediction


class FakeAnalysisBackend:
    """Deterministic backend for API, browser, and container workflow tests."""

    def model_inventory(self) -> list[dict[str, str]]:
        return [
            {"name": "fake-genre", "role": "genre", "status": "ready"},
            {"name": "fake-mood", "role": "mood", "status": "ready"},
        ]

    def available_compute(self) -> list[str]:
        return ["cpu"]

    def analyze(
        self,
        path: Path,
        options: AnalysisOptions,
        cancellation: Event | None = None,
    ) -> AnalysisResult:
        genres = self._genres(path) if options.enable_genres else []
        moods = [Prediction("moodtheme---happy", 0.84)] if options.enable_moods else []
        return AnalysisResult(
            genres=genres,
            moods=moods,
            model_ids=["fake-genre", "fake-mood"],
        )

    @staticmethod
    def _genres(path: Path) -> list[Prediction]:
        if path.stem == "uncertain":
            return [Prediction("Rock---Alternative Rock", 0.116, accepted=False)]
        return [Prediction("Electronic---House", 0.91)]
