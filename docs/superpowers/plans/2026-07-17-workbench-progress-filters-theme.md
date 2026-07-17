# Workbench Progress, Filters, and Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add truthful live progress for analysis and writing, persistent table filters and columns, an accessible dark mode, clearer analysis help, and human-readable model names.

**Architecture:** Reuse the existing `JobCoordinator` and server-sent events for both analysis and serial write jobs, exposing job-item results through a read-only API. Keep per-browser display preferences in validated, versioned `localStorage`, while server settings remain YAML/env driven. Build focused React components for progress, view controls, theme selection, and setting help instead of expanding `WorkbenchView` further.

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy/SQLite, React 19, TypeScript, Vite, Vitest/Testing Library, Playwright, CSS custom properties, Apple Container.

## Global Constraints

- A title is complete only after a verified write; analyzed but unwritten titles remain visible.
- `written` tracks are hidden by default and can be explicitly shown again.
- Selection always targets the currently filtered rows.
- Theme, filters, and visible columns persist in versioned browser storage and safely fall back on invalid values.
- Writing remains preview-first and requires explicit confirmation.
- Write jobs process files serially and preserve the existing snapshots and undo semantics.
- File paths appear only in a dedicated optional `Datei` column, never beneath the title.
- All controls must work with mouse and keyboard in light and dark themes.
- Keep Windows, macOS, Linux, CPU-image, CUDA-image, and Apple Container behavior intact.

---

## File Structure

- `backend/essentia_studio/domain/jobs.py`: public job-item record.
- `backend/essentia_studio/repositories/jobs.py`: list job items including result/error.
- `backend/essentia_studio/schemas/jobs.py`: job-item API schema.
- `backend/essentia_studio/api/routes/jobs.py`: read-only job-item endpoint.
- `backend/essentia_studio/api/routes/writes.py`: submit write jobs.
- `backend/essentia_studio/main.py`: register serial write handler.
- `frontend/src/features/jobs/types.ts`: complete job and job-item frontend types.
- `frontend/src/features/jobs/useJobEvents.ts`: reset and reconnect-safe event state.
- `frontend/src/features/workbench/JobProgress.tsx`: reusable accessible progress display.
- `frontend/src/features/workbench/viewPreferences.ts`: validated versioned storage contract.
- `frontend/src/features/workbench/WorkbenchViewControls.tsx`: filters and column toggles.
- `frontend/src/features/workbench/LibraryTable.tsx`: filtered, configurable library columns.
- `frontend/src/features/workbench/ResultTable.tsx`: configurable result columns.
- `frontend/src/features/workbench/WritePreviewDialog.tsx`: write-job lifecycle and results.
- `frontend/src/features/workbench/WorkbenchView.tsx`: orchestration only.
- `frontend/src/app/theme.ts`: validated theme persistence and system resolution.
- `frontend/src/app/App.tsx`: apply theme and pass selector state.
- `frontend/src/components/AppNav.tsx`: theme selector.
- `frontend/src/features/settings/SettingField.tsx`: accessible help control.
- `frontend/src/features/settings/modelPresentation.ts`: model-role display mapping.
- `frontend/src/features/settings/SettingsView.tsx`: explanations and friendly model inventory.
- `frontend/src/styles/tokens.css`: semantic light/dark tokens.
- `frontend/src/styles/global.css`: component states, layout, contrast, progress.

---

### Task 1: Job Item API and Asynchronous Write Jobs

**Files:**
- Modify: `backend/essentia_studio/domain/jobs.py`
- Modify: `backend/essentia_studio/repositories/jobs.py`
- Modify: `backend/essentia_studio/schemas/jobs.py`
- Modify: `backend/essentia_studio/api/routes/jobs.py`
- Modify: `backend/essentia_studio/api/routes/writes.py`
- Modify: `backend/essentia_studio/main.py`
- Test: `tests/api/test_jobs.py`
- Test: `tests/api/test_writes.py`
- Test: `tests/services/test_jobs.py`

**Interfaces:**
- Produces: `JobItemRecord(id, job_id, position, value, status, result, error)`.
- Produces: `GET /api/jobs/{job_id}/items -> list[JobItemResponse]`.
- Produces: `POST /api/writes/jobs` accepting `WriteSelectionRequest` and returning `JobResponse` with status 202.
- Write handler result: `{"operation_id": str, "status": str, "relative_path": str}`; non-verified operations raise `AppError` so the job item is counted as failed.

- [ ] **Step 1: Write failing repository and API tests**

Add tests that create completed and failed job items and assert the detail response:

