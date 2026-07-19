import json
from importlib.resources import files
from pathlib import Path
from threading import Event
from typing import Any

import numpy as np

from essentia_studio.analysis.genre_selection import select_genre_predictions
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
        if cancellation is not None and cancellation.is_set():
            return AnalysisResult(model_ids=[])
        models = self._load_models()
        embeddings = models["embedding"](audio)
        genres = self._predict_genres(models, embeddings, options) if options.enable_genres else []
        moods = self._predict_moods(models, embeddings, options) if options.enable_moods else []
        result = AnalysisResult(
            genres=genres,
            moods=moods,
            model_ids=[model["name"] for model in self._manifest],
        )
        if cancellation is not None and cancellation.is_set():
            return AnalysisResult(model_ids=[])
        return result

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
        activations = np.mean(models["genre"](embeddings), axis=0)
        return select_genre_predictions(
            models["genre_labels"],
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
        activations = np.mean(models["mood"](embeddings), axis=0)
        predictions = [
            Prediction(models["mood_labels"][index], float(activation))
            for index, activation in enumerate(activations)
            if activation >= options.mood_threshold
        ]
        return sorted(predictions, key=lambda value: value.confidence, reverse=True)[:5]
