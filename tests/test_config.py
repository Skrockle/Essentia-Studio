from pathlib import Path

from essentia_studio.config import RuntimeConfig


def test_runtime_config_uses_container_defaults() -> None:
    config = RuntimeConfig.from_env({})

    assert config.music_root == Path("/music")
    assert config.data_dir == Path("/data")
    assert config.database_path == Path("/data/essentia-studio.db")
    assert config.playlist_dir == Path("/music/SmartPlaylists")
    assert config.host == "0.0.0.0"
    assert config.port == 8000