```python
response = client.get(f"/api/jobs/{job_id}/items")
assert response.status_code == 200
assert response.json() == [
    {
        "id": item_id,
        "job_id": job_id,
        "position": 0,
        "value": "Artist/song.flac",
        "status": "completed",
        "result": {"operation_id": "write-1", "status": "verified"},
        "error": None,
    }
]
```

Add a write API test that previews a selected result, submits `/api/writes/jobs`, runs the coordinator, and asserts `completed_items == 1`, `failed_items == 0`, plus a verified job-item result. Add the conflict variant and assert `completed_with_errors` and one failed item.

- [ ] **Step 2: Run focused backend tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/api/test_jobs.py tests/api/test_writes.py tests/services/test_jobs.py -q
```

Expected: failures because `/api/jobs/{job_id}/items` and `/api/writes/jobs` do not exist and `JobRepository` cannot list item details.

- [ ] **Step 3: Add the job-item record, repository query, schema, and route**

Implement this immutable domain contract:

```python
@dataclass(frozen=True, slots=True)
class JobItemRecord:
    id: int
    job_id: str
    position: int
    value: str
    status: str
    result: dict[str, Any] | None
    error: str | None
```

`JobRepository.list_items(job_id)` must query in `position` order, decode non-null JSON results, and return `JobItemRecord` values. `JobItemResponse.from_record()` mirrors the fields exactly. Add the route before `/{job_id}`-style dynamic ambiguity becomes relevant and use the repository dependency already present in `jobs.py`.

- [ ] **Step 4: Submit and process serial write jobs**

`POST /writes/jobs` resolves the selection once and submits the result IDs:

```python
return JobResponse.from_record(
    coordinator.submit(JobType.WRITE, result_ids, {"trigger": "manual"})
)
```

Register a `JobType.WRITE` handler in `main.py`:

```python
def write_handler(_job_id: str, result_id: str, _cancelled: Event) -> dict[str, str]:
    operation = tag_operation_service.write_one(result_id, "manual")
    if operation.status != "verified":
        raise AppError(
            operation.error_code or "write_not_verified",
            operation.error_message or "Die Tags konnten nicht verifiziert werden.",
            409,
        )
    return {
        "operation_id": operation.id,
        "status": operation.status,
        "relative_path": operation.relative_path,
    }
```

Do not add `worker_count`; `JobCoordinator._worker_count` already restricts parallel execution to analysis jobs.

- [ ] **Step 5: Run focused and full backend verification**

Run the focused command from Step 2, then:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check backend tests scripts
```

Expected: all tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 6: Commit Task 1**

```bash
git add backend/essentia_studio tests/api/test_jobs.py tests/api/test_writes.py tests/services/test_jobs.py
git commit -m "feat: run tag writes as observable jobs"
```

---

### Task 2: Truthful Analysis and Write Progress UI

