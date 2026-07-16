import pytest

from essentia_studio.errors import AppError
from essentia_studio.playlists.catalog import PlaylistCatalog
from essentia_studio.playlists.storage import PlaylistStorage
from essentia_studio.playlists.validation import validate_playlist


@pytest.fixture
def storage(tmp_path) -> PlaylistStorage:
    return PlaylistStorage(tmp_path / "playlists")


@pytest.fixture
def valid_playlist():
    return validate_playlist(
        {"name": "Mix", "all": [{"contains": {"genre": "Ambient"}}]},
        PlaylistCatalog.load(),
    )


def test_playlist_name_cannot_escape_root(storage) -> None:
    with pytest.raises(AppError) as error:
        storage.read("../secrets.nsp")

    assert error.value.code == "invalid_playlist_name"


def test_update_rejects_external_change(storage, valid_playlist) -> None:
    saved = storage.create("mix.nsp", valid_playlist)
    saved.path.write_text('{"name":"external"}\n', encoding="utf-8")

    with pytest.raises(AppError) as error:
        storage.update(
            "mix.nsp",
            valid_playlist,
            expected_fingerprint=saved.fingerprint,
        )

    assert error.value.code == "playlist_changed"


def test_create_update_delete_lifecycle_is_fingerprint_guarded(storage, valid_playlist) -> None:
    created = storage.create("mix.nsp", valid_playlist)
    updated_definition = valid_playlist.model_copy(update={"name": "Updated Mix"})
    updated = storage.update(
        "mix.nsp",
        updated_definition,
        expected_fingerprint=created.fingerprint,
    )

    assert updated.fingerprint != created.fingerprint
    assert updated.definition["name"] == "Updated Mix"
    storage.delete("mix.nsp", updated.fingerprint)
    assert storage.list() == []
