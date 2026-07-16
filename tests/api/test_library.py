import time


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
    assert tracks["items"][0]["relative_path"] == "Artist/song.flac"
