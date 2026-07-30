import time
from datetime import datetime, timezone

from essentia_studio.domain.tracks import (
    ManagedTagInventory,
    ScannedTrack,
    TrackFingerprint,
    TrackMetadata,
)


def test_scan_records_mounted_tracks_without_analysis(client, music_root) -> None:
    (music_root / "Artist").mkdir()
    (music_root / "Artist" / "song.flac").write_bytes(b"audio")

    response = client.post("/api/library/scan")
    assert response.status_code == 202
    job_id = response.json()["id"]

    for _ in range(50):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] != "queued" and job["status"] != "running":
            break
        time.sleep(0.01)

    tracks = client.get("/api/library/tracks").json()
    assert job["status"] == "completed"
    assert tracks["total"] == 1
    item = tracks["items"][0]
    assert item["relative_path"] == "Artist/song.flac"
    assert item["artist"] == "Artist"
    assert item["title"] == "song"
    assert item["processing_state"] == "new"

    searched = client.get("/api/library/tracks", params={"search": "artist"}).json()
    assert searched["total"] == 1


def test_library_filters_missing_file_tags_and_returns_inventory(client) -> None:
    client.app.state.track_repository.replace_scan(
        [
            ScannedTrack(
                "complete.flac",
                ".flac",
                TrackFingerprint(10, 100),
                TrackMetadata("Artist", "Complete", None, None, "embedded"),
                ManagedTagInventory(["Rock"], ["Calm"], "ok"),
            ),
            ScannedTrack(
                "genre-only.flac",
                ".flac",
                TrackFingerprint(10, 100),
                TrackMetadata("Artist", "Genre only", None, None, "embedded"),
                ManagedTagInventory(["Rock"], [], "ok"),
            ),
            ScannedTrack(
                "mood-only.flac",
                ".flac",
                TrackFingerprint(10, 100),
                TrackMetadata("Artist", "Mood only", None, None, "embedded"),
                ManagedTagInventory([], ["Calm"], "ok"),
            ),
            ScannedTrack(
                "empty.flac",
                ".flac",
                TrackFingerprint(10, 100),
                TrackMetadata("Artist", "Empty", None, None, "embedded"),
                ManagedTagInventory([], [], "ok"),
            ),
            ScannedTrack(
                "unreadable.flac",
                ".flac",
                TrackFingerprint(10, 100),
                TrackMetadata("Artist", "Unreadable", None, None, "embedded"),
                ManagedTagInventory([], [], "error", "managed_tags_unreadable"),
            ),
        ],
        datetime(2026, 7, 16, 10, tzinfo=timezone.utc),
    )

    missing_genre = client.get("/api/library/tracks", params={"missing_genre": True}).json()
    missing_mood = client.get("/api/library/tracks", params={"missing_mood": True}).json()
    missing_any = client.get(
        "/api/library/tracks",
        params={"missing_genre": True, "missing_mood": True},
    ).json()

    assert missing_genre["total"] == 2
    assert [track["relative_path"] for track in missing_genre["items"]] == [
        "empty.flac",
        "mood-only.flac",
    ]
    assert missing_mood["total"] == 2
    assert [track["relative_path"] for track in missing_mood["items"]] == [
        "empty.flac",
        "genre-only.flac",
    ]
    assert missing_any["total"] == 3
    assert [track["relative_path"] for track in missing_any["items"]] == [
        "empty.flac",
        "genre-only.flac",
        "mood-only.flac",
    ]
    assert missing_any["items"][0] == {
        "id": 4,
        "relative_path": "empty.flac",
        "extension": ".flac",
        "size": 10,
        "mtime_ns": 100,
        "last_seen": "2026-07-16T10:00:00Z",
        "present": True,
        "artist": "Artist",
        "title": "Empty",
        "album": None,
        "duration_seconds": None,
        "metadata_source": "embedded",
        "processing_state": "new",
        "managed_genres": [],
        "managed_moods": [],
        "managed_tags_status": "ok",
        "managed_tags_error_code": None,
    }
