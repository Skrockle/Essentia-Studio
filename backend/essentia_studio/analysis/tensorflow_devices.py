"""Runtime compute detection without importing heavy ML libraries at module load."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Literal

from essentia_studio.errors import AppError


@dataclass(frozen=True, slots=True)
class DeviceReport:
    gpu_devices: tuple[str, ...]
    provider: str
    cuda_version: str | None = None
    cudnn_version: str | None = None
    diagnostic: str | None = None


def detect_tensorflow_devices() -> DeviceReport:
    """Report GPUs visible to TensorFlow, with an NVIDIA runtime fallback.

    Essentia embeds TensorFlow's C++ runtime and does not install the Python
    ``tensorflow`` package. On that wheel, ``nvidia-smi`` is the reliable
    preflight; the release GPU smoke additionally proves a real inference.
    """
    try:
        import tensorflow as tensorflow  # type: ignore[import-not-found]

        devices = tuple(device.name for device in tensorflow.config.list_physical_devices("GPU"))
        build_info: dict[str, Any] = tensorflow.sysconfig.get_build_info()
        return DeviceReport(
            gpu_devices=devices,
            provider="tensorflow",
            cuda_version=_optional_string(build_info.get("cuda_version")),
            cudnn_version=_optional_string(build_info.get("cudnn_version")),
        )
    except ImportError:
        return _detect_nvidia_runtime()
    except Exception as error:  # TensorFlow can fail while loading native libraries.
        return DeviceReport((), "tensorflow", diagnostic=str(error))


def select_compute(
    preference: Literal["auto", "cpu", "cuda"],
    *,
    image_variant: str,
    gpu_devices: list[str] | tuple[str, ...],
) -> Literal["cpu", "cuda"]:
    if preference == "cpu":
        return "cpu"
    if image_variant != "cuda":
        if preference == "cuda":
            raise _cuda_unavailable("The CPU image does not contain CUDA libraries.")
        return "cpu"
    if gpu_devices:
        return "cuda"
    if preference == "cuda":
        raise _cuda_unavailable("No NVIDIA GPU is visible inside the CUDA container.")
    return "cpu"


def _detect_nvidia_runtime() -> DeviceReport:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return DeviceReport((), "nvidia-runtime", diagnostic=str(error))
    devices = tuple(line.strip() for line in result.stdout.splitlines() if line.strip())
    diagnostic = result.stderr.strip() or None if result.returncode else None
    return DeviceReport(devices, "nvidia-runtime", diagnostic=diagnostic)


def _optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None


def _cuda_unavailable(message: str) -> AppError:
    return AppError("cuda_device_unavailable", message, 409)
