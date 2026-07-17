from threading import Event, Lock, Thread

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
