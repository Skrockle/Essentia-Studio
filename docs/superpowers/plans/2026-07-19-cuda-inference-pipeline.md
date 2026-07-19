# Persistent CUDA Inference Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CUDA per-track process pool with one persistent GPU inference process fed by bounded CPU preprocessing and micro-batched requests, while preserving the existing CPU backend and job contracts.

**Architecture:** CUDA analysis uses a long-lived pipeline owned by `ProcessAnalysisBackend`: CPU preprocessing workers decode and prepare bounded requests, a dispatcher forms batches, and exactly one spawned inference process owns the Essentia/TensorFlow models. Each request retains its job cancellation event and result event. CPU mode continues using the existing process pool. OOM recovery reduces the batch size, retries the batch, and recreates only the GPU process after unrecoverable failure.

**Tech Stack:** Python 3.10, `concurrent.futures`, `multiprocessing`, `queue`, NumPy, Essentia TensorFlow, FastAPI settings, pytest.

## Global Constraints

- CUDA uses one inference process per visible GPU; CPU worker count never creates additional model copies.
- Queues and batches are bounded; producers block rather than accumulating unbounded audio in RAM.
- Cancellation removes queued requests for the cancelled job and does not terminate unrelated work.
- CPU analysis and existing `AnalysisBackend`/job/result contracts remain compatible.
- A CUDA OOM has a bounded fallback path and a stable German application error when batch size one cannot run.
- Real CUDA inference is not claimed without an NVIDIA host; source tests use injected fake preprocessors/inference workers.
- Run focused tests first, then `python scripts/verify.py`; update documentation for new settings and benchmark output.

---

### Task 1: Define the pipeline contracts and configuration

**Files:**
- Create: `backend/essentia_studio/analysis/cuda_pipeline.py`
- Modify: `backend/essentia_studio/analysis/protocol.py`
- Modify: `backend/essentia_studio/schemas/settings.py`
- Modify: `backend/essentia_studio/services/settings.py`
- Test: `tests/analysis/test_cuda_pipeline.py`
- Test: `tests/services/test_settings_service.py`

**Interfaces:**
- `CudaPipelineSettings(cpu_workers: int, batch_size: int, queue_size: int)` validates positive CPU workers, batch sizes `1/2/4/8`, and a positive queue size.
- `CudaInferencePipeline.analyze(path, options, cancellation) -> AnalysisResult` is synchronous at the public boundary.
- `CudaInferencePipeline.cancel_job(job_id)` removes queued requests belonging to that job; request metadata carries `job_id` when supplied by the service.
- `AnalysisSettings` gains `cpu_workers`, `gpu_workers` (fixed to `1`), `gpu_batch_size`, and `gpu_queue_size`, while `workers` remains the compatibility alias used by existing jobs.

- [ ] Write tests for accepted batch sizes, rejected values, bounded queue construction, and environment variables `ESSENTIA_ANALYSIS_CPU_WORKERS`, `ESSENTIA_GPU_WORKERS`, `ESSENTIA_GPU_BATCH_SIZE`, and `ESSENTIA_GPU_QUEUE_SIZE`.
- [ ] Run the focused tests and confirm they fail because the pipeline/configuration contract is absent.
- [ ] Add the dataclasses/protocols and settings fields with defaults preserving current CPU behavior (`workers=1`, `gpu_workers=1`, `gpu_batch_size=1`, `gpu_queue_size=8`).
- [ ] Run the focused tests and Ruff for the changed files.

### Task 2: Implement bounded CPU preparation and persistent single-process inference

**Files:**
- Modify: `backend/essentia_studio/analysis/cuda_pipeline.py`
- Modify: `backend/essentia_studio/analysis/essentia_backend.py`
- Modify: `backend/essentia_studio/analysis/worker.py`
- Create: `tests/analysis/test_cuda_pipeline.py` cases for batching, reuse, backpressure, and fallback

**Interfaces:**
- `EssentiaBackend.prepare(path, options) -> PreparedAudio` performs only decode/resample/truncation and does not load TensorFlow graphs.
- `EssentiaBackend.analyze_prepared(audio, options) -> AnalysisResult` reuses already-loaded models.
- The spawned GPU entry point initializes one global `EssentiaBackend` once and processes a list of prepared requests.
- `CudaInferencePipeline.close()` stops dispatcher, preprocessing workers, and GPU process; it is idempotent.

