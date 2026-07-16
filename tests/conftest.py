from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from essentia_studio.config import RuntimeConfig
from essentia_studio.main import create_app


@pytest.fixture
def music_root(tmp_path):
    music_root = tmp_path / "music"
    music_root.mkdir()
    return music_root


@pytest.fixture
def client(tmp_path, music_root) -> Iterator[TestClient]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config = RuntimeConfig.from_env(
        {
            "ESSENTIA_MUSIC_ROOT": str(music_root),
            "ESSENTIA_DATA_DIR": str(data_dir),
            "ESSENTIA_FRONTEND_DIR": str(tmp_path / "missing-dist"),
            "ESSENTIA_ANALYSIS_BACKEND": "fake",
        }
    )

    with TestClient(create_app(config)) as test_client:
        yield test_client
