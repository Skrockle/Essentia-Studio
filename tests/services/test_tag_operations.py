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


class RetainingTagAdapter(FakeTagAdapter):
    def write(self, path, desired, _overwrite):
        self.snapshot = ManagedTagSnapshot(
            "fake",
            {
                "genres": ["Rock", *desired.genres],
                "moods": ["Dreamy", *desired.moods],
                "genre_confidence": [],
                "mood_confidence": [],
            },
        )
        path.write_bytes(path.read_bytes() + b"tags")


class WriteFailureTagAdapter(FakeTagAdapter):
    def write(self, _path, _desired, _overwrite):
        raise RuntimeError("write failed")


class UndoVerificationFailureTagAdapter(FakeTagAdapter):
    def __init__(self, snapshot: ManagedTagSnapshot) -> None:
        super().__init__(snapshot)
        self._restored = False

    def read(self, path):
        if self._restored:
            return ManagedTagSnapshot(
                "fake",
                {
                    "genres": ["Not restored"],
                    "moods": [],
                    "genre_confidence": [],
                    "mood_confidence": [],
                },
            )
        return super().read(path)

    def restore(self, path, snapshot):
        super().restore(path, snapshot)
        self._restored = True


class UndoExceptionTagAdapter(FakeTagAdapter):
    def restore(self, _path, _snapshot):
        raise RuntimeError("restore failed")


class RetryingUndoAdapter(FakeTagAdapter):
    def __init__(self, snapshot: ManagedTagSnapshot) -> None:
        super().__init__(snapshot)
        self._fail_restore = True

    def restore(self, path, snapshot):
        if self._fail_restore:
            self._fail_restore = False
            raise RuntimeError("temporary restore failure")
        super().restore(path, snapshot)


class UnreadableFirstTrackAdapter(FakeTagAdapter):
    def read(self, path):
        if path.name == "unreadable.mp3":
            raise RuntimeError("cannot read tags")
        return super().read(path)


def make_service(
    client,
    music_root,
    adapter_type=FakeTagAdapter,
    initial_inventory: ManagedTagInventory | None = None,
):
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
                managed_tags=initial_inventory or inventory_from_snapshot(original),
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


def make_two_track_service(client, music_root):
    paths = [music_root / "unreadable.mp3", music_root / "writable.mp3"]
    for path in paths:
        path.write_bytes(b"audio")
    tracks = client.app.state.track_repository
    tracks.replace_scan(
        [
            ScannedTrack(
                path.name,
                ".mp3",
                TrackFingerprint(path.stat().st_size, path.stat().st_mtime_ns),
                managed_tags=ManagedTagInventory(["Rock"], ["Dreamy"], "ok"),
            )
            for path in paths
        ],
        datetime.now(timezone.utc),
    )
    results = [
        client.app.state.result_repository.save(
            tracks.get_by_path(path.name),
            AnalysisResult(model_ids=["fake"]),
            ["Ambient"],
            ["Calm"],
        )
        for path in paths
    ]
    original = ManagedTagSnapshot(
        "fake",
        {
            "genres": ["Rock"],
            "moods": ["Dreamy"],
            "genre_confidence": [],
            "mood_confidence": [],
        },
    )
    adapter = UnreadableFirstTrackAdapter(original)
    service = TagOperationService(
        client.app.state.result_repository,
        WriteRepository(client.app.state.engine),
        TagAdapterRegistry(adapter),
        music_root,
    )
    return service, results


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


def test_write_many_isolates_unreadable_file_tags(client, music_root) -> None:
    service, results = make_two_track_service(client, music_root)

    operations = service.write_many([result.id for result in results])

    first = client.app.state.track_repository.get_by_path("unreadable.mp3")
    second = client.app.state.track_repository.get_by_path("writable.mp3")
    assert [(operation.status, operation.error_code) for operation in operations] == [
        ("failed", "managed_tags_unreadable"),
        ("verified", None),
    ]
    assert operations[0].error_message == "Die verwalteten Tags konnten nicht gelesen werden."
    assert first.managed_tags == ManagedTagInventory(["Rock"], ["Dreamy"], "ok")
    assert second.managed_tags == ManagedTagInventory(["Ambient"], ["Calm"], "ok")


def test_write_many_isolates_unavailable_file_paths(client, music_root) -> None:
    service, results = make_two_track_service(client, music_root)
    (music_root / "unreadable.mp3").unlink()

    operations = service.write_many([result.id for result in results])

    first = client.app.state.track_repository.get_by_path("unreadable.mp3")
    second = client.app.state.track_repository.get_by_path("writable.mp3")
    assert [(operation.status, operation.error_code) for operation in operations] == [
        ("failed", "track_unavailable"),
        ("verified", None),
    ]
    assert operations[0].error_message == "Die Datei konnte vor dem Schreiben nicht gelesen werden."
    assert first.managed_tags == ManagedTagInventory(["Rock"], ["Dreamy"], "ok")
    assert second.managed_tags == ManagedTagInventory(["Ambient"], ["Calm"], "ok")


