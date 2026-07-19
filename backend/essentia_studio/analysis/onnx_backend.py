from __future__ import annotations

import json
from pathlib import Path
from threading import Event
from typing import Any

import numpy as np

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


class OnnxBackend(EssentiaBackend):
    """EffNet inference through ONNX Runtime with Essentia-compatible features."""

    def __init__(self, model_dir: Path, image_variant: str = "cuda") -> None:
        super().__init__(model_dir, image_variant)
        self._manifest = json.loads(
            (model_dir / "onnx-models.json").read_text(encoding="utf-8")
        )

    def _load_models(self) -> dict[str, Any]:
        if self._loaded is not None:
            return self._loaded

        import essentia
        import onnxruntime as ort

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if self._image_variant != "cuda":
            providers = ["CPUExecutionProvider"]
        from essentia.standard import (
            FrameGenerator,
            MonoLoader,
            TensorflowInputMusiCNN,
            TensorflowPredict2D,
        )

        essentia.log.warningActive = False
        self._loaded = {
            "embedding": ort.InferenceSession(
                str(self._model_dir / "discogs-effnet-bsdynamic-1.onnx"),
                providers=providers,
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
            "FrameGenerator": FrameGenerator,
            "MonoLoader": MonoLoader,
            "TensorflowInputMusiCNN": TensorflowInputMusiCNN,
            "genre_labels": self._read_labels("genre_discogs400-discogs-effnet-1.json"),
            "mood_labels": self._read_labels(
                "mtg_jamendo_moodtheme-discogs-effnet-1.json"
            ),
        }
        return self._loaded

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
        feature_batches = [self._features(audio, models) for audio in audio_batch]
        lengths = [len(features) for features in feature_batches]
        all_features = np.concatenate(feature_batches, axis=0)
        embeddings = self._run_embedding(models["embedding"], all_features)
        genre_predictions = self._predict_genre_batch(
            models, embeddings, lengths, options
        )
        mood_predictions = self._predict_mood_batch(
            models, embeddings, lengths, options
        )
        results = []
        for genre_output, mood_output in zip(genre_predictions, mood_predictions, strict=True):
            genres = genre_output if options.enable_genres else []
            moods = mood_output if options.enable_moods else []
            results.append(
                AnalysisResult(
                    genres=genres,
                    moods=moods,
                    model_ids=[model["name"] for model in self._manifest],
                )
            )
        return results

    @staticmethod
    def _run_embedding(session: Any, features: np.ndarray) -> np.ndarray:
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: features.astype(np.float32)})
        embedding = next(output for output in outputs if output.shape[-1] == 1280)
        return np.asarray(embedding)

    def _features(self, audio: Any, models: dict[str, Any]) -> np.ndarray:
        input_extractor = models["TensorflowInputMusiCNN"]()
        bands = [
            input_extractor(frame).bands
            for frame in models["FrameGenerator"](audio, 512, 256)
        ]
        if not bands:
            return np.zeros((1, 128, 96), dtype=np.float32)
        mel_spectrogram = np.asarray(bands, dtype=np.float32)
        patches = [
            mel_spectrogram[start : start + 128]
            for start in range(0, max(1, len(mel_spectrogram) - 127), 62)
        ]
        if len(mel_spectrogram) < 128:
            padding = np.zeros((128 - len(mel_spectrogram), 96), dtype=np.float32)
            patches = [np.concatenate((mel_spectrogram, padding), axis=0)]
        elif len(patches[-1]) < 128:
            patches[-1] = np.pad(patches[-1], ((0, 128 - len(patches[-1])), (0, 0)))
        return np.asarray(patches, dtype=np.float32)
