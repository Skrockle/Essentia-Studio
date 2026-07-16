from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    music_root: Path
    data_dir: Path
    database_path: Path
    playlist_dir: Path
    frontend_dir: Path
    model_dir: Path
    analysis_backend: Literal["essentia", "fake"]
    image_variant: Literal["cpu", "cuda"]
    host: str
    port: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> RuntimeConfig:
        values = os.environ if env is None else env
        music_root = Path(values.get("ESSENTIA_MUSIC_ROOT", "/music"))
        data_dir = Path(values.get("ESSENTIA_DATA_DIR", "/data"))

        return cls(
            music_root=music_root,
            data_dir=data_dir,
            database_path=Path(
                values.get("ESSENTIA_DATABASE_PATH", str(data_dir / "essentia-studio.db"))
            ),
            playlist_dir=Path(
                values.get("ESSENTIA_PLAYLIST_DIR", str(music_root / "SmartPlaylists"))
            ),
            frontend_dir=Path(values.get("ESSENTIA_FRONTEND_DIR", "frontend/dist")),
            model_dir=Path(values.get("ESSENTIA_MODEL_DIR", "/app/models")),
            analysis_backend=_analysis_backend(
                values.get("ESSENTIA_ANALYSIS_BACKEND", "essentia")
            ),
            image_variant=_image_variant(values.get("ESSENTIA_IMAGE_VARIANT", "cpu")),
            host=values.get("ESSENTIA_HOST", "0.0.0.0"),
            port=int(values.get("ESSENTIA_PORT", "8000")),
        )


def _image_variant(value: str) -> Literal["cpu", "cuda"]:
    if value not in {"cpu", "cuda"}:
        raise ValueError("ESSENTIA_IMAGE_VARIANT must be 'cpu' or 'cuda'")
    return value


def _analysis_backend(value: str) -> Literal["essentia", "fake"]:
    if value not in {"essentia", "fake"}:
        raise ValueError("ESSENTIA_ANALYSIS_BACKEND must be 'essentia' or 'fake'")
    return value
