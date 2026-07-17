# Analysis Worker Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover once from an abruptly terminated Essentia process pool, isolate a repeat crash to the affected track, persist a stable error code, and continue unrelated analysis items.

**Architecture:** `WorkerPoolManager` remains the sole owner of process-pool replacement and performs one bounded retry. The generic `JobCoordinator` persists structured `AppError` details without knowing about Essentia, while `JobRepository` exposes the error code through the existing job-item API. A deterministic container smoke check exercises the same recovery path without intentionally crashing a real TensorFlow process.

**Tech Stack:** Python 3.10, `concurrent.futures`, FastAPI, SQLAlchemy 2, SQLite migrations, pytest, Apple Container/Docker-compatible OCI images, GitHub Actions.

## Global Constraints

- At most two analysis attempts are permitted per track: the initial submission and one retry after `BrokenProcessPool`.
- Only `BrokenProcessPool` is retried; ordinary inference, decoding, cancellation, and validation errors keep their current behavior.
- A second pool crash raises `AppError` code `analysis_worker_crashed` with the approved German message.
- Concurrent callers replace one shared broken backend at most once and never close a newer backend.
- Successful unrelated tracks and partial results remain available; no whole-job restart is introduced.
- Analysis remains read-only and logs use mount-relative paths only.
- Development commands remain PowerShell-compatible and must work on macOS, Windows 11, and Linux.
- Hand-written Python cyclomatic complexity may not exceed 10.

---

### Task 1: Bounded worker-pool recovery

**Files:**
- Modify: `tests/analysis/test_pool_manager.py`
- Modify: `tests/services/test_jobs.py`
- Modify: `backend/essentia_studio/analysis/pool_manager.py`

**Interfaces:**
- Consumes: `AnalysisBackend.analyze(path, options)`, `BackendFactory`, `BrokenProcessPool`.
- Produces: unchanged `WorkerPoolManager.analyze(path: Path, options: AnalysisOptions) -> AnalysisResult`, now with one bounded recovery attempt.

- [x] **Step 1: Add deterministic crash backends and all recovery tests**

Add these imports and test support to `tests/analysis/test_pool_manager.py`:

```python
from concurrent.futures.process import BrokenProcessPool
from threading import Barrier


class CrashingBackend(FakeBackend):
    def __init__(self, workers: int, barrier: Barrier | None = None):
        super().__init__(workers)
        self.barrier = barrier

    def analyze(self, _path: Path, _options: AnalysisOptions) -> AnalysisResult:
        if self.barrier is not None:
            self.barrier.wait(timeout=2)
        raise BrokenProcessPool("worker exited")
```

Add the focused behavior test:

```python
def test_analyze_retries_once_with_replacement_after_broken_pool() -> None:
    created: list[FakeBackend] = []

    def factory(settings: AnalysisSettings) -> FakeBackend:
        backend = (
            CrashingBackend(settings.workers)
            if not created
            else FakeBackend(settings.workers)
        )
        created.append(backend)
        return backend

    manager = WorkerPoolManager(factory, AnalysisSettings(workers=1))

    result = manager.analyze(Path("song.flac"), AnalysisOptions())

    assert result == AnalysisResult()
    assert len(created) == 2
    assert created[0].closed is True
    assert created[1].closed is False
```

Add the repeat-crash and concurrent-caller tests before changing production code:

```python
def test_analyze_reports_stable_error_after_second_broken_pool() -> None:
    created: list[FakeBackend] = []

    def factory(settings: AnalysisSettings) -> FakeBackend:
        backend = CrashingBackend(settings.workers)
        created.append(backend)
        return backend

    manager = WorkerPoolManager(factory, AnalysisSettings(workers=1))

    with pytest.raises(AppError) as raised:
        manager.analyze(Path("song.flac"), AnalysisOptions())

    assert raised.value.code == "analysis_worker_crashed"
    assert "übrige Analyse wird fortgesetzt" in raised.value.message
    assert len(created) == 3
    assert created[0].closed is True
    assert created[1].closed is True
    assert created[2].closed is False


def test_concurrent_callers_share_one_replacement_for_a_broken_pool() -> None:
    barrier = Barrier(2)
    created: list[FakeBackend] = []

    def factory(settings: AnalysisSettings) -> FakeBackend:
        backend = (
            CrashingBackend(settings.workers, barrier)
            if not created
            else FakeBackend(settings.workers)
        )
        created.append(backend)
        return backend

    manager = WorkerPoolManager(factory, AnalysisSettings(workers=2))
    results: list[AnalysisResult] = []
    threads = [
        Thread(
            target=lambda path=Path(f"song-{index}.flac"): results.append(
                manager.analyze(path, AnalysisOptions())
            )
        )
        for index in range(2)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert len(results) == 2
    assert len(created) == 2
    assert created[0].closed is True
    assert created[1].closed is False
```

