import os
from pathlib import Path

from essentia_studio.config import RuntimeConfig
from essentia_studio.schemas.common import Capabilities, PathCapability


def inspect_path(path: Path) -> PathCapability:
    if not path.exists():
        return PathCapability(path=str(path), status="missing")

    probe_parent = path if path.is_dir() else path.parent
    status = "ready" if os.access(probe_parent, os.W_OK) else "read_only"
    return PathCapability(path=str(path), status=status)


class CapabilityService:
    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config

    def inspect(self) -> Capabilities:
        available_compute = ["cpu", "cuda"] if self._config.image_variant == "cuda" else ["cpu"]
        return Capabilities(
            image_variant=self._config.image_variant,
            available_compute=available_compute,
            music_root=inspect_path(self._config.music_root),
            data_dir=inspect_path(self._config.data_dir),
            playlist_dir=inspect_path(self._config.playlist_dir),
            models=[],
        )
