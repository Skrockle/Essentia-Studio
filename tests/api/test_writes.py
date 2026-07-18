from datetime import datetime, timezone

from essentia_studio.domain.analysis import AnalysisResult
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint
from essentia_studio.services.tag_operations import TagOperationService
from essentia_studio.tags.protocol import ManagedTagSnapshot
from essentia_studio.tags.registry import TagAdapterRegistry


class MemoryAdapter:
    def __init__(self) -> None:
        self.snapshot = ManagedTagSnapshot(
            "fake",
            {
                "genres": ["Rock"],
                "moods": [],
                "genre_confidence": [],
                "mood_confidence": [],
            },
        )

    def read(self, _path):
        return self.snapshot

    def write(self, path, desired, _overwrite):
        self.snapshot = ManagedTagSnapshot(
            "fake",
            {
                "genres": desired.genres,
                "moods": desired.moods,
                "genre_confidence": [],
                "mood_confidence": [],
            },
        )
        path.write_bytes(path.read_bytes() + b"write")

    def restore(self, path, snapshot):
        self.snapshot = snapshot
        path.write_bytes(path.read_bytes() + b"undo")


def seed_result(client, music_root):
    path = music_root / "song.mp3"
    path.write_bytes(b"audio")
    stat = path.stat()
    tracks = client.app.state.track_repository
    tracks.replace_scan(
        [
            ScannedTrack(
                "song.mp3",
                ".mp3",
                TrackFingerprint(stat.st_size, stat.st_mtime_ns),
            )
        ],
        datetime.now(timezone.utc),
    )
    result = client.app.state.result_repository.save(
        tracks.get_by_path("song.mp3"),
        AnalysisResult(model_ids=["fake"]),
        ["Ambient"],
        ["Calm"],
    )
    adapter = MemoryAdapter()
    registry = TagAdapterRegistry(adapter)
    client.app.state.tag_registry = registry
    client.app.state.tag_operation_service = TagOperationService(
        client.app.state.result_repository,
        client.app.state.write_repository,
        registry,
        music_root,
    )
    return result, adapter


def test_preview_requires_a_separate_write_confirmation(client, music_root) -> None:
    result, adapter = seed_result(client, music_root)
    selection = {"selection": {"mode": "ids", "ids": [result.id]}}

    preview = client.post("/api/writes/preview", json=selection)

    assert preview.status_code == 200
    assert preview.json()["items"][0] == {
        "result_id": result.id,
        "relative_path": "song.mp3",
        "before_genres": ["Rock"],
        "after_genres": ["Ambient"],
        "before_moods": [],
        "after_moods": ["Calm"],
        "conflict": False,
    }
    assert adapter.snapshot.fields["genres"] == ["Rock"]

    written = client.post("/api/writes", json=selection)
    operation = written.json()["operations"][0]
    assert operation["status"] == "verified"
    assert operation["undo_available"] is True

    undone = client.post(f"/api/writes/{operation['id']}/undo")
    assert undone.json()["status"] == "undone"
    assert adapter.snapshot.fields["genres"] == ["Rock"]


def test_preview_reports_invalid_audio_instead_of_returning_server_error(
    client, music_root
) -> None:
    path = music_root / "broken.mp3"
    path.write_bytes(b"not an mp3")
    stat = path.stat()
    tracks = client.app.state.track_repository
    tracks.replace_scan(
        [
            ScannedTrack(
                "broken.mp3",
                ".mp3",
                TrackFingerprint(stat.st_size, stat.st_mtime_ns),
            )
        ],
        datetime.now(timezone.utc),
    )
    result = client.app.state.result_repository.save(
        tracks.get_by_path("broken.mp3"),
        AnalysisResult(model_ids=["fake"]),
        ["Ambient"],
        ["Calm"],
    )

    response = client.post(
        "/api/writes/preview",
        json={"selection": {"mode": "ids", "ids": [result.id]}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_audio_file"
