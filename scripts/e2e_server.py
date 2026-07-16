"""Start an isolated fake-analysis backend with a valid audio fixture."""

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


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="essentia-studio-e2e-"))
    music_root = root / "music"
    data_dir = root / "data"
    music_root.mkdir()
    data_dir.mkdir()
    create_wave_fixture(music_root / "song-one.wav")
    config = RuntimeConfig.from_env(
        {
            "ESSENTIA_MUSIC_ROOT": str(music_root),
            "ESSENTIA_DATA_DIR": str(data_dir),
            "ESSENTIA_FRONTEND_DIR": str(root / "missing-frontend"),
            "ESSENTIA_ANALYSIS_BACKEND": "fake",
        }
    )
    uvicorn.run(create_app(config), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