- [ ] Add fake injected preparation/inference functions and tests proving two CPU workers feed one persistent inference worker, three requests form batches of configured size, and the model initializer runs once across multiple calls.
- [ ] Run the tests RED before implementation.
- [ ] Extract preparation and prepared inference from `EssentiaBackend` without changing the existing `analyze` behavior.
- [ ] Implement the bounded queue, CPU preparation executor, batch dispatcher, spawned GPU worker, request completion events, and clean shutdown.
- [ ] Run pipeline tests and the existing `tests/analysis/test_process_backend.py` tests.

### Task 3: Integrate CUDA selection, cancellation, and worker recovery

**Files:**
- Modify: `backend/essentia_studio/analysis/process_backend.py`
- Modify: `backend/essentia_studio/analysis/pool_manager.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `backend/essentia_studio/services/jobs.py`
- Modify: `backend/essentia_studio/services/analysis_jobs.py`
- Test: `tests/analysis/test_process_backend.py`
- Test: `tests/analysis/test_pool_manager.py`
- Test: `tests/services/test_jobs.py`

**Interfaces:**
- `ProcessAnalysisBackend` creates `CudaInferencePipeline` only when effective compute is `cuda`, and keeps the existing process pool for `cpu`.
- `ProcessAnalysisBackend.cancel()` cancels the active CUDA requests or terminates the CPU executor; it never affects another job's queued requests.
- CUDA OOM reduces batch size `4 -> 2 -> 1`, retries, records a fallback counter, and raises `analysis_cuda_oom` after batch one fails.
- `WorkerPoolManager` discards/recreates a broken backend after fatal CUDA or process-pool failure.

- [ ] Add failing tests for CUDA backend selection, model reuse, cancellation of queued requests, OOM fallback, and recreation after fatal worker failure.
- [ ] Implement settings propagation from `main.py`, preserving fake backend and CPU behavior.
- [ ] Register the existing analysis cancellation hook against the new backend manager and ensure cancelled jobs finish as `cancelled` with no normal item failure.
- [ ] Run focused backend/service tests and the recovery smoke script.

### Task 4: Make benchmarks exercise and report the pipeline

**Files:**
- Modify: `backend/essentia_studio/benchmark/runner.py`
- Modify: `backend/essentia_studio/benchmark/worker.py`
- Modify: `backend/essentia_studio/domain/benchmarks.py`
- Modify: `backend/essentia_studio/services/benchmarks.py`
- Modify: `backend/essentia_studio/schemas/benchmarks.py`
- Modify: `scripts/ci/benchmark_api_smoke.py`
- Test: `tests/benchmark/test_runner.py`
- Test: `tests/api/test_benchmarks.py`

**Interfaces:**
- Benchmark configuration records batch size and CPU preprocessing workers in the immutable snapshot.
- Measurements expose `tracks_per_minute`, `mean_seconds_per_track`, `initialization_seconds`, `batch_size`, and `cuda_oom_fallbacks`.
- `BenchmarkRunner` can run batch sizes `1`, `2`, and `4` serially; concurrent benchmark runs remain rejected.

- [ ] Add failing tests for batch-size coverage, throughput calculation, fallback count, CPU-only mode, and repeated runs.
- [ ] Extend the injected benchmark worker protocol and persistence mapping while keeping old records readable.
- [ ] Run focused benchmark tests and the benchmark API smoke script.

### Task 5: Documentation, source gate, and CUDA image verification

**Files:**
- Modify: `docs/deployment/linux-docker.md`
- Modify: `docs/deployment/windows.md`
- Modify: `docs/development.md`
- Modify: `README.md`
- Modify: `scripts/verify.py` only if a new deterministic check is required

- [ ] Document the CPU-worker/GPU-worker distinction, bounded queue, batch settings, OOM fallback, and benchmark interpretation in German/English project docs.
- [ ] Run the focused backend, benchmark, and settings tests.
- [ ] Run `.venv/bin/python scripts/verify.py` and fix only issue-related failures.
- [ ] Build the CUDA Dev image if Docker/build context is available; report separately that build success is not real GPU inference evidence.
- [ ] Review the final diff for secrets, private paths, generated artifacts, complexity, and unchanged CPU behavior.

