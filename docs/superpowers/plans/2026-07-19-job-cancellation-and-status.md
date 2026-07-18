# Job Cancellation and Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make persisted jobs individually cancellable, terminate the active analysis process pool on cancellation, keep benchmarks single-flight but repeatable after completion, and fix the centered dark-mode status bar.

**Architecture:** `JobCoordinator` will expose a generic cancellation hook for the currently running job. `ProcessAnalysisBackend` will terminate and discard its pool through `WorkerPoolManager`; the next analysis creates a fresh pool. The frontend will keep `/api/jobs` as the single source of truth, render one cancel action per active row, and use theme tokens for the fixed centered bar.

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy/SQLite, `ProcessPoolExecutor`, React, TypeScript, Vitest, Testing Library, CSS custom properties.

## Global Constraints

- Preserve canonical media paths and existing job/item state transitions.
- Do not terminate processes belonging to another job; only the active job's registered hook may terminate the analysis pool.
- Keep benchmark execution single-flight: one queued/running benchmark or other job at a time; terminal jobs do not block later runs.
- Preserve stable machine error codes and German user-visible messages.
- Run focused tests before `python scripts/verify.py`.
- Build and publish the CUDA Dev image only after the source gate is green.

---

### Task 1: Define failing cancellation and benchmark lifecycle tests

**Files:**
- Modify: `tests/services/test_jobs.py`
- Modify: `tests/api/test_benchmarks.py`
- Create: `tests/analysis/test_process_backend.py`

**Interfaces:**
- Tests will require `JobCoordinator.register_cancellation_handler(job_type, callback)`.
- Tests will require `ProcessAnalysisBackend.cancel()` to terminate the active executor and allow a later executor to be created.

- [ ] **Step 1: Write failing tests**

Add tests that register an analysis cancellation hook, cancel a running job, and assert the hook is called once; add a process-backend test with a fake executor whose `shutdown` is asserted and whose next submission creates a new executor; add a benchmark test that completes one run and successfully starts a second run.

- [ ] **Step 2: Run focused tests and verify the expected failures**

Run:

```bash
.venv/bin/python -m pytest tests/services/test_jobs.py tests/api/test_benchmarks.py tests/analysis/test_process_backend.py -q
```

Expected: failures for the missing cancellation hook/process termination behavior, while unrelated existing tests continue to pass.

### Task 2: Implement process ownership and hard cancellation

**Files:**
- Modify: `backend/essentia_studio/analysis/protocol.py`
- Modify: `backend/essentia_studio/analysis/process_backend.py`
- Modify: `backend/essentia_studio/analysis/pool_manager.py`
- Modify: `backend/essentia_studio/services/jobs.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `backend/essentia_studio/services/analysis_jobs.py`

**Interfaces:**
- `ProcessAnalysisBackend.cancel() -> None` terminates all processes in the active executor, shuts it down without waiting, and clears the executor reference.
- `WorkerPoolManager.cancel() -> None` calls the current backend's cancellation method when available and waits only for bookkeeping to settle.
- `JobCoordinator.register_cancellation_handler(job_type, handler) -> None` stores a callback and invokes it only when that job type is currently running.

- [ ] **Step 1: Add the smallest production implementation**

Expose the optional cancellation contract, implement executor termination using the executor's live worker process handles with guarded access, clear the pool after termination, add the coordinator's active-job hook map, and register `WorkerPoolManager.cancel` for `JobType.ANALYSIS` in application startup. Ensure queued-job cancellation only sets the database flag and does not kill a different active analysis.

- [ ] **Step 2: Propagate cancellation into the item handler**

Pass the existing cancellation event through `analysis_handler` and `AnalysisJobService.process`; check it before path work and before persisting results. A cancellation must raise the stable `analysis_cancelled` application error or return a cancellation result that the coordinator converts into the terminal cancelled state without recording a normal item failure.

- [ ] **Step 3: Run focused backend tests**

Run:

```bash
.venv/bin/python -m pytest tests/services/test_jobs.py tests/api/test_benchmarks.py tests/analysis/test_process_backend.py -q
```

Expected: all focused tests pass, including the new hook and pool recreation assertions.

### Task 3: Make active jobs individually cancellable in the UI

**Files:**
- Modify: `frontend/src/features/jobs/JobStatusBar.tsx`
- Modify: `frontend/src/features/jobs/useJobMonitor.tsx`
- Modify: `frontend/src/features/jobs/types.ts`
- Modify or create: `frontend/src/features/jobs/JobStatusBar.test.tsx`

**Interfaces:**
- `JobStatusBar` receives the existing `onCancel(jobId)` and renders it for every queued/running job in the expanded list.
- `useJobMonitor` keeps per-job cancellation state so one row does not disable unrelated rows.

- [ ] **Step 1: Add failing UI tests**

Render one running and two queued jobs, assert three distinct cancel buttons, click a queued job's button, and assert only that row enters the requested state. Add a dark-theme class/token assertion through computed styles or rendered class hooks if the test environment supports it.

- [ ] **Step 2: Implement per-job actions and refresh behavior**

Keep the summary action for the selected active job, add row-level cancel buttons, track a `Set`/map of cancelling IDs, and reload `/api/jobs` after each successful cancel. Preserve terminal jobs as history but exclude them from the active action list.

- [ ] **Step 3: Run focused frontend tests**

Run:

```bash
npm --prefix frontend test -- src/features/jobs/JobStatusBar.test.tsx
```

Expected: all status-bar tests pass.

### Task 4: Fix centered layout and dark-mode tokens

**Files:**
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/features/jobs/JobStatusBar.tsx`

