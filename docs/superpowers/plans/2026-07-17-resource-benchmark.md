# Resource Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure one representative analysis safely, compare CPU with CUDA when available, and recommend a worker count that fits the container's actual RAM with a 30 percent reserve.

**Architecture:** Pure resource-probe and recommendation functions are separated from an isolated benchmark runner. Benchmark jobs persist immutable environment/model snapshots and measurements; a `WorkerPoolManager` applies only a current successful recommendation after explicit user action and rebuilds the pool outside active jobs.

**Tech Stack:** Python 3.10, Linux cgroup v1/v2 files, `resource`, TensorFlow/Essentia worker processes, SQLAlchemy 2, FastAPI/Pydantic 2, React 19, Vitest.

## Global Constraints

- Benchmark starts manually and never writes analysis results or tags.
- Use the shortest readable track of at least 60 seconds and a fixed 60-second sample.
- One warm-up and two measured passes per available compute mode.
- CUDA runs only when TensorFlow reports a visible GPU.
- Recommendation uses container limits, not host RAM, and reserves 30 percent.
- Recommendation is capped by visible CPU cores and configured maximum 64.
- CUDA defaults to one worker per visible GPU unless measured multi-GPU evidence exists.
- Applying a recommendation is a separate explicit action and is rejected during active jobs.

---

### Task 1: Container resource probe and pure recommendation

**Files:**
- Create: `backend/essentia_studio/benchmark/resources.py`
- Create: `backend/essentia_studio/benchmark/__init__.py`
- Create: `tests/benchmark/test_resources.py`

**Interfaces:**
- Produces: `ResourceLimits(memory_bytes: int | None, cpu_count: int)`.
- Produces: `detect_resource_limits(root: Path = Path("/")) -> ResourceLimits`.
- Produces: `recommend_workers(memory_limit, baseline_peak, worker_peak, cpu_count, safety_margin=0.30, maximum=64) -> int`.

- [ ] **Step 1: Write failing cgroup v2/v1 detection tests**

```python
def test_reads_cgroup_v2_memory_and_cpu_quota(tmp_path: Path) -> None:
    write(tmp_path, "sys/fs/cgroup/memory.max", "4294967296")
    write(tmp_path, "sys/fs/cgroup/cpu.max", "200000 100000")
    assert detect_resource_limits(tmp_path) == ResourceLimits(4294967296, 2)

def test_treats_max_as_unlimited(tmp_path: Path) -> None:
    write(tmp_path, "sys/fs/cgroup/memory.max", "max")
    assert detect_resource_limits(tmp_path).memory_bytes is None
```

- [ ] **Step 2: Verify RED and implement v2, v1, affinity, and host fallbacks**

Prefer cgroup v2; then v1; CPU quota is bounded by `len(os.sched_getaffinity(0))` where available and `os.cpu_count()` otherwise. Never return fewer than one CPU.

- [ ] **Step 3: Write failing recommendation boundary tests**

```python
def test_recommendation_reserves_memory_and_caps_cpu() -> None:
    assert recommend_workers(
        memory_limit=4_000, baseline_peak=400, worker_peak=900,
        cpu_count=8, safety_margin=0.30,
    ) == 2

def test_no_worker_when_one_does_not_fit() -> None:
    assert recommend_workers(1_000, 400, 900, 8, 0.30) == 0
```

- [ ] **Step 4: Implement formula and run tests**

`usable = floor(memory_limit * (1 - margin)) - baseline_peak`; recommendation is `min(floor(usable / worker_peak), cpu_count, maximum)` and never negative. Unlimited memory still caps at CPU count but is marked as an estimate in the caller.

Run: `.venv/bin/python -m pytest tests/benchmark/test_resources.py -q`

- [ ] **Step 5: Commit**

Commit: `feat: detect container resources for benchmark`

---

### Task 2: Persist benchmark runs and validity snapshots

**Files:**
- Create: `backend/essentia_studio/db/migrations/0007_benchmarks.sql`
- Create: `backend/essentia_studio/domain/benchmarks.py`
- Create: `backend/essentia_studio/repositories/benchmarks.py`
- Create: `tests/repositories/test_benchmarks.py`

**Interfaces:**
- Produces: `BenchmarkRun`, `ComputeMeasurement`, and `BenchmarkStatus`.
- Produces repository methods `create`, `record_measurement`, `finish`, `get`, `list`, and `current_for(snapshot_hash)`.

- [ ] **Step 1: Write failing persistence/currentness tests**

```python
def test_only_matching_environment_snapshot_is_current(repository):
    old = repository.create(snapshot_hash="old", sample_track_id=1)
    repository.finish(old.id, recommended_workers=2)
    assert repository.current_for("new") is None
    assert repository.current_for("old").id == old.id
```

- [ ] **Step 2: Verify RED and add normalized tables**

