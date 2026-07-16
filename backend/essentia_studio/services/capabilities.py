import os
from pathlib import Path

from essentia_studio.analysis.protocol import AnalysisBackend
from essentia_studio.config import RuntimeConfig
from essentia_studio.schemas.common import Capabilities, PathCapability


def inspect_path(path: Path) -> PathCapability:
    if not path.exists():
        return PathCapability(path=str(path), status="missing")

    probe_parent = path if path.is_dir() else path.parent
    status = "ready" if os.access(probe_parent, os.W_OK) else "read_only"
    return PathCapability(path=str(path), status=status)


class CapabilityService:
    def __init__(
        self,
        config: RuntimeConfig,
        analysis_backend: AnalysisBackend | None = None,
    ) -> None:
        self._config = config
        self._analysis_backend = analysis_backend

    def inspect(self) -> Capabilities:
        available_compute = (
            self._analysis_backend.available_compute()
            if self._analysis_backend
            else ["cpu"]
        )
        return Capabilities(
            image_variant=self._config.image_variant,
            available_compute=available_compute,
            music_root=inspect_path(self._config.music_root),
            data_dir=inspect_path(self._config.data_dir),
            playlist_dir=inspect_path(self._config.playlist_dir),
            models=self._analysis_backend.model_inventory() if self._analysis_backend else [],
        )
