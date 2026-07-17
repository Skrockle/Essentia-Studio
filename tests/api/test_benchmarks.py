import time
from datetime import datetime, timezone

from essentia_studio.domain.jobs import JobType
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint, TrackMetadata


def _wait_for_job(client, job_id: str) -> dict:
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.01)
    raise AssertionError(f"Job {job_id} did not finish")


def _add_sample(client, relative_path: str = "Artist/song.flac") -> None:
    client.app.state.track_repository.replace_scan(
        [
            ScannedTrack(
                relative_path=relative_path,
                extension=".flac",
                fingerprint=TrackFingerprint(100, 200),
                metadata=TrackMetadata("Artist", "Song", None, 61, "embedded"),
            )
        ],
        datetime.now(timezone.utc),
    )


def test_benchmark_is_manual_job_and_does_not_change_settings(client) -> None:
    _add_sample(client)
    before = client.get("/api/settings").json()

    created = client.post("/api/benchmarks")

    assert created.status_code == 202
    assert created.json()["type"] == "benchmark"
    assert _wait_for_job(client, created.json()["id"])["status"] == "completed"
    assert client.get("/api/settings").json() == before

    runs = client.get("/api/benchmarks").json()
    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
    assert runs[0]["current"] is True
    assert [measurement["compute"] for measurement in runs[0]["measurements"]] == ["cpu"]


def test_benchmark_requires_a_long_enough_sample(client) -> None:
    response = client.post("/api/benchmarks")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "benchmark_sample_missing"


def test_benchmark_rejects_other_active_jobs(client) -> None:
    _add_sample(client)
    client.app.state.job_repository.create(JobType.SCAN, ["music-root"], {})

    response = client.post("/api/benchmarks")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "benchmark_system_busy"


def test_apply_current_recommendation_updates_workers_explicitly(client) -> None:
    _add_sample(client)
    job = client.post("/api/benchmarks").json()
    assert _wait_for_job(client, job["id"])["status"] == "completed"
    run = client.get("/api/benchmarks").json()[0]

    response = client.post(f"/api/benchmarks/{run['id']}/apply")

    assert response.status_code == 200
    assert response.json()["values"]["analysis"]["workers"] == run["recommended_workers"]
    assert response.json()["sources"]["analysis.workers"] == "file"


def test_apply_rejects_stale_benchmark(client) -> None:
    _add_sample(client)
    job = client.post("/api/benchmarks").json()
    assert _wait_for_job(client, job["id"])["status"] == "completed"
    run = client.get("/api/benchmarks").json()[0]
    client.put("/api/settings", json={"benchmark": {"safety_margin_percent": 40}})

    response = client.post(f"/api/benchmarks/{run['id']}/apply")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "benchmark_stale"