```sql
CREATE TABLE benchmark_runs (
  id TEXT PRIMARY KEY, status TEXT NOT NULL, sample_track_id INTEGER,
  sample_relative_path TEXT, sample_seconds REAL NOT NULL,
  snapshot_json TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
  recommended_workers INTEGER, error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at TEXT
);
CREATE TABLE benchmark_measurements (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES benchmark_runs(id),
  compute TEXT NOT NULL, warmup_seconds REAL, measured_seconds_json TEXT NOT NULL,
  baseline_peak_bytes INTEGER, worker_peak_bytes INTEGER,
  UNIQUE(run_id, compute)
);
```

- [ ] **Step 3: Implement immutable snapshot hashing and repository mapping**

Canonicalize JSON with sorted keys and compact separators before SHA-256. Snapshot includes RAM, CPUs, GPU names/memory, image variant, model IDs, and analysis options.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/repositories/test_benchmarks.py -q`

Commit: `feat: persist benchmark measurements`

---

### Task 3: Select sample and run isolated CPU/CUDA measurements

**Files:**
- Create: `backend/essentia_studio/benchmark/runner.py`
- Create: `backend/essentia_studio/benchmark/worker.py`
- Modify: `backend/essentia_studio/analysis/essentia_backend.py`
- Create: `tests/benchmark/test_runner.py`

**Interfaces:**
- Produces: `select_sample(tracks, minimum_seconds=60) -> LibraryTrack`.
- Produces: `BenchmarkRunner.run(sample, options, compute_modes, cancel) -> list[ComputeMeasurement]`.
- Worker result includes initialization seconds, warm-up seconds, two measured seconds, baseline/peak RSS, and model IDs.

- [ ] **Step 1: Write failing deterministic sample-selection tests**

```python
def test_selects_shortest_track_meeting_minimum() -> None:
    sample = select_sample([track(59), track(125), track(61)], minimum_seconds=60)
    assert sample.metadata.duration_seconds == 61
```

- [ ] **Step 2: Verify RED and implement sample selection with explicit no-sample error**

Sort by duration then relative path; require present files and finite durations.

- [ ] **Step 3: Write failing runner tests using an injected worker function and clock**

Assert warm-up is excluded from average, exactly two measurements are retained, CPU-only omits CUDA, cancellation stops before the next mode, and no result repository is called.

- [ ] **Step 4: Implement isolated process protocol**

Start one fresh process per compute mode with an explicit result pipe. In the child: set `CUDA_VISIBLE_DEVICES`, initialize models, analyze the fixed 60-second option, record `time.perf_counter`, and sample RSS using `resource.getrusage`. Return structured errors; parent enforces cancellation and terminates only its benchmark child.

- [ ] **Step 5: Add model-backed smoke marker test**

Mark a focused test `@pytest.mark.model` that runs the real CPU worker against a generated 60-second WAV when models exist. Standard unit tests use the injected fake worker.

- [ ] **Step 6: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/benchmark/test_runner.py -q`

Commit: `feat: run isolated analysis benchmark`

---

### Task 4: Benchmark jobs and API

**Files:**
- Modify: `backend/essentia_studio/domain/jobs.py`
- Create: `backend/essentia_studio/services/benchmarks.py`
- Create: `backend/essentia_studio/schemas/benchmarks.py`
- Create: `backend/essentia_studio/api/routes/benchmarks.py`
- Modify: `backend/essentia_studio/api/router.py`
- Modify: `backend/essentia_studio/api/dependencies.py`
- Modify: `backend/essentia_studio/main.py`
- Create: `tests/api/test_benchmarks.py`

**Interfaces:**
- Add `JobType.BENCHMARK` with one item containing the selected track path.
- `POST /api/benchmarks -> JobResponse`.
- `GET /api/benchmarks -> list[BenchmarkResponse]` with `current` marker.
- Benchmark service rejects start while any job is running with `benchmark_system_busy`.

- [ ] **Step 1: Write failing API lifecycle tests**

```python
def test_benchmark_is_manual_job_and_does_not_change_settings(client):
    before = client.get("/api/settings").json()
    created = client.post("/api/benchmarks")
    assert created.status_code == 202
    assert created.json()["type"] == "benchmark"
    assert client.get("/api/settings").json() == before
```

- [ ] **Step 2: Verify RED and register benchmark repository/service/handler**

The handler records progress per compute mode and finalizes the benchmark row before returning the run ID. Job item failures retain the benchmark error.

- [ ] **Step 3: Add busy/no-sample/CUDA-conditional tests**

