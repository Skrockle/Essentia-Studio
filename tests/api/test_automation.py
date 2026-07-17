def test_disabled_automation_status_is_read_only(client) -> None:
    jobs_before = client.get("/api/jobs").json()

    response = client.get("/api/automation/status")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "trigger_mode": "disabled",
        "watcher_health": "disabled",
        "next_runs": [],
        "last_run": None,
        "last_error": None,
    }
    assert client.get("/api/jobs").json() == jobs_before
