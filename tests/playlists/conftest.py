import pytest

from essentia_studio.playlists.catalog import PlaylistCatalog


@pytest.fixture
def catalog() -> PlaylistCatalog:
    return PlaylistCatalog.load()
