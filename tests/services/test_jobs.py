import logging
import time
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from threading import Event, Lock, Thread

from essentia_studio.analysis.pool_manager import WorkerPoolManager
from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.domain.jobs import JobStatus, JobType
from essentia_studio.errors import AppError
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.schemas.settings import AnalysisSettings
from essentia_studio.services.jobs import JobCoordinator


class PathAwareRecoveryBackend:
    def __init__(self, generation: int):
        self.generation = generation

    def analyze(self, path: Path, _options: AnalysisOptions, _cancellation=None) -> AnalysisResult:
        if path.name == "bad.flac":
            raise BrokenProcessPool("worker exited")
        return AnalysisResult(model_ids=[f"generation-{self.generation}"])

    def close(self) -> None:
        pass

    def model_inventory(self) -> list[dict[str, str]]:
        return []

    def available_compute(self) -> list[str]:
        return ["cpu"]


def test_cancelled_job_keeps_completed_items(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)
    first_started = Event()

    def handler(_job_id: str, item: str, cancelled: Event) -> dict[str, str]:
        first_started.set()
        if item == "b.flac":
            cancelled.set()
        return {"path": item}

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    job = coordinator.submit(JobType.ANALYSIS, ["a.flac", "b.flac", "c.flac"], {})
    coordinator.run_next_for_test()

    saved = repository.get(job.id)
    assert first_started.is_set()
    assert saved.status == JobStatus.CANCELLED
    assert saved.completed_items == 2
    assert saved.total_items == 3


def test_resume_copies_only_unfinished_items(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)

    def handler(_job_id: str, item: str, cancelled: Event) -> dict[str, str]:
        if item == "first.flac":
            cancelled.set()
        return {"path": item}

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    original = coordinator.submit(JobType.ANALYSIS, ["first.flac", "second.flac"], {"x": 1})
    coordinator.run_next_for_test()
    resumed = coordinator.resume(original.id)

    assert resumed.parent_job_id == original.id
    assert resumed.configuration == {"x": 1}
    assert repository.item_values(resumed.id) == ["second.flac"]


def test_start_requeues_jobs_left_active_by_previous_process(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)
    handled = Event()

    def handler(_job_id: str, item: str, _cancelled: Event) -> dict[str, str]:
        handled.set()
        return {"path": item}

    previous_coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    queued_job = previous_coordinator.submit(JobType.ANALYSIS, ["queued.flac"], {})
    repository.start(queued_job.id)

    restarted_coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    restarted_coordinator.start()
    try:
        assert handled.wait(timeout=1)
        deadline = time.monotonic() + 1
        while (
            time.monotonic() < deadline
            and repository.get(queued_job.id).status != JobStatus.COMPLETED
        ):
            time.sleep(0.01)
        assert repository.get(queued_job.id).status == JobStatus.COMPLETED
    finally:
        restarted_coordinator.stop()


def test_start_finishes_cancel_requested_job_left_by_previous_process(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)
    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: lambda *_: {}})
    job = coordinator.submit(JobType.ANALYSIS, ["cancelled.flac"], {})
    repository.request_cancel(job.id)

    coordinator.start()
    try:
        deadline = time.monotonic() + 1
        while (
            time.monotonic() < deadline
            and repository.get(job.id).status != JobStatus.CANCELLED
        ):
            time.sleep(0.01)
        assert repository.get(job.id).status == JobStatus.CANCELLED
    finally:
        coordinator.stop()


def test_item_failure_does_not_stop_remaining_items(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)

    def handler(_job_id: str, item: str, _cancelled: Event) -> dict[str, str]:
        if item == "bad.flac":
            raise ValueError("broken fixture")
        return {"path": item}

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    job = coordinator.submit(JobType.ANALYSIS, ["one.flac", "bad.flac", "two.flac"], {})
    coordinator.run_next_for_test()

    saved = repository.get(job.id)
    assert saved.status == JobStatus.COMPLETED_WITH_ERRORS
    assert saved.completed_items == 3
    assert saved.failed_items == 1
    items = repository.list_items(job.id)
    assert [item.status for item in items] == ["completed", "failed", "completed"]
    assert items[0].result == {"path": "one.flac"}
    assert items[1].error == "broken fixture"