Add the following imports, backend, and multi-item regression to `tests/services/test_jobs.py`:

```python
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

from essentia_studio.analysis.pool_manager import WorkerPoolManager
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.schemas.settings import AnalysisSettings


class PathAwareRecoveryBackend:
    def __init__(self, generation: int):
        self.generation = generation

    def analyze(self, path: Path, _options: AnalysisOptions) -> AnalysisResult:
        if path.name == "bad.flac":
            raise BrokenProcessPool("worker exited")
        return AnalysisResult(model_ids=[f"generation-{self.generation}"])

    def close(self) -> None:
        pass

    def model_inventory(self) -> list[dict[str, str]]:
        return []

    def available_compute(self) -> list[str]:
        return ["cpu"]


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
    assert items[1].result == {"models": ["generation-3"]}
```

- [x] **Step 2: Run the test and verify RED**

Run:

```text
python -m pytest tests/analysis/test_pool_manager.py tests/services/test_jobs.py::test_repeated_worker_crash_does_not_stop_later_job_items -q
```

Expected: both tests FAIL because `BrokenProcessPool` escapes instead of retrying; the multi-item job records the later healthy item as failed.

- [x] **Step 3: Implement one bounded retry in the pool manager**

Replace `WorkerPoolManager.analyze` and add `_analyze_with_recovery` in `backend/essentia_studio/analysis/pool_manager.py`:

```python
    def analyze(self, path: Path, options: AnalysisOptions) -> AnalysisResult:
        with self._lock:
            self._active += 1
        try:
            return self._analyze_with_recovery(path, options)
        finally:
            with self._idle:
                self._active -= 1
                self._idle.notify_all()

    def _analyze_with_recovery(
        self,
        path: Path,
        options: AnalysisOptions,
    ) -> AnalysisResult:
        for attempt in range(2):
            with self._lock:
                backend = self._backend
            try:
                return backend.analyze(path, options)
            except BrokenProcessPool as error:
                self._discard_broken(backend)
                if attempt == 1:
                    raise AppError(
                        "analysis_worker_crashed",
                        "Der Analyseprozess wurde unerwartet beendet. "
                        "Dieser Titel wurde übersprungen; die übrige Analyse wird fortgesetzt.",
                        500,
                    ) from error
        raise AssertionError("unreachable")
```

Do not change `_discard_broken`: its identity check already ensures that only the thread holding the current broken backend replaces and closes it.

- [x] **Step 4: Run the focused test and verify GREEN**

Run:

```text
python -m pytest tests/analysis/test_pool_manager.py tests/services/test_jobs.py::test_repeated_worker_crash_does_not_stop_later_job_items -q
```

Expected: PASS.

- [x] **Step 5: Run all pool-manager tests and review readability**

Run:

```text
python -m pytest tests/analysis/test_pool_manager.py tests/services/test_jobs.py::test_repeated_worker_crash_does_not_stop_later_job_items -q
python -m ruff check backend/essentia_studio/analysis/pool_manager.py tests/analysis/test_pool_manager.py tests/services/test_jobs.py
```

Expected: all pool tests PASS and Ruff reports no issues. Confirm retry control flow is direct, the approved message appears once, and no arbitrary exceptions are caught.

- [x] **Step 6: Commit the isolated pool recovery**

```text
git add backend/essentia_studio/analysis/pool_manager.py tests/analysis/test_pool_manager.py tests/services/test_jobs.py
git commit -m "fix: recover terminated analysis workers"
```

### Task 2: Structured per-item error persistence

**Files:**
- Create: `backend/essentia_studio/db/migrations/0011_job_item_error_code.sql`
- Modify: `backend/essentia_studio/domain/jobs.py`
- Modify: `backend/essentia_studio/repositories/jobs.py`
- Modify: `backend/essentia_studio/services/jobs.py`
- Modify: `backend/essentia_studio/schemas/jobs.py`
- Modify: `tests/db/test_migrations.py`
- Modify: `tests/services/test_jobs.py`
- Modify: `tests/api/test_jobs.py`
- Modify: `frontend/src/features/jobs/types.ts`

