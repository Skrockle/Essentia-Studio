# Analysis Worker Recovery Design

**Status:** Approved design pending written review

**Date:** 2026-07-17

## Goal

An abruptly terminated Essentia child process must not mark every remaining track in an analysis job as failed. The application recovers the process boundary once for the affected track, isolates a repeat failure to the currently active track, and continues unrelated work.

## Root cause

`ProcessAnalysisBackend` owns a shared `ProcessPoolExecutor`. When one child process terminates abruptly, every submission already using that executor raises `BrokenProcessPool`. `WorkerPoolManager` replaces the broken backend for future calls, but the call that detected the failure is not retried. Concurrent calls that still reference the discarded backend also fail. The job coordinator consequently records unrelated tracks as failed even though their audio was never evaluated by a healthy worker.

The observed library run demonstrates the failure mode: a 222-track job recorded 222 failures after one child-process termination. Later single- and two-track jobs completed successfully, confirming that the library files were not collectively invalid.

## Recovery behavior

`WorkerPoolManager.analyze()` permits at most two attempts for one track:

1. Submit the track to the current analysis backend.
2. If `BrokenProcessPool` is raised, atomically discard that backend when it is still current.
3. Acquire the current healthy backend and retry the same track once.
4. If the retry also raises `BrokenProcessPool`, discard the second broken backend and propagate a stable application error for that track.

Every subsequent track obtains the current backend, so a repeat failure remains isolated to the active item. There is no unbounded retry, backoff, or whole-job restart.

Multiple analysis threads may observe the same broken backend concurrently. Only the first thread replaces it; the others reuse the replacement for their retry. A thread must never close a newer backend created by another thread.

## User-visible errors

After two failed attempts the affected job item receives:

- machine code: `analysis_worker_crashed`;
- German message: `Der Analyseprozess wurde unerwartet beendet. Dieser Titel wurde übersprungen; die übrige Analyse wird fortgesetzt.`

The job ends as `completed_with_errors` when at least one track remains failed. Successful unrelated tracks and their analysis results remain available. The existing resume action can create a linked job for failed tracks.

Logs retain the original exception and identify the job item by its mount-relative path. They must not expose host paths.

## Boundaries

- The pool manager owns process recovery; the generic job coordinator continues to own per-item isolation and must not contain Essentia-specific logic.
- Model inference and audio files remain read-only.
- Cancellation is checked by the existing coordinator and is not converted into a retry.
- Exceptions other than `BrokenProcessPool` are not retried.
- Worker count and CPU/CUDA selection do not change automatically after a crash.

## Verification

Focused tests must prove:

1. A first `BrokenProcessPool` recreates the backend and returns the retry result.
2. Concurrent callers that observed one broken backend reuse its single replacement.
3. A second `BrokenProcessPool` becomes `analysis_worker_crashed`, leaves a fresh backend for later calls, and does not retry indefinitely.
4. A multi-item analysis job records the repeatedly crashing item as failed while later items complete.
5. Cancellation and ordinary analysis errors retain their existing behavior.

After focused tests pass, run `python scripts/verify.py`. Container verification uses a deterministic injected crashing backend for the recovery path; a real CPU inference run confirms that normal model execution still succeeds. CUDA performance or stability is not claimed without a real NVIDIA inference run.

## Out of scope

- Automatically reducing the configured worker count.
- Retrying arbitrary inference or decoding errors.
- Persisting an application-wide crash counter.
- Changing the Workbench layout, write-preview semantics, threshold controls, or dark-mode styling in this change.
