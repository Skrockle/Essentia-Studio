def test_terminal_job_events_can_be_replayed(client, music_root) -> None:
    (music_root / "song.flac").write_bytes(b"audio")
    job_id = client.post("/api/library/scan").json()["id"]

    response = client.get(f"/api/jobs/{job_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"kind":"terminal"' in response.text


def test_job_items_expose_results_and_errors(client, music_root) -> None:
    (music_root / "song.flac").write_bytes(b"audio")
    job_id = client.post("/api/library/scan").json()["id"]
    client.get(f"/api/jobs/{job_id}/events")

    response = client.get(f"/api/jobs/{job_id}/items")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "job_id": job_id,
            "position": 0,
            "value": "music-root",
            "status": "completed",
            "result": {"scanned": 1, "present": 1, "missing": 0},
            "error": None,
        }
    ]