**Interfaces:**
- Consumes: `AppError.code`, `AppError.message`, generic job handler exceptions.
- Produces: `JobItemRecord.error_code: str | None`, `JobRepository.fail_item(..., error: str, error_code: str | None = None)`, and API field `error_code`.

- [x] **Step 1: Write failing service and migration assertions**

In `tests/services/test_jobs.py`, import `AppError` and add:

```python
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
```

Update `tests/db/test_migrations.py` to expect versions 1 through 11 and assert the new column:

```python
    assert versions == list(range(1, 12))
    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(job_items)"))
        }
    assert "error_code" in columns
```

- [x] **Step 2: Run focused tests and verify RED**

Run:

```text
python -m pytest tests/services/test_jobs.py::test_app_error_code_and_message_are_persisted_per_item tests/db/test_migrations.py::test_migrations_are_idempotent -q
```

Expected: FAIL because `JobItemRecord` has no `error_code` and migration 11 does not exist.

- [x] **Step 3: Add the migration and structured repository field**

Create `backend/essentia_studio/db/migrations/0011_job_item_error_code.sql`:

```sql
ALTER TABLE job_items ADD COLUMN error_code TEXT;
```

Add `error_code: str | None` after `error` in `JobItemRecord`. In `JobRepository.list_items`, select `error_code` and pass `error_code=row.error_code` to the record.

Change `JobRepository.fail_item` to:

```python
    def fail_item(
        self,
        job_id: str,
        item_id: int,
        error: str,
        error_code: str | None = None,
    ) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE job_items SET status = 'failed', error = :error, "
                    "error_code = :error_code WHERE id = :id"
                ),
                {"id": item_id, "error": error, "error_code": error_code},
            )
            connection.execute(
                text(
                    """
                    UPDATE jobs SET completed_items = completed_items + 1,
                                    failed_items = failed_items + 1
                    WHERE id = :id
                    """
                ),
                {"id": job_id},
            )
            self._insert_event(connection, job_id, "progress", self._progress(connection, job_id))
```

- [x] **Step 4: Persist `AppError` without Essentia-specific coordinator logic**

Import `AppError` in `backend/essentia_studio/services/jobs.py` and replace its item exception block with:

```python
        except AppError as error:
            self._repository.fail_item(
                job_id,
                item_id,
                error.message,
                error_code=error.code,
            )
        except Exception as error:
            self._repository.fail_item(job_id, item_id, str(error))
```

This remains generic: any service-layer `AppError` receives structured persistence, while unexpected exceptions retain their existing text-only behavior.

- [x] **Step 5: Expose the stable code through API and TypeScript contracts**

Add `error_code: str | None` to `JobItemResponse` in `backend/essentia_studio/schemas/jobs.py` and `JobItemRecord` in `frontend/src/features/jobs/types.ts`.

Extend `test_repeated_worker_crash_does_not_stop_later_job_items` with:

```python
    assert items[0].error_code == "analysis_worker_crashed"
```

Update the expected object in `tests/api/test_jobs.py::test_job_items_expose_results_and_errors` with:

```python
            "error": None,
            "error_code": None,
```

- [x] **Step 6: Run structured-error tests and verify GREEN**

Run:

```text
python -m pytest tests/services/test_jobs.py tests/api/test_jobs.py tests/db/test_migrations.py -q
npm --prefix frontend run typecheck
```

Expected: all selected tests PASS and TypeScript reports no errors.

- [x] **Step 7: Commit structured job errors**

```text
git add backend/essentia_studio/db/migrations/0011_job_item_error_code.sql backend/essentia_studio/domain/jobs.py backend/essentia_studio/repositories/jobs.py backend/essentia_studio/services/jobs.py backend/essentia_studio/schemas/jobs.py tests/db/test_migrations.py tests/services/test_jobs.py tests/api/test_jobs.py frontend/src/features/jobs/types.ts
git commit -m "feat: persist structured job item errors"
```

### Task 3: Multi-item isolation and CPU-container recovery smoke

**Files:**
- Create: `scripts/worker_recovery_smoke.py`
- Modify: `Dockerfile`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `WorkerPoolManager`, `JobCoordinator`, the stable `analysis_worker_crashed` error contract.
- Produces: a deterministic CPU-image smoke command for the recovery path; source integration evidence comes from Task 1 and its structured error assertion from Task 2.

- [x] **Step 1: Create a deterministic container smoke script**

Create `scripts/worker_recovery_smoke.py`:

