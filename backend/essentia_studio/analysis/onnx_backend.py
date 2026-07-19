from __future__ import annotations

import json
from pathlib import Path
from threading import Event
from typing import Any

import numpy as np

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


class OnnxBackend(EssentiaBackend):
    """CPU feature preparation and batched EffNet inference through ONNX Runtime."""

    def __init__(self, model_dir: Path, image_variant: str = "cuda") -> None:
        super().__init__(model_dir, image_variant)
        self._manifest = json.loads(
            (model_dir / "onnx-models.json").read_text(encoding="utf-8")
        )

    def prepare(self, path: Path, options: AnalysisOptions) -> np.ndarray:
        audio = super().prepare(path, options)
        return self._features(audio)

    def _load_models(self) -> dict[str, Any]:
        if self._loaded is not None:
            return self._loaded

        import onnxruntime as ort

        effnet_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if self._image_variant != "cuda":
            effnet_providers = ["CPUExecutionProvider"]
        self._loaded = {
            "effnet": ort.InferenceSession(
                str(self._model_dir / "discogs-effnet-bsdynamic-1.onnx"),
                providers=effnet_providers,
            ),
            "mood": ort.InferenceSession(
                str(
                    self._model_dir
                    / "mtg_jamendo_moodtheme-discogs-effnet-1.onnx"
                ),
                providers=["CPUExecutionProvider"],
            ),
            "genre_labels": self._read_labels(
                "genre_discogs400-discogs-effnet-1.json"
            ),
            "mood_labels": self._read_labels(
                "mtg_jamendo_moodtheme-discogs-effnet-1.json"
            ),
        }
        return self._loaded

    def analyze_prepared_batch(
        self,
        feature_batches: list[Any],
        options: AnalysisOptions,
        cancellation: Event | None = None,
    ) -> list[AnalysisResult]:
        if not feature_batches:
            return []
        if cancellation is not None and cancellation.is_set():
            return [AnalysisResult(model_ids=[]) for _ in feature_batches]

        models = self._load_models()
        lengths = [len(features) for features in feature_batches]
        all_features = np.concatenate(feature_batches, axis=0)
        genre_scores, embeddings = self._run_effnet(models["effnet"], all_features)
        genres = self._select_genre_batch(
            models["genre_labels"], genre_scores, lengths, options
        )
        moods = self._select_mood_batch(models, embeddings, lengths, options)
        model_ids = [model["name"] for model in self._manifest]
        results = [
            AnalysisResult(
                genres=title_genres,
                moods=title_moods,
                model_ids=model_ids.copy(),
            )
            for title_genres, title_moods in zip(genres, moods, strict=True)
        ]
        if cancellation is not None and cancellation.is_set():
            return [AnalysisResult(model_ids=[]) for _ in feature_batches]
        return results

    @staticmethod
    def _run_effnet(
        session: Any, features: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: features.astype(np.float32)})
        genre_scores = next(output for output in outputs if output.shape[-1] == 400)
        embeddings = next(output for output in outputs if output.shape[-1] == 1280)
        return np.asarray(genre_scores), np.asarray(embeddings)

    @staticmethod
    def _run_onnx(session: Any, inputs: np.ndarray) -> np.ndarray:
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: inputs.astype(np.float32)})
        return np.asarray(outputs[0])

    def _select_genre_batch(
        self,
        labels: list[str],
        scores: np.ndarray,
        lengths: list[int],
        options: AnalysisOptions,
    ) -> list[list[Any]]:
        if not options.enable_genres:
            return [[] for _ in lengths]
        return [
            self._select_genres(labels, scores[start:end], options)
            for start, end in _ranges(lengths)
        ]

    def _select_mood_batch(
        self,
        models: dict[str, Any],
        embeddings: np.ndarray,
        lengths: list[int],
        options: AnalysisOptions,
    ) -> list[list[Any]]:
        if not options.enable_moods:
            return [[] for _ in lengths]
        scores = self._run_onnx(models["mood"], embeddings)
        return [
            self._select_moods(models["mood_labels"], scores[start:end], options)
            for start, end in _ranges(lengths)
        ]

    def _features(self, audio: Any) -> np.ndarray:
        frame_generator, input_type = self._load_feature_algorithms()
        input_extractor = input_type()
        bands = [
            np.asarray(input_extractor(frame), dtype=np.float32)
            for frame in frame_generator(audio, 512, 256)
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
            patches[-1] = np.pad(
                patches[-1], ((0, 128 - len(patches[-1])), (0, 0))
            )
        return np.asarray(patches, dtype=np.float32)

    @staticmethod
    def _load_feature_algorithms() -> tuple[Any, Any]:
        import essentia
        from essentia.standard import FrameGenerator, TensorflowInputMusiCNN

        essentia.log.warningActive = False
        return FrameGenerator, TensorflowInputMusiCNN


def _ranges(lengths: list[int]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    for length in lengths:
        end = start + length
        ranges.append((start, end))
        start = end
    return ranges
