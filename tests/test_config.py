from pathlib import Path

import pytest

from essentia_studio.config import RuntimeConfig


def test_runtime_config_uses_container_defaults() -> None:
    config = RuntimeConfig.from_env({})

    assert config.music_root == Path("/music")
    assert config.data_dir == Path("/data")
    assert config.database_path == Path("/data/essentia-studio.db")
    assert config.playlist_dir == Path("/music/SmartPlaylists")
    assert config.image_variant == "cpu"
    assert config.host == "0.0.0.0"
    assert config.port == 8000


def test_runtime_config_rejects_unknown_image_variant() -> None:
    with pytest.raises(ValueError, match="ESSENTIA_IMAGE_VARIANT"):
        RuntimeConfig.from_env({"ESSENTIA_IMAGE_VARIANT": "metal"})
