import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from essentia_studio.analysis.onnx_backend import OnnxBackend
from essentia_studio.domain.analysis import AnalysisOptions


class _Input:
    name = "features"


class _EffnetSession:
    def __init__(self) -> None:
        self.received = None

    def get_inputs(self):
        return [_Input()]

    def run(self, _outputs, inputs):
        self.received = inputs["features"]
        patch_count = len(self.received)
        genres = np.zeros((patch_count, 400), dtype=np.float32)
        embeddings = np.ones((patch_count, 1280), dtype=np.float32)
        return [genres, embeddings]


class _MoodSession:
    def get_inputs(self):
        return [SimpleNamespace(name="embeddings")]

    def run(self, _outputs, inputs):
        embeddings = inputs["embeddings"]
        return [np.zeros((len(embeddings), 2), dtype=np.float32)]


def _write_metadata(model_dir: Path) -> None:
    (model_dir / "onnx-models.json").write_text("[]", encoding="utf-8")
    (model_dir / "genre_discogs400-discogs-effnet-1.json").write_text(
        json.dumps({"classes": [f"genre-{index}" for index in range(400)]}),
        encoding="utf-8",
    )
    (model_dir / "mtg_jamendo_moodtheme-discogs-effnet-1.json").write_text(
        json.dumps({"classes": ["calm", "energetic"]}),
        encoding="utf-8",
    )


def test_prepare_returns_mel_features_without_loading_inference_models(
    tmp_path: Path, monkeypatch
) -> None:
    _write_metadata(tmp_path)
    backend = OnnxBackend(tmp_path)
    audio = np.arange(20_000, dtype=np.float32)
    received_audio = None

    class Loader:
        def __init__(self, **_kwargs) -> None:
            pass

        def __call__(self) -> np.ndarray:
            return audio

    def features(truncated_audio: np.ndarray) -> np.ndarray:
        nonlocal received_audio
        received_audio = truncated_audio
        return np.ones((3, 128, 96), dtype=np.float32)

    monkeypatch.setattr(backend, "_load_audio_loader", lambda: Loader)
    monkeypatch.setattr(backend, "_features", features)
    monkeypatch.setattr(
        backend,
        "_load_models",
        lambda: (_ for _ in ()).throw(AssertionError("inference models loaded")),
    )

    prepared = backend.prepare(tmp_path / "song.flac", AnalysisOptions(max_audio_seconds=1))

    assert prepared.shape == (3, 128, 96)
    assert received_audio is not None
    assert len(received_audio) == 16_000


def test_effnet_uses_dynamic_batch_and_selects_both_semantic_outputs() -> None:
    session = _EffnetSession()
    features = np.zeros((2, 128, 96), dtype=np.float64)

    genres, embeddings = OnnxBackend._run_effnet(session, features)

    assert genres.shape == (2, 400)
    assert embeddings.shape == (2, 1280)
    assert session.received.dtype == np.float32


def test_model_sessions_keep_mood_inference_on_cpu(tmp_path: Path, monkeypatch) -> None:
    _write_metadata(tmp_path)
    created_sessions: list[tuple[str, list[str]]] = []

    class Session:
        def __init__(self, path: str, providers: list[str]) -> None:
            created_sessions.append((Path(path).name, providers))

    monkeypatch.setitem(
        sys.modules,
        "onnxruntime",
        SimpleNamespace(InferenceSession=Session),
    )
    backend = OnnxBackend(tmp_path, image_variant="cuda")

    backend.initialize()

    assert created_sessions == [
        (
            "discogs-effnet-bsdynamic-1.onnx",
            ["CUDAExecutionProvider", "CPUExecutionProvider"],
        ),
        ("mtg_jamendo_moodtheme-discogs-effnet-1.onnx", ["CPUExecutionProvider"]),
    ]


def test_prepared_batch_splits_genres_and_moods_by_title(tmp_path: Path) -> None:
    _write_metadata(tmp_path)
    backend = OnnxBackend(tmp_path)
    effnet = _EffnetSession()
    mood = _MoodSession()

    def run_effnet(_session, features):
        genres = np.zeros((len(features), 400), dtype=np.float32)
        genres[0, 1] = 0.9
        genres[1:, 2] = 0.8
        embeddings = np.ones((len(features), 1280), dtype=np.float32)
        return genres, embeddings

    def run_mood(_session, embeddings):
        moods = np.zeros((len(embeddings), 2), dtype=np.float32)
        moods[0, 0] = 0.7
        moods[1:, 1] = 0.6
        return moods

    backend._loaded = {
        "effnet": effnet,
        "mood": mood,
        "genre_labels": [f"genre-{index}" for index in range(400)],
        "mood_labels": ["calm", "energetic"],
    }
    backend._run_effnet = run_effnet
    backend._run_onnx = run_mood

    results = backend.analyze_prepared_batch(
        [
            np.zeros((1, 128, 96), dtype=np.float32),
            np.zeros((2, 128, 96), dtype=np.float32),
        ],
        AnalysisOptions(genre_threshold=0.5, mood_threshold=0.5),
    )

    assert [[value.label for value in result.genres] for result in results] == [
        ["genre-1"],
        ["genre-2"],
    ]
    assert [[value.label for value in result.moods] for result in results] == [
        ["calm"],
        ["energetic"],
    ]


def test_onnx_backend_reads_separate_model_manifest(tmp_path: Path) -> None:
    (tmp_path / "onnx-models.json").write_text("[]", encoding="utf-8")

    backend = OnnxBackend(tmp_path)

    assert backend.model_inventory() == []


def test_onnx_features_accept_tensorflow_input_numpy_arrays(
    tmp_path: Path, monkeypatch
) -> None:
    class InputExtractor:
        def __call__(self, _frame: np.ndarray) -> np.ndarray:
            return np.ones(96, dtype=np.float32)

    monkeypatch.setattr(
        OnnxBackend,
        "_load_feature_algorithms",
        staticmethod(
            lambda: (
                lambda _audio, _frame_size, _hop_size: [
                    np.zeros(512, dtype=np.float32)
                ],
                InputExtractor,
            )
        ),
    )
    (tmp_path / "onnx-models.json").write_text("[]", encoding="utf-8")
    backend = OnnxBackend(tmp_path)

    features = backend._features(np.zeros(512, dtype=np.float32))

    assert features.shape == (1, 128, 96)
    assert features.dtype == np.float32
