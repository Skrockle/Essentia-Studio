from datetime import datetime, timezone

from essentia_studio.domain.analysis import AnalysisResult
from essentia_studio.domain.tracks import ManagedTagInventory, ScannedTrack, TrackFingerprint
from essentia_studio.repositories.writes import WriteRepository
from essentia_studio.services.managed_tag_inventory import inventory_from_snapshot
from essentia_studio.services.tag_operations import TagOperationService
from essentia_studio.services.track_state import TrackStateService
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


class VerificationFailureTagAdapter(FakeTagAdapter):
    def __init__(self, snapshot: ManagedTagSnapshot) -> None:
        super().__init__(snapshot)
        self._verification_read = False

    def read(self, path):
        if self._verification_read:
            return ManagedTagSnapshot(
                "fake",
                {
                    "genres": ["Unverified"],
                    "moods": [],
                    "genre_confidence": [],
                    "mood_confidence": [],
                },
            )
        return super().read(path)

    def write(self, path, desired, overwrite):
        super().write(path, desired, overwrite)
        self._verification_read = True


def make_service(client, music_root, adapter_type=FakeTagAdapter):
    path = music_root / "song.mp3"
    path.write_bytes(b"audio")
    stat = path.stat()
    fingerprint = TrackFingerprint(stat.st_size, stat.st_mtime_ns)
    original = ManagedTagSnapshot(
        "fake",
        {
            "genres": ["Rock"],
            "moods": [],
            "genre_confidence": [],
            "mood_confidence": [],
        },
    )
    tracks = client.app.state.track_repository
    tracks.replace_scan(
        [
            ScannedTrack(
                "song.mp3",
                ".mp3",
                fingerprint,
                managed_tags=inventory_from_snapshot(original),
            )
        ],
        datetime.now(timezone.utc),
    )
    track = tracks.get_by_path("song.mp3")
    stored = client.app.state.result_repository.save(
        track,
        AnalysisResult(model_ids=["fake"]),
        ["Ambient"],
        ["Calm"],
    )
    adapter = adapter_type(original)
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


def test_verified_write_updates_current_file_inventory(client, music_root) -> None:
    service, _adapter, result_id, _path, _original = make_service(client, music_root)

    operation = service.write_one(result_id)

    stored = client.app.state.track_repository.get_by_path(operation.relative_path)
    assert stored.managed_tags == ManagedTagInventory(["Ambient"], ["Calm"], "ok")


def test_verified_undo_restores_current_file_inventory(client, music_root) -> None:
    service, _adapter, result_id, _path, original = make_service(client, music_root)

    operation = service.write_one(result_id)
    client.app.state.track_repository.update_managed_tags(
        client.app.state.result_repository.get(result_id).track_id,
        ManagedTagInventory(["Ambient"], ["Calm"], "ok"),
    )
    service.undo(operation.id)

    stored = client.app.state.track_repository.get_by_path(operation.relative_path)
    assert stored.managed_tags == inventory_from_snapshot(original)


def test_failed_write_verification_preserves_current_file_inventory(client, music_root) -> None:
    service, _adapter, result_id, path, original = make_service(
        client, music_root, VerificationFailureTagAdapter
    )

    operation = service.write_one(result_id)

    stored = client.app.state.track_repository.get_by_path(operation.relative_path)
    assert path.exists()
    assert operation.status == "failed"
    assert operation.error_code == "write_verification_failed"
    assert stored.managed_tags == inventory_from_snapshot(original)


def test_verified_write_commits_the_draft_as_the_current_file_state(
    client, music_root
) -> None:
    service, _adapter, result_id, _path, _original = make_service(client, music_root)
    results = client.app.state.result_repository
    results.update_selection({"mode": "ids", "ids": [result_id]}, True)

    operation = service.write_one(result_id)

    stored = results.get(result_id)
    track = client.app.state.track_repository.get_by_path(stored.relative_path)
    assert operation.status == "verified"
    assert operation.requested_tags == DesiredTags(["Ambient"], ["Calm"])
    assert stored.draft.selected is False
    assert track.fingerprint == operation.post_write_fingerprint


def test_editing_a_verified_draft_makes_it_pending_again(client, music_root) -> None:
    service, _adapter, result_id, _path, _original = make_service(client, music_root)
    results = client.app.state.result_repository
    stored = results.get(result_id)

    service.write_one(result_id)
    assert TrackStateService(client.app.state.engine).states([stored.track_id]) == {
        stored.track_id: "written"
    }

    results.replace_draft(result_id, ["Ambient", "Downtempo"], None)

    assert TrackStateService(client.app.state.engine).states([stored.track_id]) == {
        stored.track_id: "current"
    }
