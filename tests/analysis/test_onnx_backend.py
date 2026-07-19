from pathlib import Path

import numpy as np

from essentia_studio.analysis.onnx_backend import OnnxBackend


class _Input:
    name = "features"


class _Session:
    def __init__(self) -> None:
        self.inputs = []
        self.received = None

    def get_inputs(self):
        return [_Input()]

    def run(self, _outputs, inputs):
        self.received = inputs["features"]
        return [np.zeros((2, 400), dtype=np.float32), np.ones((2, 1280), dtype=np.float32)]


def test_onnx_embedding_uses_dynamic_batch_and_embedding_output() -> None:
    session = _Session()
    features = np.zeros((2, 128, 96), dtype=np.float64)

    embeddings = OnnxBackend._run_embedding(session, features)

    assert embeddings.shape == (2, 1280)
    assert session.received.dtype == np.float32


def test_onnx_backend_reads_separate_model_manifest(tmp_path: Path) -> None:
    (tmp_path / "onnx-models.json").write_text("[]", encoding="utf-8")

    backend = OnnxBackend(tmp_path)

    assert backend.model_inventory() == []


def test_onnx_features_accept_tensorflow_input_numpy_arrays(tmp_path: Path) -> None:
    class InputExtractor:
        def __call__(self, _frame: np.ndarray) -> np.ndarray:
            return np.ones(96, dtype=np.float32)

    models = {
        "TensorflowInputMusiCNN": InputExtractor,
        "FrameGenerator": lambda _audio, _frame_size, _hop_size: [
            np.zeros(512, dtype=np.float32)
        ],
    }

    (tmp_path / "onnx-models.json").write_text("[]", encoding="utf-8")
    backend = OnnxBackend(tmp_path)

    features = backend._features(np.zeros(512, dtype=np.float32), models)

    assert features.shape == (1, 128, 96)
    assert features.dtype == np.float32
