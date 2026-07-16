import pytest

from essentia_studio.analysis.tensorflow_devices import select_compute
from essentia_studio.errors import AppError


def test_auto_uses_cpu_when_cuda_image_has_no_visible_gpu() -> None:
    assert select_compute("auto", image_variant="cuda", gpu_devices=[]) == "cpu"


def test_auto_uses_cuda_when_gpu_is_visible() -> None:
    assert select_compute("auto", image_variant="cuda", gpu_devices=["GPU:0"]) == "cuda"


def test_explicit_cuda_requires_visible_tensorflow_gpu() -> None:
    with pytest.raises(AppError) as error:
        select_compute("cuda", image_variant="cuda", gpu_devices=[])
    assert error.value.code == "cuda_device_unavailable"


def test_cpu_image_never_selects_cuda() -> None:
    assert select_compute("auto", image_variant="cpu", gpu_devices=["GPU:0"]) == "cpu"
