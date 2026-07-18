from threading import Event, Lock
from time import sleep

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.jobs import JobStatus, JobType
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.services.jobs import JobCoordinator


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


def test_analysis_items_run_in_parallel_when_workers_are_configured(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    repository = JobRepository(engine)
    active = 0
    peak_active = 0
    state_lock = Lock()
    both_started = Event()

    def handler(_job_id: str, _item: str, _cancelled: Event) -> dict[str, str]:
        nonlocal active, peak_active
        with state_lock:
            active += 1
            peak_active = max(peak_active, active)
            if peak_active == 2:
                both_started.set()
        both_started.wait(timeout=2)
        sleep(0.01)
        with state_lock:
            active -= 1
        return {"path": "done"}

    coordinator = JobCoordinator(
        repository,
        {JobType.ANALYSIS: handler},
        worker_counts={JobType.ANALYSIS: 2},
    )
    job = coordinator.submit(JobType.ANALYSIS, ["a.flac", "b.flac"], {})
    coordinator.run_next_for_test()

    assert repository.get(job.id).status == JobStatus.COMPLETED
    assert peak_active == 2