CPU image snapshots contain one CPU measurement. CUDA image with no visible GPU also contains only CPU and a diagnostic. CUDA image with a fake visible GPU contains comparable CPU and CUDA measurements.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/api/test_benchmarks.py -q`

Commit: `feat: expose benchmark jobs and results`

---

### Task 5: Safely apply recommendations and rebuild worker pool

**Files:**
- Create: `backend/essentia_studio/analysis/pool_manager.py`
- Modify: `backend/essentia_studio/analysis/process_backend.py`
- Modify: `backend/essentia_studio/services/benchmarks.py`
- Modify: `backend/essentia_studio/api/routes/benchmarks.py`
- Modify: `backend/essentia_studio/main.py`
- Create: `tests/analysis/test_pool_manager.py`
- Modify: `tests/api/test_benchmarks.py`

**Interfaces:**
- Produces: `WorkerPoolManager.analyze`, `reconfigure(settings)`, `close`, and `is_busy`.
- `POST /api/benchmarks/{id}/apply` writes `analysis.workers` only for a successful current run with recommendation >= 1.

- [ ] **Step 1: Write failing safe-reconfigure tests**

```python
def test_reconfigure_closes_old_pool_only_when_idle(fake_backend_factory):
    manager = WorkerPoolManager(fake_backend_factory, settings(workers=1))
    manager.reconfigure(settings(workers=2))
    assert fake_backend_factory.closed_worker_counts == [1]

def test_reconfigure_rejects_active_analysis(manager):
    manager.mark_busy_for_test()
    with pytest.raises(AppError, match="Analysejob"):
        manager.reconfigure(settings(workers=2))
```

- [ ] **Step 2: Verify RED and implement synchronized pool lifecycle**

Protect pool swap and active count with one condition/lock. A broken process pool is discarded after item failure so the next analysis gets a fresh executor.

- [ ] **Step 3: Write failing apply API tests**

Reject failed, stale, zero-worker, and active-job runs. On success update YAML through `SettingsService`, reconfigure the manager, and return effective settings with source `file`.

- [ ] **Step 4: Implement endpoint and run tests**

Run: `.venv/bin/python -m pytest tests/analysis/test_pool_manager.py tests/api/test_benchmarks.py -q`

- [ ] **Step 5: Commit**

Commit: `feat: apply benchmark worker recommendation`

---

### Task 6: Benchmark settings interface

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/features/settings/BenchmarkPanel.tsx`
- Create: `frontend/src/features/settings/BenchmarkPanel.test.tsx`
- Modify: `frontend/src/features/settings/SettingsView.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes benchmark list/job SSE and apply endpoint.
- Renders CPU and optional CUDA timings, ratio, RAM measurement, recommendation, sample, snapshot age, and error.

- [ ] **Step 1: Write failing CPU-only result test**

```tsx
test('shows a worker recommendation without applying it', async () => {
  render(<BenchmarkPanel />)
  await userEvent.click(screen.getByRole('button', { name: 'Benchmark starten' }))
  expect(await screen.findByText('Empfohlen: 2 Worker')).toBeVisible()
  expect(updateSettingsCalls).toHaveLength(0)
})
```

- [ ] **Step 2: Write failing CUDA comparison and stale-result tests**

Assert a GPU result says e.g. `CUDA 2,4× schneller`; CPU-only does not render an empty CUDA card; stale snapshot disables apply with an explanation.

- [ ] **Step 3: Verify RED and implement panel**

Start is disabled while another job runs. Apply requires its own click and updates the displayed worker field only after API success. Show the exact sample track and 60-second window.

- [ ] **Step 4: Run frontend verification and commit**

Run: `npm --prefix frontend run lint && npm --prefix frontend test -- --run && npm --prefix frontend run typecheck && npm --prefix frontend run build`

Commit: `feat: add resource benchmark interface`

---

### Task 7: Container smoke tests and operational documentation

**Files:**
- Modify: `scripts/ci/generate_fixture.py`
- Create: `scripts/ci/benchmark_api_smoke.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/deployment/apple-container.md`
- Modify: `docs/deployment/linux-docker.md`
- Modify: `docs/deployment/windows.md`
- Modify: `tests/ci/test_workflows.py`
- Modify: `tests/docs/test_commands.py`

- [ ] **Step 1: Add failing CI contract tests**

Assert CPU image smoke starts with an explicit memory limit >= 4 GB where the runner supports it, generates a 60-second audio fixture, starts a benchmark, waits for terminal success, and confirms no write operation was created. CUDA workflow compares modes only on a GPU runner.

- [ ] **Step 2: Implement smoke script and workflow steps**

The script prints compact JSON with run ID, sample, CPU time, optional CUDA time, recommendation, and snapshot. It exits nonzero for failed jobs or missing CPU measurement.

- [ ] **Step 3: Document sizing and interpretation**

Explain the 4 GB starting recommendation, 30 percent reserve, why CUDA warnings are normal in CPU mode, why GPU workers are conservative, and when a saved benchmark becomes stale.

- [ ] **Step 4: Run complete verification**

Run: `.venv/bin/python scripts/verify.py`

Run: `docker build -t essentia-studio:benchmark-cpu -f Dockerfile .`

Run the CPU image with a 4 GB limit and execute `benchmark_api_smoke.py` against it.

- [ ] **Step 5: Commit**

Commit: `test: verify benchmark in cpu container`
