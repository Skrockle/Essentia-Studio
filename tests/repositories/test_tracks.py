from datetime import datetime, timezone

import pytest

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.tracks import (
    ManagedTagInventory,
    ScannedTrack,
    TrackFingerprint,
    TrackMetadata,
)
from essentia_studio.repositories.tracks import TrackRepository


def scanned_track(
    path: str,
    size: int = 10,
    *,
    artist: str = "Unknown",
    title: str = "Song",
    managed_tags: ManagedTagInventory | None = None,
) -> ScannedTrack:
    return ScannedTrack(
        path,
        ".flac",
        TrackFingerprint(size=size, mtime_ns=100),
        TrackMetadata(artist, title, "Album", 185.25, "embedded"),
        managed_tags if managed_tags is not None else ManagedTagInventory(),
    )


def test_replace_scan_upserts_tracks_and_marks_missing(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = TrackRepository(engine)

    first = repository.replace_scan(
        [scanned_track("a.flac"), scanned_track("b.flac")],
        datetime(2026, 7, 16, 10, tzinfo=timezone.utc),
    )
    second = repository.replace_scan(
        [scanned_track("b.flac", size=20)],
        datetime(2026, 7, 16, 11, tzinfo=timezone.utc),
    )

    assert (first.scanned, first.present, first.missing) == (2, 2, 0)
    assert (second.scanned, second.present, second.missing) == (1, 1, 1)
    assert repository.get_by_path("b.flac").fingerprint.size == 20
    assert repository.get_by_path("a.flac").present is False


def test_replace_scan_persists_and_updates_metadata(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = TrackRepository(engine)
    seen_at = datetime(2026, 7, 16, 10, tzinfo=timezone.utc)

    repository.replace_scan(
        [
            scanned_track(
                "Artist/Album/song.flac",
                artist="Artist",
                title="Old Title",
                managed_tags=ManagedTagInventory(
                    ["Rock"], ["Energetic"], "error", "managed_tags_unreadable"
                ),
            )
        ],
        seen_at,
    )
    repository.replace_scan(
        [
            scanned_track(
                "Artist/Album/song.flac",
                artist="Artist",
                title="New Title",
                managed_tags=ManagedTagInventory(["Ambient"], [], "ok", None),
            )
        ],
        datetime(2026, 7, 16, 11, tzinfo=timezone.utc),
    )

    stored = repository.get_by_path("Artist/Album/song.flac")
    assert stored.metadata == TrackMetadata(
        "Artist", "New Title", "Album", 185.25, "embedded"
    )
    assert stored.managed_tags == ManagedTagInventory(["Ambient"], [], "ok", None)


def test_replace_scan_preserves_last_read_tags_after_an_inventory_error(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = TrackRepository(engine)

    repository.replace_scan(
        [scanned_track("song.flac", managed_tags=ManagedTagInventory(["Rock"], ["Calm"], "ok"))],
        datetime(2026, 7, 16, 10, tzinfo=timezone.utc),
    )
    repository.replace_scan(
        [
            scanned_track(
                "song.flac",
                managed_tags=ManagedTagInventory(
                    status="error", error_code="managed_tags_unreadable"
                ),
            )
        ],
        datetime(2026, 7, 16, 11, tzinfo=timezone.utc),
    )

    assert repository.get_by_path("song.flac").managed_tags == ManagedTagInventory(
        ["Rock"], ["Calm"], "error", "managed_tags_unreadable"
    )

    repository.replace_scan(
        [scanned_track("song.flac", managed_tags=ManagedTagInventory([], [], "ok"))],
        datetime(2026, 7, 16, 12, tzinfo=timezone.utc),
    )

    assert repository.get_by_path("song.flac").managed_tags == ManagedTagInventory(
        [], [], "ok", None
    )


def test_update_managed_tags_replaces_successful_file_state(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = TrackRepository(engine)
    repository.replace_scan(
        [
            scanned_track(
                "song.flac",
                managed_tags=ManagedTagInventory(
                    ["Rock"], [], "error", "managed_tags_unreadable"
                ),
            )
        ],
        datetime(2026, 7, 16, 10, tzinfo=timezone.utc),
    )

    repository.update_managed_tags(1, ManagedTagInventory(["Ambient"], ["Calm"], "ok"))

    assert repository.get_by_path("song.flac").managed_tags == ManagedTagInventory(
        ["Ambient"], ["Calm"], "ok", None
    )


def test_update_managed_tags_rejects_an_unreadable_inventory(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = TrackRepository(engine)

    with pytest.raises(ValueError, match="Only successfully read managed tags"):
        repository.update_managed_tags(
            1, ManagedTagInventory(status="error", error_code="managed_tags_unreadable")
        )
