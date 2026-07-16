import time


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
    assert job["configuration"]["analysis"]["mood_threshold"] == 0.005
    assert wait_for_job(client, job["id"])["status"] == "completed"


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
