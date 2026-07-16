from scripts.gpu_smoke import _tensorflow_gpu_evidence


def test_gpu_evidence_requires_tensorflow_device_creation() -> None:
    log = (
        "Created TensorFlow device "
        "(/job:localhost/replica:0/task:0/device:GPU:0 with 8192 MB memory)"
    )

    assert _tensorflow_gpu_evidence("", log) == [log]


def test_visible_driver_without_tensorflow_placement_is_not_evidence() -> None:
    log = "NVIDIA-SMI found GPU:0, inference completed"

    assert _tensorflow_gpu_evidence(log, "") == []