def test_app_error_code_and_message_are_persisted_per_item(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)

    def handler(_job_id: str, _item: str, _cancelled: Event) -> dict[str, str]:
        raise AppError("analysis_worker_crashed", "Analyseprozess beendet", 500)

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    job = coordinator.submit(JobType.ANALYSIS, ["bad.flac"], {})
    coordinator.run_next_for_test()

    failed = repository.list_items(job.id)[0]
    assert failed.error_code == "analysis_worker_crashed"
    assert failed.error == "Analyseprozess beendet"


def test_app_error_logs_relative_item_and_original_cause(tmp_path, caplog) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)

    def handler(_job_id: str, _item: str, _cancelled: Event) -> dict[str, str]:
        try:
            raise BrokenProcessPool("worker exited")
        except BrokenProcessPool as cause:
            raise AppError(
                "analysis_worker_crashed",
                "Analyseprozess beendet",
                500,
            ) from cause

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    job = coordinator.submit(JobType.ANALYSIS, ["albums/bad.flac"], {})
    item_id = repository.pending_items(job.id)[0].id
    caplog.set_level(logging.ERROR, logger="essentia_studio.services.jobs")

    coordinator.run_next_for_test()

    record = next(
        record
        for record in caplog.records
        if record.name == "essentia_studio.services.jobs"
        and record.exc_info is not None
    )
    assert job.id in record.getMessage()
    assert str(item_id) in record.getMessage()
    assert "albums/bad.flac" in record.getMessage()
    assert "analysis_worker_crashed" in record.getMessage()
    logged_error = record.exc_info[1]
    assert isinstance(logged_error, AppError)
    assert isinstance(logged_error.__cause__, BrokenProcessPool)


def test_analysis_job_uses_configured_parallel_workers(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)
    lock = Lock()
    release = Event()
    two_started = Event()
    active = 0
    maximum_active = 0

    def handler(_job_id: str, item: str, _cancelled: Event) -> dict[str, str]:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
            if active == 2:
                two_started.set()
        release.wait(timeout=2)
        with lock:
            active -= 1
        return {"path": item}

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    job = coordinator.submit(
        JobType.ANALYSIS,
        ["one.flac", "two.flac", "three.flac"],
        {"worker_count": 2},
    )
    thread = Thread(target=coordinator.run_next_for_test)
    thread.start()

    assert two_started.wait(timeout=1)
    release.set()
    thread.join(timeout=2)

    assert maximum_active == 2
    assert repository.get(job.id).status == JobStatus.COMPLETED


def test_cancel_running_job_invokes_registered_cancellation_hook(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)
    started = Event()
    release = Event()
    hook_called = Event()

    def handler(_job_id: str, _item: str, cancelled: Event) -> dict[str, str]:
        started.set()
        release.wait(timeout=2)
        assert cancelled.is_set()
        return {"status": "cancelled"}

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    coordinator.register_cancellation_handler(JobType.ANALYSIS, hook_called.set)
    job = coordinator.submit(JobType.ANALYSIS, ["song.flac"], {})
    thread = Thread(target=coordinator.run_next_for_test)
    thread.start()

    assert started.wait(timeout=1)
    cancelled = coordinator.cancel(job.id)
    release.set()
    thread.join(timeout=2)

    assert hook_called.wait(timeout=1)
    assert cancelled.cancel_requested is True
    assert repository.get(job.id).status == JobStatus.CANCELLED


def test_repeated_worker_crash_does_not_stop_later_job_items(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)
    generation = 0

    def factory(_settings: AnalysisSettings) -> PathAwareRecoveryBackend:
        nonlocal generation
        generation += 1
        return PathAwareRecoveryBackend(generation)

    pool = WorkerPoolManager(factory, AnalysisSettings(workers=1))

    def handler(_job_id: str, item: str, _cancelled: Event) -> dict[str, object]:
        result = pool.analyze(Path(item), AnalysisOptions())
        return {"models": result.model_ids}

    coordinator = JobCoordinator(repository, {JobType.ANALYSIS: handler})
    job = coordinator.submit(JobType.ANALYSIS, ["bad.flac", "good.flac"], {})
    coordinator.run_next_for_test()

    saved = repository.get(job.id)
    items = repository.list_items(job.id)
    assert saved.status == JobStatus.COMPLETED_WITH_ERRORS
    assert [item.status for item in items] == ["failed", "completed"]
    assert items[0].error_code == "analysis_worker_crashed"
    assert items[1].result == {"models": ["generation-3"]}