**Files:**
- Create: `frontend/src/features/workbench/JobProgress.tsx`
- Create: `frontend/src/features/workbench/JobProgress.test.tsx`
- Modify: `frontend/src/features/jobs/types.ts`
- Modify: `frontend/src/features/jobs/useJobEvents.ts`
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.test.tsx`
- Modify: `frontend/src/features/workbench/WritePreviewDialog.tsx`
- Create: `frontend/src/features/workbench/WritePreviewDialog.test.tsx`

**Interfaces:**
- Consumes: `POST /api/writes/jobs`, `GET /api/jobs/{id}/items`, SSE progress/terminal events.
- Produces: `<JobProgress label job event />` with `role="progressbar"`, `aria-valuemin`, `aria-valuemax`, and `aria-valuenow`.
- Produces: write dialog states `preview | writing | summary`.
- Produces: `WriteJobSummary = { verified: number; failed: Array<{ relativePath: string; error: string }> }` passed to `onCompleted`.

- [ ] **Step 1: Write failing component and workbench tests**

Assert a progress event renders exact, accessible state:

```tsx
render(<JobProgress label="Analyse" job={job} event={{
  sequence: 2,
  kind: 'progress',
  payload: { total_items: 10, completed_items: 4, failed_items: 1 },
}} />)
expect(screen.getByRole('progressbar', { name: 'Analysefortschritt' })).toHaveAttribute('aria-valuenow', '40')
expect(screen.getByText('4 von 10 verarbeitet')).toBeVisible()
expect(screen.getByText('1 fehlgeschlagen')).toBeVisible()
```

In `WorkbenchView.test.tsx`, start a two-track analysis, emit progress `1/2`, and assert `50 %` before the terminal event. Simulate an EventSource error, return a terminal record from `GET /api/jobs/analysis-1`, and assert the UI reaches the terminal state instead of remaining busy. In the dialog test, confirm writing, assert `/api/writes/jobs` was called, emit progress, then terminal, and assert the summary is built from `/api/jobs/write-1/items`.

- [ ] **Step 2: Run frontend tests and verify RED**

```bash
npm --prefix frontend test -- JobProgress.test.tsx WorkbenchView.test.tsx WritePreviewDialog.test.tsx
```

Expected: failures because `JobProgress` and asynchronous write UI do not exist.

- [ ] **Step 3: Implement event state and progress component**

Export `JobEventPayload` and reset `lastEvent` plus `lastSequence.current` whenever `jobId` changes. Add an EventSource error listener that closes the source, fetches `/api/jobs/{jobId}`, and synthesizes a terminal event when the fetched job has a terminal status; otherwise expose a German connection error while retaining the active job. `JobProgress` computes:

```ts
const total = Number(event?.payload.total_items ?? job.total_items)
const completed = Number(event?.payload.completed_items ?? job.completed_items)
const failed = Number(event?.payload.failed_items ?? job.failed_items)
const percent = total > 0 ? Math.round((completed / total) * 100) : 0
const succeeded = Math.max(0, completed - failed)
```

Render a native-width visual bar plus accessible numeric attributes and separate success/error counts.

- [ ] **Step 4: Wire analysis and scan progress into WorkbenchView**

Replace `jobMessage()` and the plain notice with `JobProgress`. Preserve the existing terminal refresh and status messages. Do not clear the active job until the terminal event has been processed and the results/library refresh has completed.

- [ ] **Step 5: Convert WritePreviewDialog to job states**

After confirmation, submit the job and retain its record. Render `JobProgress` in the dialog while active. On terminal, fetch `JobItemRecord[]`, build `WriteJobSummary` from completed results and failed `value`/`error` pairs, render it, and call `onCompleted(summary)`. `WorkbenchView` refreshes results and sets its notice from `summary.verified`; it does not need complete `WriteOperation` objects. Keep the dialog open on partial failure and keep its close control available without cancelling an already submitted job.

- [ ] **Step 6: Run focused tests and commit**

```bash
npm --prefix frontend test -- JobProgress.test.tsx WorkbenchView.test.tsx WritePreviewDialog.test.tsx
git add frontend/src/features/jobs frontend/src/features/workbench
git commit -m "feat: show live analysis and write progress"
```

Expected: focused tests pass.

---

### Task 3: Persistent Filters and Configurable Columns

**Files:**
- Create: `frontend/src/features/workbench/viewPreferences.ts`
- Create: `frontend/src/features/workbench/viewPreferences.test.ts`
- Create: `frontend/src/features/workbench/WorkbenchViewControls.tsx`
- Create: `frontend/src/features/workbench/WorkbenchViewControls.test.tsx`
- Modify: `frontend/src/features/workbench/LibraryTable.tsx`
- Modify: `frontend/src/features/workbench/ResultTable.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.test.tsx`

**Interfaces:**
- Produces: `WorkbenchViewPreferencesV1` with `statuses`, `formats`, `showWritten`, `libraryColumns`, and `resultColumns`.
- Produces: `loadWorkbenchPreferences(storage)` and `saveWorkbenchPreferences(storage, value)`.
- Produces: column IDs `artist | title | file | album | format | status | genres | moods`; selection is never configurable.

- [ ] **Step 1: Write failing storage, filter, and table tests**

Test defaults and invalid JSON:

```ts
expect(loadWorkbenchPreferences(storage)).toEqual(DEFAULT_WORKBENCH_PREFERENCES)
storage.setItem(WORKBENCH_PREFERENCES_KEY, '{broken')
expect(loadWorkbenchPreferences(storage)).toEqual(DEFAULT_WORKBENCH_PREFERENCES)
```

Render a written and current track. Assert only current is visible by default; toggle „Vollständig geschriebene anzeigen“ and assert both appear. Hide `file` and assert no `Datei` header/path; re-enable it and assert the path is in its own cell while the title cell contains only the title.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
npm --prefix frontend test -- viewPreferences.test.ts WorkbenchViewControls.test.tsx WorkbenchView.test.tsx
```

Expected: failures because preferences and controls do not exist and paths remain in title cells.

- [ ] **Step 3: Implement validated versioned storage**

