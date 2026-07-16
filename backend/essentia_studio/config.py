from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    music_root: Path
    data_dir: Path
    database_path: Path
    playlist_dir: Path
    frontend_dir: Path
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
            host=values.get("ESSENTIA_HOST", "0.0.0.0"),
            port=int(values.get("ESSENTIA_PORT", "8000")),
        )
