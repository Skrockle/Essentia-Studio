from pathlib import Path

import numpy as np

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions


def test_prepared_batch_runs_genre_and_mood_heads_once_per_batch() -> None:
    embedding_calls: list[object] = []
    genre_calls: list[object] = []
    mood_calls: list[object] = []

    class FakeModel:
        def __init__(self, calls: list[object], output: np.ndarray) -> None:
            self.calls = calls
            self.output = output

        def __call__(self, value):
            self.calls.append(value)
            return self.output

    backend = EssentiaBackend(Path("/models"), "cuda")
    backend._loaded = {
        "embedding": FakeModel(embedding_calls, np.ones((2, 3))),
        "genre": FakeModel(genre_calls, np.array([[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]])),
        "mood": FakeModel(mood_calls, np.array([[0.9, 0.1], [0.2, 0.8], [0.8, 0.2], [0.1, 0.9]])),
        "genre_labels": ["rock", "pop"],
        "mood_labels": ["calm", "energetic"],
    }
    options = AnalysisOptions(genre_threshold=0.5, mood_threshold=0.5, genre_count=1)

    results = backend.analyze_prepared_batch(["one", "two"], options)

    assert len(embedding_calls) == 2
    assert len(genre_calls) == 1
    assert len(mood_calls) == 1
    assert [result.genres[0].label for result in results] == ["rock", "pop"]
    assert [result.moods[0].label for result in results] == ["calm", "energetic"]