Use key `essentia-studio.workbench.v1`. Parse inside `try/catch`, intersect arrays with known constants, and merge missing fields with defaults. Defaults include all statuses except `written`, `showWritten: false`, all observed formats, and all columns visible. Never persist `Set`; store sorted arrays.

- [ ] **Step 4: Implement controls and filtering**

`WorkbenchViewControls` exposes multi-select checkbox groups for status/format and separate library/result column groups. Its reset button restores defaults. In `WorkbenchView`, derive filtered tracks with `useMemo`; exclude `written` unless `showWritten`, then require selected status and format. Pass filtered tracks to `LibraryTable`, and use the filtered IDs for selection/select-all.

When no rows match, render `Keine Titel entsprechen diesen Filtern.` and a unique `Filter zurücksetzen` button wired to `DEFAULT_WORKBENCH_PREFERENCES`.

- [ ] **Step 5: Split title and file cells in both tables**

Render cells conditionally by stable column ID. The title cell renders only:

```tsx
<strong className="track-title">{track.title}</strong>
```

The file cell renders only:

```tsx
<code className="track-path">{track.relative_path}</code>
```

Keep the checkbox accessible name based on `relative_path` so similarly named titles remain distinguishable.

- [ ] **Step 6: Run focused tests and commit**

```bash
npm --prefix frontend test -- viewPreferences.test.ts WorkbenchViewControls.test.tsx WorkbenchView.test.tsx
git add frontend/src/features/workbench
git commit -m "feat: persist workbench filters and columns"
```

---

### Task 4: Persistent System, Light, and Dark Themes

**Files:**
- Create: `frontend/src/app/theme.ts`
- Create: `frontend/src/app/theme.test.ts`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/components/AppNav.tsx`
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Produces: `ThemePreference = 'system' | 'light' | 'dark'`.
- Produces: `loadThemePreference`, `saveThemePreference`, and `resolveTheme(preference, prefersDark)`.
- Applies `document.documentElement.dataset.theme` as `light` or `dark` and sets `color-scheme`.

- [ ] **Step 1: Write failing theme persistence and App tests**

Assert invalid values become `system`, explicit dark wins, and system follows `matchMedia`. Render `App`, choose „Dunkel“, assert `data-theme="dark"` and persisted key `essentia-studio.theme.v1`; rerender and assert the selection remains.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
npm --prefix frontend test -- theme.test.ts App.test.tsx
```

Expected: failures because no theme contract or selector exists.

- [ ] **Step 3: Implement theme state and selector**

Use a labeled `<select aria-label="Darstellung">` in navigation with System, Hell, Dunkel. Subscribe to `matchMedia('(prefers-color-scheme: dark)')` only while preference is `system`; remove the listener on cleanup.

- [ ] **Step 4: Replace color assumptions with semantic tokens**

Define light and dark values for paper, surface, surface-subtle, ink, ink-muted, line, genre, mood, signal, success, danger, primary background/text/hover, focus ring, and overlay. Replace hard-coded white/black text in global styles with tokens. Ensure `.primary-button` always sets both `background` and `color`, including dialog specificity.

- [ ] **Step 5: Run tests and commit**

```bash
npm --prefix frontend test -- theme.test.ts App.test.tsx
git add frontend/src/app frontend/src/components/AppNav.tsx frontend/src/styles
git commit -m "feat: add persistent accessible themes"
```

---

### Task 5: Accessible Setting Help and Friendly Model Inventory

**Files:**
- Create: `frontend/src/features/settings/modelPresentation.ts`
- Create: `frontend/src/features/settings/modelPresentation.test.ts`
- Modify: `frontend/src/features/settings/SettingField.tsx`
- Create: `frontend/src/features/settings/SettingField.test.tsx`
- Modify: `frontend/src/features/settings/SettingsView.tsx`
- Create or modify: `frontend/src/features/settings/SettingsView.test.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- `SettingField` adds `explanation?: string`.
- Produces: `presentModels(models) -> Array<{ title: string; detail: string; files: ModelCapability[] }>` grouped by role.

- [ ] **Step 1: Write failing accessibility and presentation tests**

Assert the info button has accessible name `Genre-Schwelle erklären`, toggles a visible description, and the description ID is referenced by `aria-describedby`. Assert model roles yield `Klangmerkmale (Discogs EffNet)`, `Genre-Erkennung (Discogs 400)`, and `Mood-Erkennung (MTG Jamendo)` while `.pb` names appear only inside a `<details>` element.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
npm --prefix frontend test -- SettingField.test.tsx modelPresentation.test.ts SettingsView.test.tsx
```

