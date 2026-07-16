from pathlib import Path

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

    def analyze(self, path: Path, options: AnalysisOptions) -> AnalysisResult:
        genres = [Prediction("Electronic---House", 0.91)] if options.enable_genres else []
        moods = [Prediction("moodtheme---happy", 0.84)] if options.enable_moods else []
        return AnalysisResult(
            genres=genres,
            moods=moods,
            model_ids=["fake-genre", "fake-mood"],
        )
