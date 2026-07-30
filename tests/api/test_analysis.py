import time
from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.jobs import JobType
from essentia_studio.domain.tracks import (
    ManagedTagInventory,
    ScannedTrack,
    TrackFingerprint,
    TrackMetadata,
)
from essentia_studio.services.analysis_admission import AnalysisAdmissionService
from essentia_studio.tags.protocol import ManagedTagSnapshot
from essentia_studio.tags.registry import TagAdapterRegistry


class SnapshotAdapter:
    def __init__(self, snapshots: dict[str, ManagedTagSnapshot]) -> None:
        self.snapshots = snapshots

    def read(self, path):
        return self.snapshots[path.name]

    def write(self, *_args) -> None:
        raise AssertionError("Analysis admission must not write tags")

    def restore(self, *_args) -> None:
        raise AssertionError("Analysis admission must not restore tags")


def install_admission(client, snapshots: dict[str, ManagedTagSnapshot]) -> None:
    client.app.state.analysis_admission_service = AnalysisAdmissionService(
        client.app.state.track_repository,
        TagAdapterRegistry(SnapshotAdapter(snapshots)),
        client.app.state.config.music_root,
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
    install_admission(
        client,
        {"a.flac": ManagedTagSnapshot("vorbis", {}), "z.flac": ManagedTagSnapshot("vorbis", {})},
    )
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
    install_admission(client, {"song.flac": ManagedTagSnapshot("vorbis", {})})
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


def test_analysis_rejects_unknown_selection_filter_fields(client, music_root) -> None:
    (music_root / "song.flac").write_bytes(b"song")
    scan_job = client.post("/api/library/scan").json()
    wait_for_job(client, scan_job["id"])
    install_admission(client, {"song.flac": ManagedTagSnapshot("vorbis", {})})
    track_id = client.get("/api/library/tracks").json()["items"][0]["id"]

    nested_filter = client.post(
        "/api/analysis/jobs",
        json={"query": {"missing_genres": True}},
    )
    root_filter = client.post(
        "/api/analysis/jobs",
        json={"track_ids": [track_id], "missing_genre": True},
    )
    valid_default = client.post("/api/analysis/jobs", json={"query": {}})

    assert nested_filter.status_code == 422
    assert root_filter.status_code == 422
    assert valid_default.status_code == 202
    assert valid_default.json()["configuration"]["selection"] == {
        "query": {
            "present": True,
            "missing_genre": False,
            "missing_mood": False,
        },
        "enable_genres": True,
        "enable_moods": True,
    }


def test_analysis_query_selects_the_same_missing_tag_set_as_the_library(client) -> None:
    names = ["complete.flac", "genre-only.flac", "mood-only.flac", "empty.flac", "unreadable.flac"]
    for name in names:
        (client.app.state.config.music_root / name).write_bytes(b"audio")
    install_admission(
        client,
        {
            "complete.flac": ManagedTagSnapshot("vorbis", {"genres": ["Rock"], "moods": ["Calm"]}),
            "genre-only.flac": ManagedTagSnapshot("vorbis", {"genres": ["Rock"]}),
            "mood-only.flac": ManagedTagSnapshot("vorbis", {"moods": ["Calm"]}),
            "empty.flac": ManagedTagSnapshot("vorbis", {}),
            "unreadable.flac": ManagedTagSnapshot("vorbis", {}),
        },
    )
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
    assert response.json()["configuration"]["heads_by_path"] == {
        "empty.flac": {"enable_genres": True, "enable_moods": True},
        "genre-only.flac": {"enable_genres": False, "enable_moods": True},
        "mood-only.flac": {"enable_genres": True, "enable_moods": False},
    }


def test_analysis_rejects_a_client_provided_complete_track(client) -> None:
    music_root = client.app.state.config.music_root
    (music_root / "complete.flac").write_bytes(b"audio")
    client.app.state.track_repository.replace_scan(
        [
            ScannedTrack(
                "complete.flac",
                ".flac",
                TrackFingerprint(5, 1),
                managed_tags=ManagedTagInventory(["Rock"], ["Calm"], "ok"),
            )
        ],
        datetime.now(timezone.utc),
    )
    track_id = client.app.state.track_repository.get_by_path("complete.flac").id
    install_admission(
        client,
        {"complete.flac": ManagedTagSnapshot("vorbis", {"genres": ["Rock"], "moods": ["Calm"]})},
    )

    response = client.post("/api/analysis/jobs", json={"track_ids": [track_id]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_missing_managed_tags"


def test_legacy_analysis_job_fails_without_a_per_track_tag_scope(client) -> None:
    job = client.app.state.job_coordinator.submit(
        JobType.ANALYSIS,
        ["legacy.flac"],
        {"analysis": asdict(AnalysisOptions())},
    )

    completed = wait_for_job(client, job.id)

    assert completed["status"] == "completed_with_errors"
    assert client.app.state.job_repository.list_items(job.id)[0].error_code == (
        "analysis_job_missing_tag_scope"
    )


def test_analysis_job_rejects_wrong_persisted_option_type_after_resume(client) -> None:
    configuration = _persisted_analysis_configuration()
    configuration["analysis"]["genre_count"] = "broken"
    original = client.app.state.job_coordinator.submit(
        JobType.ANALYSIS,
        ["legacy.flac"],
        configuration,
    )

    _assert_scope_failure(client, original.id)
    resumed = client.app.state.job_coordinator.resume(original.id)

    _assert_scope_failure(client, resumed.id)
    assert client.app.state.job_repository.get(resumed.id).parent_job_id == original.id


def test_analysis_job_rejects_persisted_snapshot_missing_an_option(client) -> None:
    configuration = _persisted_analysis_configuration()
    del configuration["analysis"]["mood_threshold"]
    job = client.app.state.job_coordinator.submit(
        JobType.ANALYSIS,
        ["legacy.flac"],
        configuration,
    )

    _assert_scope_failure(client, job.id)


def test_analysis_job_rejects_persisted_snapshot_with_no_enabled_head(client) -> None:
    configuration = _persisted_analysis_configuration()
    configuration["heads_by_path"]["legacy.flac"] = {
        "enable_genres": False,
        "enable_moods": False,
    }
    job = client.app.state.job_coordinator.submit(
        JobType.ANALYSIS,
        ["legacy.flac"],
        configuration,
    )

    _assert_scope_failure(client, job.id)


def test_analysis_job_rejects_non_boolean_persisted_head_flag(client) -> None:
    configuration = _persisted_analysis_configuration()
    configuration["heads_by_path"]["legacy.flac"]["enable_moods"] = 1
    job = client.app.state.job_coordinator.submit(
        JobType.ANALYSIS,
        ["legacy.flac"],
        configuration,
    )

    _assert_scope_failure(client, job.id)


def test_analysis_job_rejects_invalid_persisted_head_path(client) -> None:
    configuration = _persisted_analysis_configuration()
    configuration["heads_by_path"] = {
        "../legacy.flac": {"enable_genres": True, "enable_moods": False}
    }
    job = client.app.state.job_coordinator.submit(
        JobType.ANALYSIS,
        ["legacy.flac"],
        configuration,
    )

    _assert_scope_failure(client, job.id)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("genre_threshold", -0.01),
        ("genre_threshold", 10**400),
        ("mood_threshold", 1.01),
        ("genre_count", True),
        ("max_audio_seconds", 3601),
    ],
)
def test_analysis_job_rejects_out_of_range_or_boolean_persisted_option(
    client,
    field: str,
    invalid_value: object,
) -> None:
    configuration = _persisted_analysis_configuration()
    configuration["analysis"][field] = invalid_value
    job = client.app.state.job_coordinator.submit(
        JobType.ANALYSIS,
        ["legacy.flac"],
        configuration,
    )

    _assert_scope_failure(client, job.id)


def _persisted_analysis_configuration() -> dict:
    return {
        "analysis": asdict(AnalysisOptions()),
        "heads_by_path": {"legacy.flac": {"enable_genres": True, "enable_moods": False}},
    }


def _assert_scope_failure(client, job_id: str) -> None:
    assert wait_for_job(client, job_id)["status"] == "completed_with_errors"
    assert client.app.state.job_repository.list_items(job_id)[0].error_code == (
        "analysis_job_missing_tag_scope"
    )