Expected: failures because explanation controls and friendly model mapping do not exist.

- [ ] **Step 3: Implement accessible help**

Do not nest an interactive button inside the existing `<label>`. Refactor `SettingField` to a wrapper `<div>`, render a separate `<label htmlFor={id}>`, and use a button with `aria-expanded` and `aria-controls`. Show the same help on click and keyboard activation; CSS hover/focus may reveal it visually but must not be the only access path.

- [ ] **Step 4: Add exact explanations and model mapping**

Pass the approved German explanations for Worker, maximale Audiolänge, Anzahl Genres, Genre-Schwelle, and Mood-Schwelle. Group `embedding`, `genre`, `mood`, `genre_labels`, and `mood_labels`; keep filename and checksum in details.

- [ ] **Step 5: Run focused tests and commit**

```bash
npm --prefix frontend test -- SettingField.test.tsx modelPresentation.test.ts SettingsView.test.tsx
git add frontend/src/features/settings frontend/src/styles/global.css
git commit -m "feat: explain analysis settings and models"
```

---

### Task 6: Browser Flows, Visual QA, and Local Container Replacement

**Files:**
- Modify: `frontend/e2e/analysis-workbench.spec.ts`
- Create: `frontend/e2e/theme-and-filters.spec.ts`
- Modify: `scripts/verify.py` only if the new E2E file needs no special command change; otherwise leave it untouched.
- Modify: `README.md` and `docs/deployment/apple-container.md` only for new user-visible controls that require operational documentation.

**Interfaces:**
- Consumes all preceding tasks.
- Produces a verified local CPU image `essentia-studio:local-cpu` and running container `essentia-studio` on `0.0.0.0:8090:8000` with existing mounts.

- [ ] **Step 1: Extend E2E tests before final UI adjustments**

Cover scanning, selecting two tracks, observing a non-terminal progress bar, terminal analysis, filtering written rows, toggling the file column, persisting dark mode after reload, previewing writes, confirming, observing write progress, and displaying the verified summary. Add exact contrast regression by asserting the primary button's computed foreground differs from background and is visible in both themes.

- [ ] **Step 2: Run E2E and verify failures identify remaining gaps**

```bash
npm --prefix frontend run e2e
```

Expected before final adjustments: any remaining focus, copy, persistence, or dialog-state mismatch fails with a targeted locator assertion.

- [ ] **Step 3: Apply only the minimal UI/CSS corrections exposed by E2E**

Keep fixes scoped to the failing component. Do not change feature behavior or add unrelated styling. Run the failing spec after each correction until green.

- [ ] **Step 4: Run the complete repository gate**

```bash
.venv/bin/python scripts/verify.py
npm --prefix frontend run e2e
git diff --check
```

Expected: backend tests, Ruff, frontend tests, ESLint, TypeScript, Vite production build, and all Playwright flows pass; `git diff --check` is silent.

- [ ] **Step 5: Perform browser visual and accessibility QA**

Using the in-app browser, verify at normal desktop width and a narrow viewport:

- light/system/dark theme switching and persistence,
- readable primary/disabled buttons and dialog overlay,
- keyboard focus and help popovers,
- filter and column menus without overflow,
- progress bar updates and terminal summaries,
- zero console errors and no unexpected failed API requests.

Record concrete issues and fix them test-first. Re-run Step 4 after any source change.

- [ ] **Step 6: Build and replace the Apple Container instance**

```bash
container build --arch amd64 -f Dockerfile -t essentia-studio:local-cpu .
container stop essentia-studio
container run --arch amd64 --rm -d --name essentia-studio \
  --cpus 4 --memory 4g -p 0.0.0.0:8090:8000 \
  --volume /Users/justus/Music:/music \
  --volume /Users/justus/EssentiaStudio/data:/data \
  essentia-studio:local-cpu
```

Wait conditionally for `/health`, verify `/api/capabilities`, scan the real library, analyze one unwritten track, and confirm that a previously verified written track is hidden by default but recoverable with the filter. Do not write tags to an additional real file solely for testing without explicit user approval; use existing verified state for the visibility check.

- [ ] **Step 7: Commit, push, and monitor CI**

```bash
git add frontend/e2e README.md docs/deployment/apple-container.md
git commit -m "test: cover workbench themes and progress"
git push origin feat/metadata-automation-benchmark
gh pr checks 2 --repo Skrockle/Essentia-Studio --watch --interval 15
```

Expected: Ubuntu, macOS, Windows, Browser flows, CPU image, and CUDA image checks all complete successfully.
