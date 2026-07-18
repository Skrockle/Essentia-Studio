from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from essentia_studio.domain.jobs import JobRecord, JobStatus, JobType
from essentia_studio.domain.tracks import LibraryTrack, TrackFingerprint, TrackMetadata
from essentia_studio.services.automation import AutomationService
from essentia_studio.services.settings import SettingsService


def _track(track_id: int, path: str, size: int) -> LibraryTrack:
    return LibraryTrack(
        id=track_id,
        relative_path=path,
        extension=".flac",
        fingerprint=TrackFingerprint(size, size * 10),
        last_seen=datetime.now(timezone.utc),
        present=True,
        metadata=TrackMetadata("Artist", path, None, 120, "embedded"),
    )


class FakeCoordinator:
    def __init__(self) -> None:
        self.submissions: list[tuple[JobType, list[str], dict]] = []
        self.listeners = []

    def add_terminal_listener(self, listener) -> None:
        self.listeners.append(listener)

    def submit(self, job_type, items, configuration):
        self.submissions.append((job_type, list(items), configuration))
        return SimpleNamespace(id=f"job-{len(self.submissions)}")


class InlineCoordinator(FakeCoordinator):
    def submit(self, job_type, items, configuration):
        job = super().submit(job_type, items, configuration)
        terminal = JobRecord(
            id=job.id,
            type=job_type,
            status=JobStatus.COMPLETED,
            configuration=configuration,
            parent_job_id=None,
            total_items=len(items),
            completed_items=len(items),
            failed_items=0,
            cancel_requested=False,
        )
        for listener in self.listeners:
            listener(terminal)
        return job


class FakeTracks:
    def __init__(self, tracks: list[LibraryTrack]) -> None:
        self.tracks = tracks

    def query(self, *_args, **_kwargs):
        return self.tracks, len(self.tracks)


class FakeStates:
    def __init__(self, states: dict[int, str]) -> None:
        self.values = states

    def states(self, track_ids: list[int]):
        return {track_id: self.values[track_id] for track_id in track_ids}


class FakeResults:
    def __init__(self) -> None:
        self.by_job = {}

    def for_job(self, job_id: str):
        return self.by_job.get(job_id, [])


class FakeTags:
    def __init__(self) -> None:
        self.calls = []

    def write_many(self, result_ids: list[str], trigger: str = "manual") -> None:
        self.calls.append((result_ids, trigger))


def _service(tmp_path: Path, mode: str = "analyze"):
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "automation:\n  enabled: true\n  mode: " + mode + "\n",
        encoding="utf-8",
    )
    tracks = [
        _track(1, "new.flac", 10),
        _track(2, "current.flac", 20),
        _track(3, "changed.flac", 30),
    ]
    coordinator = FakeCoordinator()
    states = FakeStates({1: "new", 2: "current", 3: "changed"})
    results = FakeResults()
    tags = FakeTags()
    refreshes = []
    service = AutomationService(
        settings=SettingsService(settings_path, {}),
        tracks=FakeTracks(tracks),
        states=states,
        coordinator=coordinator,
        results=results,
        tag_operations=tags,
        refresh_library=lambda: refreshes.append(True),
    )
    return service, coordinator, states, results, tags, refreshes


def test_trigger_submits_only_new_and_changed_fingerprints_once(tmp_path: Path) -> None:
    service, coordinator, _states, _results, _tags, refreshes = _service(tmp_path)

    service.trigger("schedule")
    service.trigger("watcher")

    assert len(refreshes) == 2
    assert len(coordinator.submissions) == 1
    job_type, items, configuration = coordinator.submissions[0]
    assert job_type == JobType.ANALYSIS
    assert items == ["changed.flac", "new.flac"]
    assert configuration["trigger"] == "schedule"
    assert configuration["automation_mode"] == "analyze"


def test_auto_write_requires_opt_in_and_writes_only_current_results(tmp_path: Path) -> None:
    service, coordinator, states, results, tags, _refreshes = _service(
        tmp_path,
        "analyze_and_write",
    )
    service.trigger("schedule")
    results.by_job["job-1"] = [
        SimpleNamespace(id="result-1", track_id=1),
        SimpleNamespace(id="result-3", track_id=3),
    ]
    states.values[1] = "current"
    states.values[3] = "failed"

    coordinator.listeners[0](
        JobRecord(
            id="job-1",
            type=JobType.ANALYSIS,
            status=JobStatus.COMPLETED_WITH_ERRORS,
            configuration={"trigger": "schedule"},
            parent_job_id=None,
            total_items=2,
            completed_items=1,
            failed_items=1,
            cancel_requested=False,
        )
    )

    assert tags.calls == [(["result-1"], "automation")]


def test_analyze_mode_never_writes_after_completion(tmp_path: Path) -> None:
    service, coordinator, _states, results, tags, _refreshes = _service(tmp_path)
    service.trigger("schedule")
    results.by_job["job-1"] = [SimpleNamespace(id="result-1", track_id=1)]

    coordinator.listeners[0](
        JobRecord(
            id="job-1",
            type=JobType.ANALYSIS,
            status=JobStatus.COMPLETED,
            configuration={},
            parent_job_id=None,
            total_items=1,
            completed_items=1,
            failed_items=0,
            cancel_requested=False,
        )
    )

    assert tags.calls == []


def test_inline_terminal_event_releases_reserved_fingerprints(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text("automation:\n  enabled: true\n", encoding="utf-8")
    coordinator = InlineCoordinator()
    track = _track(1, "fast.flac", 10)
    service = AutomationService(
        settings=SettingsService(settings_path, {}),
        tracks=FakeTracks([track]),
        states=FakeStates({1: "new"}),
        coordinator=coordinator,
        results=FakeResults(),
        tag_operations=FakeTags(),
        refresh_library=lambda: None,
    )

    service.trigger("schedule")
    service.trigger("schedule")

    assert len(coordinator.submissions) == 2
