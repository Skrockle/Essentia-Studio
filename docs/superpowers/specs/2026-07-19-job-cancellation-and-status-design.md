# Job cancellation and status design

**Status:** Approved

**Date:** 2026-07-19

## Goal

Make every queued or running job visible, individually cancellable, and reliably
stoppable. A cancelled analysis must not leave TensorFlow worker processes alive or
keep the benchmark locked. A benchmark remains single-flight, but may be started
again after the previous run reaches a terminal state.

## Root cause

The global status bar reads the authoritative `GET /api/jobs` response. The API
returns all persisted jobs, including several queued/running jobs. The expanded
status list currently renders those jobs without actions, while only the selected
top job has a cancel button.

`JobCoordinator.cancel()` currently persists `cancel_requested` and sets a
cooperative `Event`. That is sufficient for queued work and benchmark workers, but
`ProcessAnalysisBackend` waits on a shared `ProcessPoolExecutor` future. A running
TensorFlow inference does not observe the event, so the analysis process can remain
alive and the job remains running.

## Design

### Job ownership and process lifecycle

The coordinator tracks cancellation callbacks for the currently running job. The
analysis backend registers a callback for the active analysis job. Cancelling a
queued job only marks it cancelled; cancelling the running analysis job also
terminates its analysis process pool and clears the pool so the next job gets fresh
workers. The coordinator then finalizes the job as `cancelled` and emits the normal
terminal event.

The coordinator remains the generic job lifecycle owner. It does not know TensorFlow
details; it invokes a registered job-type cancellation hook. Benchmark cancellation
continues to terminate its already isolated per-compute process. No two jobs run at
the same time, so terminating the active analysis pool cannot affect another job.

### Status UI

The status bar remains a single fixed element, centered within the app content area
and styled with existing light/dark theme tokens. The expanded list shows every
queued/running job with type, progress, ETA where available, and its own cancel
button. The top summary button cancels only the active top job. Cancel requests are
shown per job, and the list refreshes after the API response.

### Benchmark single-flight

The backend keeps the existing active-job guard, with an atomic test immediately
before creating a benchmark job. Terminal jobs never block a new benchmark. The UI
derives its disabled state from queued/running jobs and refreshes after terminal or
cancel events. A 409 remains a user-visible German error if another job wins a race.

## Error handling

- Cancelling a missing or terminal job returns the existing API error or current
  terminal record without starting a process.
- A cancelled analysis receives a terminal `cancelled` event and does not create
  additional item failures.
- Pool termination is followed by a fresh executor on the next analysis call.
- Existing worker-crash recovery remains unchanged for non-cancellation failures.
- Errors retain stable machine codes and German user-facing messages.

## Verification

Add focused tests for:

1. every active status-row job renders an enabled cancel action;
2. cancelling a queued job marks it terminal without invoking the process hook;
3. cancelling the running analysis job invokes the registered cancellation hook and
   emits a terminal event;
4. terminating an analysis pool leaves a fresh pool for the next job;
5. benchmark submission rejects a concurrent active job but succeeds again after a
   terminal job;
6. the status bar uses dark theme variables and is centered within the content
   column.

Run the focused tests and then `python scripts/verify.py`. Build and publish the
CUDA Dev image only after the source gate is green.
