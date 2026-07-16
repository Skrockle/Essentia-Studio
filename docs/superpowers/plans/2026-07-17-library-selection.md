# Library Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show scanned tracks, analyze only explicitly selected tracks, report the scan count, and publish the service on host port 8080.

**Architecture:** A new frontend library hook loads all server-paginated tracks and owns no persistent state. `WorkbenchView` owns the analysis selection set and keeps it independent from result draft selection. Deployment maps configurable host port 8080 to unchanged container port 8000.

**Tech Stack:** React 19, TypeScript, Testing Library/Vitest, FastAPI, Apple Container, Docker Compose

## Global Constraints

- Preserve the existing result selection used for metadata writes.
- Never start analysis without explicit track IDs.
- Keep container port 8000 and use host port 8080.
- Keep the interface in German and follow existing workbench styling.

---

### Task 1: Scanned library selection

**Files:**
- Create: `frontend/src/features/workbench/useLibraryTracks.ts`
- Create: `frontend/src/features/workbench/LibraryTable.tsx`
- Modify: `frontend/src/features/workbench/types.ts`
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Test: `frontend/src/features/workbench/WorkbenchView.test.tsx`

**Interfaces:**
- Consumes: `GET /api/library/tracks?page=N&page_size=200&search=...`
- Produces: `useLibraryTracks(search)` with all matching tracks and async `refresh`; `LibraryTable` with numeric ID selection callbacks.

- [ ] Write a failing Workbench test that returns scanned tracks, selects one track, and expects `/api/analysis/jobs` to receive only that track ID.
- [ ] Run `npm test -- --run frontend/src/features/workbench/WorkbenchView.test.tsx` and confirm the scanned title is absent.
- [ ] Add typed library responses, paginated loading, the dedicated table, selection state, disabled empty analysis, and track-ID request body.
- [ ] Run the focused test and confirm it passes.
- [ ] Add a failing test for select-all and the visible scanned-track count, then implement the minimum behavior and rerun the focused test.

### Task 2: Scan completion count

**Files:**
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Test: `frontend/src/features/workbench/WorkbenchView.test.tsx`

**Interfaces:**
- Consumes: terminal scan event and `useLibraryTracks.refresh()`.
- Produces: `Scan abgeschlossen – N Titel gefunden` and refreshed result data.

- [ ] Add a failing event-driven test for the scan count.
- [ ] Reload tracks on scan completion, reconcile selection IDs, and display the returned total.
- [ ] Run the focused workbench test and confirm it passes.

### Task 3: Host port 8080

**Files:**
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Modify: `docs/deployment/apple-container.md`
- Test: `tests/docs/test_commands.py`

**Interfaces:**
- Produces: `${ESSENTIA_BIND:-0.0.0.0}:${ESSENTIA_PORT:-8080}:8000` and matching commands.

- [ ] Add a failing documentation test asserting the Compose host-port default.
- [ ] Update Compose and user-facing commands from host port 8000 to 8080.
- [ ] Run `pytest tests/docs/test_commands.py -q` and confirm it passes.

### Task 4: Verification and local replacement

**Files:** No production source changes.

- [ ] Run the complete backend test and Ruff suites.
- [ ] Run frontend tests, ESLint, TypeScript, and the Vite production build.
- [ ] Build `essentia-studio:local-cpu` with Apple Container for amd64.
- [ ] Stop the old `essentia-studio` container and start the new image at `0.0.0.0:8080:8000` with the existing `/music` and `/data` mounts.
- [ ] Verify `/health`, scanned library count, and the rendered frontend at localhost:8080.
- [ ] Commit and push the verified change.
