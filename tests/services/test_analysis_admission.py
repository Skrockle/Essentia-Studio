from datetime import datetime, timezone
from pathlib import Path

import pytest

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.analysis_admission import AnalysisAdmissionService, AnalysisWorkItem
from essentia_studio.tags.protocol import ManagedTagSnapshot
from essentia_studio.tags.registry import TagAdapterRegistry


class CountingAdapter:
    def __init__(self, snapshots: dict[str, ManagedTagSnapshot | Exception]) -> None:
        self.snapshots = snapshots
        self.reads: list[str] = []

    def read(self, path: Path) -> ManagedTagSnapshot:
        self.reads.append(path.name)
        snapshot = self.snapshots[path.name]
        if isinstance(snapshot, Exception):
            raise snapshot
        return snapshot

    def write(self, *_args) -> None:
        raise AssertionError("Admission must not write tags")

    def restore(self, *_args) -> None:
        raise AssertionError("Admission must not restore tags")


@pytest.fixture
def track_repository(tmp_path) -> TrackRepository:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    return TrackRepository(engine)


@pytest.fixture
def tracks(tmp_path, track_repository: TrackRepository):
    names = ["empty.flac", "genre-only.flac", "mood-only.flac", "complete.flac"]
    for name in names:
        (tmp_path / name).write_bytes(b"audio")
    track_repository.replace_scan(
        [
            ScannedTrack(name, ".flac", TrackFingerprint(5, index))
            for index, name in enumerate(names, start=1)
        ],
        datetime.now(timezone.utc),
    )
    return [track_repository.get_by_path(name) for name in names]


@pytest.fixture
def admission(tmp_path, track_repository: TrackRepository):
    adapter = CountingAdapter(
        {
            "empty.flac": ManagedTagSnapshot("vorbis", {}),
            "genre-only.flac": ManagedTagSnapshot("vorbis", {"genres": ["Rock"]}),
            "mood-only.flac": ManagedTagSnapshot("vorbis", {"moods": ["Calm"]}),
            "complete.flac": ManagedTagSnapshot(
                "vorbis", {"genres": ["Rock"], "moods": ["Calm"]}
            ),
            "unreadable.flac": ValueError("broken tag metadata"),
        }
    )
    return (
        AnalysisAdmissionService(track_repository, TagAdapterRegistry(adapter), tmp_path),
        adapter,
    )


def test_admission_enables_only_missing_requested_heads(
    admission,
    tracks,
    track_repository,
) -> None:
    service, adapter = admission

    admitted = service.prepare(tracks, AnalysisOptions())

    assert admitted.items == [
        AnalysisWorkItem("empty.flac", True, True),
        AnalysisWorkItem("genre-only.flac", False, True),
        AnalysisWorkItem("mood-only.flac", True, False),
    ]
    assert admitted.skipped_complete == ["complete.flac"]
    assert admitted.failures == []
    assert adapter.reads == ["empty.flac", "genre-only.flac", "mood-only.flac", "complete.flac"]
    assert track_repository.get_by_path("genre-only.flac").managed_tags.genres == ["Rock"]
    assert track_repository.get_by_path("mood-only.flac").managed_tags.moods == ["Calm"]


def test_admission_does_not_reenable_a_disabled_head(admission, tracks) -> None:
    service, _adapter = admission

    admitted = service.prepare(tracks, AnalysisOptions(enable_genres=False, enable_moods=True))

    assert admitted.items == [
        AnalysisWorkItem("empty.flac", False, True),
        AnalysisWorkItem("genre-only.flac", False, True),
    ]
    assert admitted.skipped_complete == ["mood-only.flac", "complete.flac"]


def test_admission_excludes_read_failure_instead_of_assuming_empty(
    admission,
    tmp_path,
    track_repository,
) -> None:
    service, adapter = admission
    (tmp_path / "unreadable.flac").write_bytes(b"audio")
    track_repository.replace_scan(
        [ScannedTrack("unreadable.flac", ".flac", TrackFingerprint(5, 1))],
        datetime.now(timezone.utc),
    )
    unreadable_track = track_repository.get_by_path("unreadable.flac")

    admitted = service.prepare([unreadable_track], AnalysisOptions())

    assert admitted.items == []
    assert admitted.failures[0].code == "managed_tags_unreadable"
    assert admitted.failures[0].relative_path == "unreadable.flac"
    assert adapter.reads == ["unreadable.flac"]
