import json
from importlib.resources import files
from pathlib import Path
from typing import Any

import numpy as np

from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult, Prediction


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

    def analyze(self, path: Path, options: AnalysisOptions) -> AnalysisResult:
        models = self._load_models()
        audio = models["MonoLoader"](
            filename=str(path),
            sampleRate=16000,
            resampleQuality=1,
        )()
        max_samples = options.max_audio_seconds * 16000
        embeddings = models["embedding"](audio[:max_samples])
        genres = self._predict_genres(models, embeddings, options) if options.enable_genres else []
        moods = self._predict_moods(models, embeddings, options) if options.enable_moods else []
        return AnalysisResult(
            genres=genres,
            moods=moods,
            model_ids=[model["name"] for model in self._manifest],
        )

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
        activations = np.mean(models["genre"](embeddings), axis=0)
        top_indices = np.argsort(activations)[::-1][: options.genre_count * 2]
        predictions = [
            Prediction(models["genre_labels"][index], float(activations[index]))
            for index in top_indices
            if activations[index] >= options.genre_threshold
        ][: options.genre_count]
        if predictions:
            return predictions
        top_index = int(np.argmax(activations))
        return [Prediction(models["genre_labels"][top_index], float(activations[top_index]))]

    @staticmethod
    def _predict_moods(
        models: dict[str, Any],
        embeddings: Any,
        options: AnalysisOptions,
    ) -> list[Prediction]:
        activations = np.mean(models["mood"](embeddings), axis=0)
        predictions = [
            Prediction(models["mood_labels"][index], float(activation))
            for index, activation in enumerate(activations)
            if activation >= options.mood_threshold
        ]
        return sorted(predictions, key=lambda value: value.confidence, reverse=True)[:5]