def test_verified_write_uses_actual_read_back_tags_for_inventory(client, music_root) -> None:
    service, _adapter, result_id, _path, _original = make_service(
        client, music_root, RetainingTagAdapter
    )

    operation = service.write_one(result_id)

    stored = client.app.state.track_repository.get_by_path(operation.relative_path)
    assert stored.managed_tags == ManagedTagInventory(["Rock", "Ambient"], ["Dreamy", "Calm"], "ok")


def test_write_exception_preserves_error_inventory(client, music_root) -> None:
    error_inventory = ManagedTagInventory([], [], "error", "managed_tags_unreadable")
    service, _adapter, result_id, _path, _original = make_service(
        client,
        music_root,
        WriteFailureTagAdapter,
        error_inventory,
    )

    operation = service.write_one(result_id)

    stored = client.app.state.track_repository.get_by_path(operation.relative_path)
    assert operation.status == "failed"
    assert operation.error_code == "tag_write_failed"
    assert stored.managed_tags == error_inventory


def test_undo_verification_failure_preserves_verified_write_state(client, music_root) -> None:
    service, _adapter, result_id, _path, original = make_service(
        client, music_root, UndoVerificationFailureTagAdapter
    )

    verified = service.write_one(result_id)
    failed = service.undo(verified.id)

    stored = client.app.state.track_repository.get_by_path(failed.relative_path)
    assert failed.status == "verified"
    assert failed.undo_available is True
    assert failed.error_code == "undo_verification_failed"
    assert failed.original_snapshot == original
    assert failed.post_write_fingerprint == verified.post_write_fingerprint
    assert stored.managed_tags == ManagedTagInventory(["Ambient"], ["Calm"], "ok")


def test_undo_exception_preserves_verified_write_state(client, music_root) -> None:
    service, _adapter, result_id, _path, original = make_service(
        client, music_root, UndoExceptionTagAdapter
    )

    verified = service.write_one(result_id)
    failed = service.undo(verified.id)

    stored = client.app.state.track_repository.get_by_path(failed.relative_path)
    assert failed.status == "verified"
    assert failed.undo_available is True
    assert failed.error_code == "undo_failed"
    assert failed.original_snapshot == original
    assert failed.post_write_fingerprint == verified.post_write_fingerprint
    assert stored.managed_tags == ManagedTagInventory(["Ambient"], ["Calm"], "ok")
    track_id = client.app.state.result_repository.get(result_id).track_id
    assert TrackStateService(client.app.state.engine).states([track_id]) == {track_id: "written"}


def test_undo_precondition_read_failure_preserves_verified_write_state(client, music_root) -> None:
    service, _adapter, result_id, path, original = make_service(client, music_root)

    verified = service.write_one(result_id)
    path.unlink()
    failed = service.undo(verified.id)

    stored = client.app.state.track_repository.get_by_path(failed.relative_path)
    assert failed.status == "verified"
    assert failed.undo_available is True
    assert failed.error_code == "undo_precondition_unreadable"
    assert failed.error_message == "Die Datei konnte vor dem Wiederherstellen nicht gelesen werden."
    assert failed.original_snapshot == original
    assert failed.post_write_fingerprint == verified.post_write_fingerprint
    assert stored.managed_tags == ManagedTagInventory(["Ambient"], ["Calm"], "ok")


def test_undo_fingerprint_conflict_preserves_verified_write_state(client, music_root) -> None:
    service, _adapter, result_id, path, original = make_service(client, music_root)

    verified = service.write_one(result_id)
    path.write_bytes(path.read_bytes() + b"changed")
    conflicted = service.undo(verified.id)

    stored = client.app.state.track_repository.get_by_path(conflicted.relative_path)
    assert conflicted.status == "verified"
    assert conflicted.undo_available is True
    assert conflicted.error_code == "track_changed_since_write"
    assert conflicted.original_snapshot == original
    assert conflicted.post_write_fingerprint == verified.post_write_fingerprint
    assert stored.managed_tags == ManagedTagInventory(["Ambient"], ["Calm"], "ok")


def test_transient_undo_failure_can_be_retried(client, music_root) -> None:
    service, _adapter, result_id, _path, original = make_service(
        client, music_root, RetryingUndoAdapter
    )

    verified = service.write_one(result_id)
    failed = service.undo(verified.id)
    undone = service.undo(verified.id)

    stored = client.app.state.track_repository.get_by_path(undone.relative_path)
    assert failed.status == "verified"
    assert failed.undo_available is True
    assert undone.status == "undone"
    assert stored.managed_tags == inventory_from_snapshot(original)


def test_verified_write_commits_the_draft_as_the_current_file_state(client, music_root) -> None:
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
