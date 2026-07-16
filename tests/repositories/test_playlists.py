import pytest
from sqlalchemy import text

from essentia_studio.errors import AppError
from essentia_studio.playlists.storage import PlaylistStorage
from essentia_studio.repositories.playlists import PlaylistRepository


def test_success_and_failure_audit_preserve_last_known_good_record(client, tmp_path) -> None:
    engine = client.app.state.engine
    storage = PlaylistStorage(tmp_path / "playlists", PlaylistRepository(engine))
    created = storage.create("mix.nsp", {"name": "Mix"})
    created.path.write_text('{"name":"External"}\n', encoding="utf-8")

    with pytest.raises(AppError):
        storage.update("mix.nsp", {"name": "Changed"}, created.fingerprint)

    with engine.connect() as connection:
        record = connection.execute(
            text("SELECT display_name, fingerprint FROM playlist_records")
        ).one()
        operations = connection.execute(
            text("SELECT success, error_code FROM playlist_operations ORDER BY id")
        ).all()

    assert record.display_name == "Mix"
    assert record.fingerprint == created.fingerprint
    assert [(row.success, row.error_code) for row in operations] == [
        (1, None),
        (0, "playlist_changed"),
    ]
