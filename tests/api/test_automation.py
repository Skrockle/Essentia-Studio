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


def test_enabling_schedule_updates_status_without_restart(client) -> None:
    updated = client.put(
        "/api/settings",
        json={
            "automation": {
                "enabled": True,
                "watcher": False,
                "schedule": "0 3 * * *",
                "timezone": "Europe/Berlin",
            }
        },
    )

    assert updated.status_code == 200
    status = client.get("/api/automation/status").json()
    assert status["enabled"] is True
    assert status["trigger_mode"] == "schedule"
    assert status["watcher_health"] == "disabled"
    assert len(status["next_runs"]) == 3
