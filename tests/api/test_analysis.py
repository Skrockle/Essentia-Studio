import time
from datetime import datetime, timezone

from essentia_studio.domain.tracks import (
    ManagedTagInventory,
    ScannedTrack,
    TrackFingerprint,
    TrackMetadata,
)


def wait_for_job(client, job_id: str) -> dict:
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.01)
    raise AssertionError(f"Job {job_id} did not finish")


def test_analysis_job_snapshots_settings_and_orders_tracks(client, music_root) -> None:
    (music_root / "z.flac").write_bytes(b"z")
    (music_root / "a.flac").write_bytes(b"a")
    scan_job = client.post("/api/library/scan").json()
    wait_for_job(client, scan_job["id"])
    tracks = client.get("/api/library/tracks").json()["items"]

    response = client.post(
        "/api/analysis/jobs",
        json={
            "track_ids": [tracks[1]["id"], tracks[0]["id"]],
            "genre_threshold": 0.2,
            "enable_moods": True,
        },
    )

    assert response.status_code == 202
    job = response.json()
    assert job["configuration"]["analysis"]["genre_threshold"] == 0.2
    assert job["configuration"]["analysis"]["mood_threshold"] == 0.10
    assert wait_for_job(client, job["id"])["status"] == "completed"


def test_analysis_job_uses_cpu_worker_setting_for_job_parallelism(client, music_root) -> None:
    (music_root / "song.flac").write_bytes(b"song")
    scan_job = client.post("/api/library/scan").json()
    wait_for_job(client, scan_job["id"])
    track_id = client.get("/api/library/tracks").json()["items"][0]["id"]

    settings = client.put("/api/settings", json={"analysis": {"cpu_workers": 8}})
    assert settings.status_code == 200

    response = client.post("/api/analysis/jobs", json={"track_ids": [track_id]})

    assert response.status_code == 202
    assert response.json()["configuration"]["worker_count"] == 8
    wait_for_job(client, response.json()["id"])


def test_analysis_rejects_empty_selection_and_disabled_heads(client) -> None:
    empty = client.post("/api/analysis/jobs", json={"track_ids": []})
    disabled = client.post(
        "/api/analysis/jobs",
        json={"track_ids": [1], "enable_genres": False, "enable_moods": False},
    )

    assert empty.status_code == 422
    assert disabled.status_code == 422


def test_analysis_query_rejects_no_matching_tracks(client) -> None:
    response = client.post(
        "/api/analysis/jobs",
        json={"query": {"search": "does-not-exist"}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_selection"


def test_analysis_query_selects_the_same_missing_tag_set_as_the_library(client) -> None:
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

    response = client.post(
        "/api/analysis/jobs",
        json={"query": {"missing_genre": True, "missing_mood": True}},
    )

    assert response.status_code == 202
    assert response.json()["total_items"] == 3
    assert client.app.state.job_repository.item_values(response.json()["id"]) == [
        "empty.flac",
        "genre-only.flac",
        "mood-only.flac",
    ]