```python
"""Verify bounded process-pool recovery inside a production image."""

from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

from essentia_studio.analysis.pool_manager import WorkerPoolManager
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.schemas.settings import AnalysisSettings


class SmokeBackend:
    def __init__(self, should_crash: bool):
        self._should_crash = should_crash

    def analyze(self, _path: Path, _options: AnalysisOptions) -> AnalysisResult:
        if self._should_crash:
            raise BrokenProcessPool("intentional smoke failure")
        return AnalysisResult(model_ids=["recovered"])

    def close(self) -> None:
        pass

    def model_inventory(self) -> list[dict[str, str]]:
        return []

    def available_compute(self) -> list[str]:
        return ["cpu"]


def main() -> int:
    generation = 0

    def factory(_settings: AnalysisSettings) -> SmokeBackend:
        nonlocal generation
        generation += 1
        return SmokeBackend(should_crash=generation == 1)

    manager = WorkerPoolManager(factory, AnalysisSettings(workers=1))
    result = manager.analyze(Path("smoke.wav"), AnalysisOptions())
    if result.model_ids != ["recovered"] or generation != 2:
        raise RuntimeError("Analysis worker recovery smoke failed")
    print("Analysis worker recovery smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 2: Package and execute the smoke in CPU image CI**

Add to `Dockerfile` beside the existing CPU smoke copy:

```dockerfile
COPY scripts/worker_recovery_smoke.py /app/scripts/worker_recovery_smoke.py
```

Add to the CPU-image workflow after real CPU inference:

```yaml
          docker exec essentia-studio-cpu \
            python /app/scripts/worker_recovery_smoke.py
```

- [x] **Step 3: Run focused source verification**

Run:

```text
python -m pytest tests/analysis/test_pool_manager.py tests/services/test_jobs.py tests/api/test_jobs.py tests/db/test_migrations.py -q
python -m ruff check backend tests scripts
python -m pytest tests/ci/test_workflows.py tests/docs/test_commands.py -q
```

Expected: all selected tests PASS and Ruff reports no issues.

- [x] **Step 4: Rebuild and verify the local CPU image**

Run the repository's Apple Container-compatible image build and replace script, then execute:

```text
container exec essentia-studio python /app/scripts/worker_recovery_smoke.py
```

Expected: recovery smoke prints `Analysis worker recovery smoke passed`. The CPU-image CI separately runs real inference against its generated `/music/tone.wav` fixture and must emit non-empty genres, moods, and model identifiers.

- [x] **Step 5: Run the full source gate**

Run:

```text
python scripts/verify.py
```

Expected: Python tests, Ruff, frontend lint, Vitest, TypeScript, and frontend build all PASS.

- [x] **Step 6: Review scope and commit container evidence**

Confirm no arbitrary exceptions are retried, no host paths or audio files are committed, and no CUDA claim is made. Then commit:

```text
git add scripts/worker_recovery_smoke.py Dockerfile .github/workflows/ci.yml
git commit -m "test: verify analysis recovery in cpu image"
```

### Task 4: Delivery verification

**Files:**
- Modify: `docs/superpowers/plans/2026-07-17-analysis-worker-recovery.md` (checkboxes only)

**Interfaces:**
- Consumes: all completed tasks and the private GitHub CI workflow.
- Produces: pushed reviewable commits and direct evidence that the regression is fixed across source and CPU-image gates.

- [x] **Step 1: Inspect the final branch delta**

Run:

```text
git status --short
git diff --check origin/feat/metadata-automation-benchmark...HEAD
git log --oneline origin/feat/metadata-automation-benchmark..HEAD
```

Expected: only planned documentation and implementation commits; no whitespace errors or private media paths.

- [ ] **Step 2: Push and observe all PR checks**

Push `feat/metadata-automation-benchmark`, then observe PR #2 until these checks reach a terminal state:

- Source (`ubuntu-latest`)
- Source (`macos-latest`)
- Source (`windows-latest`)
- Browser flows
- CPU image
- CUDA image without GPU

Expected: all six checks PASS. CUDA success proves only build and CPU fallback; it does not prove NVIDIA inference.

- [ ] **Step 3: Report evidence and remaining scope**

Report the focused test counts, full source gate, local recovery smoke, real CPU inference, and GitHub check conclusions. Keep the separate open work explicit: write-preview merge semantics, finished-results table, remaining dark-mode/table styling, percentage thresholds/tooltips, full-format live writes, and real NVIDIA CUDA inference.