**Interfaces:**
- The bar remains fixed and spans the content column using a centered `width`/`max-width` calculation rather than asymmetric `left` and `right` offsets.
- Background, border, track, button, and text colors use existing light/dark CSS variables; no hard-coded white or light-blue surfaces remain in the job-status block.

- [ ] **Step 1: Add a layout/style regression assertion**

Extend the status-bar test to assert the rendered status bar has the semantic theme class and that all active rows remain visible at desktop and mobile widths.

- [ ] **Step 2: Implement the CSS change**

Use the app content width as the alignment reference, center the bar with `left: 50%` and `transform: translateX(-50%)` plus responsive max-width, and replace literal colors with existing theme variables and a dedicated job-surface token only if no suitable token exists.

- [ ] **Step 3: Run frontend lint, tests, and typecheck**

Run:

```bash
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run typecheck
```

Expected: no lint/type errors and all frontend tests pass.

### Task 5: Verify, commit, and publish the CUDA Dev image

**Files:**
- Verify: all changed files and `docs/superpowers/specs/2026-07-19-job-cancellation-and-status-design.md`
- Modify: `docs/deployment/linux-docker.md` only if the final cancellation/update command needs documentation

**Interfaces:**
- The source gate is `python scripts/verify.py`.
- The CUDA image tag is `ghcr.io/skrockle/essentia-studio:dev-cuda`.

- [ ] **Step 1: Run the complete source gate**

Run:

```bash
.venv/bin/python scripts/verify.py
```

Expected: backend tests, Ruff, frontend lint/tests/typecheck, and production build all pass.

- [ ] **Step 2: Review the final diff and commit**

Confirm `.playwright-mcp/` and `essentia-light.png` remain ignored, then run:

```bash
git add backend frontend tests docs/superpowers/specs/2026-07-19-job-cancellation-and-status-design.md docs/superpowers/plans/2026-07-19-job-cancellation-and-status.md
git commit -m "fix: cancel jobs and stabilize status bar"
git push origin main
```

- [ ] **Step 3: Trigger and monitor the CUDA Dev workflow**

Run:

```bash
gh workflow run dev-images.yml --repo Skrockle/Essentia-Studio --ref main -f variant=cuda
gh run list --repo Skrockle/Essentia-Studio --workflow dev-images.yml --limit 3
```

Expected: the CUDA job completes successfully and publishes `dev-cuda`; only then report that the server may pull and recreate the CUDA container.
