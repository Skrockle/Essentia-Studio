import json
from importlib.resources import files
from pathlib import Path
from threading import Event
from typing import Any

import numpy as np

from essentia_studio.analysis.genre_selection import select_genre_predictions
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult, Prediction

_CLASSIFICATION_CHUNK_SIZE = 16


class EssentiaBackend:
    def __init__(self, model_dir: Path, image_variant: str = "cpu") -> None:
        self._model_dir = model_dir
        self._image_variant = image_variant
        self._manifest = json.loads(
            files("essentia_studio.analysis").joinpath("models.json").read_text(encoding="utf-8")
        )
        self._loaded: dict[str, Any] | None = None

    def model_inventory(self) -> list[dict[str, str]]:
        return [
            {
                "name": model["name"],
                "role": model["role"],
                "sha256": model["sha256"],
                "status": "ready" if (self._model_dir / model["name"]).is_file() else "missing",
            }
            for model in self._manifest
        ]

    def available_compute(self) -> list[str]:
        return ["cpu", "cuda"] if self._image_variant == "cuda" else ["cpu"]

    def initialize(self) -> None:
        self._load_models()

    def analyze(
        self,
        path: Path,
        options: AnalysisOptions,
        cancellation: Event | None = None,
    ) -> AnalysisResult:
        if cancellation is not None and cancellation.is_set():
            return AnalysisResult(model_ids=[])
        audio = self.prepare(path, options)
        result = self.analyze_prepared(audio, options, cancellation)
        return result

    def prepare(self, path: Path, options: AnalysisOptions) -> Any:
        audio = self._load_audio_loader()(
            filename=str(path),
            sampleRate=16000,
            resampleQuality=1,
        )()
        max_samples = options.max_audio_seconds * 16000
        return audio[:max_samples]

    def analyze_prepared(
        self,
        audio: Any,
        options: AnalysisOptions,
        cancellation: Event | None = None,
    ) -> AnalysisResult:
        return self.analyze_prepared_batch([audio], options, cancellation)[0]

    def analyze_prepared_batch(
        self,
        audio_batch: list[Any],
        options: AnalysisOptions,
        cancellation: Event | None = None,
    ) -> list[AnalysisResult]:
        if not audio_batch:
            return []
        if cancellation is not None and cancellation.is_set():
            return [AnalysisResult(model_ids=[]) for _ in audio_batch]
        models = self._load_models()
        embeddings = [models["embedding"](audio) for audio in audio_batch]
        lengths = [len(embedding) for embedding in embeddings]
        combined_embeddings = np.concatenate(embeddings, axis=0)
        genre_predictions = self._predict_genre_batch(
            models, combined_embeddings, lengths, options
        )
        mood_predictions = self._predict_mood_batch(
            models, combined_embeddings, lengths, options
        )
        model_ids = [model["name"] for model in self._manifest]
        results = [
            AnalysisResult(genres=genres, moods=moods, model_ids=model_ids.copy())
            for genres, moods in zip(genre_predictions, mood_predictions, strict=True)
        ]
        if cancellation is not None and cancellation.is_set():
            return [AnalysisResult(model_ids=[]) for _ in audio_batch]
        return results

    def _predict_genre_batch(
        self,
        models: dict[str, Any],
        embeddings: Any,
        lengths: list[int],
        options: AnalysisOptions,
    ) -> list[list[Prediction]]:
        if not options.enable_genres:
            return [[] for _ in lengths]
        predictions = _predict_in_chunks(models["genre"], embeddings)
        return [
            self._select_genres(models["genre_labels"], predictions[start:end], options)
            for start, end in _ranges(lengths)
        ]

    def _predict_mood_batch(
        self,
        models: dict[str, Any],
        embeddings: Any,
        lengths: list[int],
        options: AnalysisOptions,
    ) -> list[list[Prediction]]:
        if not options.enable_moods:
            return [[] for _ in lengths]
        predictions = _predict_in_chunks(models["mood"], embeddings)
        return [
            self._select_moods(models["mood_labels"], predictions[start:end], options)
            for start, end in _ranges(lengths)
        ]

    def _load_audio_loader(self) -> Any:
        import essentia
        from essentia.standard import MonoLoader

        essentia.log.warningActive = False
        return MonoLoader

    def _load_models(self) -> dict[str, Any]:
        if self._loaded is not None:
            return self._loaded

        import essentia
        from essentia.standard import (
            MonoLoader,
            TensorflowPredict2D,
            TensorflowPredictEffnetDiscogs,
        )

        essentia.log.warningActive = False
        self._loaded = {
            "MonoLoader": MonoLoader,
            "embedding": TensorflowPredictEffnetDiscogs(
                graphFilename=str(self._model_dir / "discogs-effnet-bs64-1.pb"),
                output="PartitionedCall:1",
            ),
            "genre": TensorflowPredict2D(
                graphFilename=str(self._model_dir / "genre_discogs400-discogs-effnet-1.pb"),
                input="serving_default_model_Placeholder",
                output="PartitionedCall",
            ),
            "mood": TensorflowPredict2D(
                graphFilename=str(
                    self._model_dir / "mtg_jamendo_moodtheme-discogs-effnet-1.pb"
                ),
                input="model/Placeholder",
                output="model/Sigmoid",
            ),
            "genre_labels": self._read_labels("genre_discogs400-discogs-effnet-1.json"),
            "mood_labels": self._read_labels(
                "mtg_jamendo_moodtheme-discogs-effnet-1.json"
            ),
        }
        return self._loaded

    def _read_labels(self, filename: str) -> list[str]:
        with (self._model_dir / filename).open(encoding="utf-8") as metadata_file:
            return json.load(metadata_file)["classes"]

    @staticmethod
    def _predict_genres(
        models: dict[str, Any],
        embeddings: Any,
        options: AnalysisOptions,
    ) -> list[Prediction]:
        return EssentiaBackend._select_genres(
            models["genre_labels"], models["genre"](embeddings), options
        )

    @staticmethod
    def _select_genres(
        labels: list[str], predictions: Any, options: AnalysisOptions
    ) -> list[Prediction]:
        activations = np.mean(predictions, axis=0)
        return select_genre_predictions(
            labels,
            activations,
            options.genre_threshold,
            options.genre_count,
        )

    @staticmethod
    def _predict_moods(
        models: dict[str, Any],
        embeddings: Any,
        options: AnalysisOptions,
    ) -> list[Prediction]:
        return EssentiaBackend._select_moods(
            models["mood_labels"], models["mood"](embeddings), options
        )

    @staticmethod
    def _select_moods(
        labels: list[str], predictions: Any, options: AnalysisOptions
    ) -> list[Prediction]:
        activations = np.mean(predictions, axis=0)
        predictions = [
            Prediction(labels[index], float(activation))
            for index, activation in enumerate(activations)
            if activation >= options.mood_threshold
        ]
        return sorted(predictions, key=lambda value: value.confidence, reverse=True)[:5]


def _ranges(lengths: list[int]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    for length in lengths:
        end = start + length
        ranges.append((start, end))
        start = end
    return ranges


def _predict_in_chunks(model: Any, embeddings: Any) -> np.ndarray:
    embedding_array = np.asarray(embeddings)
    predictions = [
        np.asarray(model(embedding_array[start : start + _CLASSIFICATION_CHUNK_SIZE]))
        for start in range(0, len(embedding_array), _CLASSIFICATION_CHUNK_SIZE)
    ]
    return np.concatenate(predictions, axis=0)
