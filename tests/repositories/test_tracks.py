from datetime import datetime, timezone

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint
from essentia_studio.repositories.tracks import TrackRepository


def scanned_track(path: str, size: int = 10) -> ScannedTrack:
    return ScannedTrack(path, ".flac", TrackFingerprint(size=size, mtime_ns=100))


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
