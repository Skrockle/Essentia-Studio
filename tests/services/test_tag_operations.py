from datetime import datetime, timezone

from essentia_studio.domain.analysis import AnalysisResult
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint
from essentia_studio.repositories.writes import WriteRepository
from essentia_studio.services.tag_operations import TagOperationService
from essentia_studio.tags.protocol import DesiredTags, ManagedTagSnapshot
from essentia_studio.tags.registry import TagAdapterRegistry


class FakeTagAdapter:
    def __init__(self, snapshot: ManagedTagSnapshot) -> None:
        self.snapshot = snapshot
        self.write_calls: list[DesiredTags] = []

    def read(self, _path):
        return self.snapshot

    def write(self, path, desired, _overwrite):
        self.write_calls.append(desired)
        self.snapshot = ManagedTagSnapshot(
            "fake",
            {
                "genres": desired.genres,
                "moods": desired.moods,
                "genre_confidence": [],
                "mood_confidence": [],
            },
        )
        path.write_bytes(path.read_bytes() + b"tags")

    def restore(self, path, snapshot):
        self.snapshot = snapshot
        path.write_bytes(path.read_bytes() + b"undo")


def make_service(client, music_root):
    path = music_root / "song.mp3"
    path.write_bytes(b"audio")
    stat = path.stat()
    fingerprint = TrackFingerprint(stat.st_size, stat.st_mtime_ns)
    tracks = client.app.state.track_repository
    tracks.replace_scan(
        [ScannedTrack("song.mp3", ".mp3", fingerprint)],
        datetime.now(timezone.utc),
    )
    track = tracks.get_by_path("song.mp3")
    stored = client.app.state.result_repository.save(
        track,
        AnalysisResult(model_ids=["fake"]),
        ["Ambient"],
        ["Calm"],
    )
    original = ManagedTagSnapshot(
        "fake",
        {
            "genres": ["Rock"],
            "moods": [],
            "genre_confidence": [],
            "mood_confidence": [],
        },
    )
    adapter = FakeTagAdapter(original)
    service = TagOperationService(
        client.app.state.result_repository,
        WriteRepository(client.app.state.engine),
        TagAdapterRegistry(adapter),
        music_root,
    )
    return service, adapter, stored.id, path, original


def test_write_skips_track_changed_after_analysis(client, music_root) -> None:
    service, adapter, result_id, path, _original = make_service(client, music_root)
    path.write_bytes(path.read_bytes() + b"changed")

    result = service.write_one(result_id)

    assert result.status == "conflict"
    assert result.error_code == "track_changed_since_analysis"
    assert adapter.write_calls == []


def test_undo_restores_exact_managed_snapshot(client, music_root) -> None:
    service, adapter, result_id, _path, original = make_service(client, music_root)

    operation = service.write_one(result_id)
    restored = service.undo(operation.id)

    assert operation.status == "verified"
    assert restored.status == "undone"
    assert adapter.snapshot == original
