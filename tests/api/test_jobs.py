def test_terminal_job_events_can_be_replayed(client, music_root) -> None:
    (music_root / "song.flac").write_bytes(b"audio")
    job_id = client.post("/api/library/scan").json()["id"]

    response = client.get(f"/api/jobs/{job_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"kind":"terminal"' in response.text
