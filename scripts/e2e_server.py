"""Start an isolated fake-analysis backend with a valid audio fixture."""

import json
import tempfile
import wave
from pathlib import Path

import uvicorn

from essentia_studio.config import RuntimeConfig
from essentia_studio.main import create_app


def create_wave_fixture(path: Path) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\0\0" * 16_000)


def create_tag_catalogs(model_dir: Path) -> None:
    catalogs = {
        "genre_discogs400-discogs-effnet-1.json": ["Ambient", "Electronic---House", "Rock"],
        "mtg_jamendo_moodtheme-discogs-effnet-1.json": ["moodtheme---happy", "moodtheme---sad"],
    }
    for catalog_name, classes in catalogs.items():
        (model_dir / catalog_name).write_text(json.dumps({"classes": classes}), encoding="utf-8")


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="essentia-studio-e2e-"))
    music_root = root / "music"
    data_dir = root / "data"
    model_dir = root / "models"
    music_root.mkdir()
    data_dir.mkdir()
    model_dir.mkdir()
    create_wave_fixture(music_root / "song-one.wav")
    create_wave_fixture(music_root / "uncertain.wav")
    create_tag_catalogs(model_dir)
    config = RuntimeConfig.from_env(
        {
            "ESSENTIA_MUSIC_ROOT": str(music_root),
            "ESSENTIA_DATA_DIR": str(data_dir),
            "ESSENTIA_FRONTEND_DIR": str(root / "missing-frontend"),
            "ESSENTIA_ANALYSIS_BACKEND": "fake",
            "ESSENTIA_MODEL_DIR": str(model_dir),
        }
    )
    uvicorn.run(create_app(config), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
