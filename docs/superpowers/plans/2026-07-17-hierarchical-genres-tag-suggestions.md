# Hierarchical Genres and Tag Suggestions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split hierarchical Discogs predictions into separate genre tags, repair exactly identifiable legacy drafts, and add an accessible model-backed suggestion list that still accepts free-form genre and mood values.

**Architecture:** Pure label functions in the domain layer define the canonical parent/child and mood formatting used by analysis, reconciliation, and the catalog service. `ResultRepository` owns the short idempotent SQL reconciliation, while a read-only tag-catalog service exposes normalized bundled labels at `/api/tag-options`. The Workbench fetches that catalog once and passes it into an isolated React combobox used by each tag editor.

**Tech Stack:** Python 3.10, FastAPI, Pydantic, SQLAlchemy/SQLite JSON, React 19, TypeScript 6, Vitest/Testing Library, Playwright, Apple Container.

## Global Constraints

- Raw model predictions and confidence values remain unchanged; only draft tags are expanded.
- `genre_count` continues to limit model predictions, not the number of expanded metadata values.
- Existing free-form values containing semicolons must never be split unless they exactly match a legacy value derived from that result's raw model labels.
- Catalog loading is read-only and offline; it uses only the configured bundled JSON model metadata.
- Manual edits remain draft-only until the existing explicit preview and write workflow.
- The combobox must support mouse, keyboard, free-form entry, light theme, dark theme, and reduced motion.
- No host paths, real music data, model files, or secrets enter tests or commits.
- Run `python scripts/verify.py` through `.venv/bin/python` and the relevant Playwright specification before completion.

---

### Task 1: Canonical Label Expansion

**Files:**
- Create: `backend/essentia_studio/domain/tag_labels.py`
- Modify: `backend/essentia_studio/services/labels.py`
- Modify: `backend/essentia_studio/services/analysis_jobs.py`
- Modify: `tests/services/test_labels.py`
- Modify: `tests/services/test_analysis_jobs.py`

**Interfaces:**
- Produces: `split_genre_label(raw_label: str) -> list[str]`
- Produces: `legacy_genre_label(raw_label: str) -> str`
- Produces: `format_mood_label(raw_label: str) -> str`
- Consumes: existing `normalize_tags(values: list[str]) -> list[str]`

- [x] **Step 1: Write failing pure-label tests**

Add assertions that establish the exact contract:

```python
from essentia_studio.domain.tag_labels import (
    format_mood_label,
    legacy_genre_label,
    split_genre_label,
)

def test_discogs_parent_and_child_become_separate_tags() -> None:
    assert split_genre_label("Funk / Soul---Contemporary R&B") == [
        "Funk / Soul",
        "Contemporary R&B",
    ]
    assert split_genre_label("Rock") == ["Rock"]
    assert split_genre_label("Electronic---") == ["Electronic"]
    assert legacy_genre_label("Electronic---House") == "Electronic; House"

def test_mood_uses_the_last_model_segment() -> None:
    assert format_mood_label("moodtheme---happy") == "Happy"
```

Update the analysis-service expectation to:

```python
assert stored.draft.genres == ["Electronic", "House"]
assert stored.draft.moods == ["Happy"]
```

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```text
.venv/bin/python -m pytest -q tests/services/test_labels.py tests/services/test_analysis_jobs.py
```

Expected: collection fails because `essentia_studio.domain.tag_labels` does not exist, or the old combined genre assertion fails.

- [x] **Step 3: Implement the pure functions and analysis expansion**

Create direct, side-effect-free functions:

```python
def split_genre_label(raw_label: str) -> list[str]:
    return [segment.strip() for segment in raw_label.split("---") if segment.strip()]

def legacy_genre_label(raw_label: str) -> str:
    return "; ".join(split_genre_label(raw_label))

def format_mood_label(raw_label: str) -> str:
    return raw_label.rsplit("---", maxsplit=1)[-1].strip().title()
```

Keep `normalize_tags` in `services/labels.py`, import/re-export the pure functions where existing callers need compatibility, and flatten predictions in `AnalysisJobService.process`:

```python
genres = normalize_tags([
    genre
    for prediction in result.genres
    for genre in split_genre_label(prediction.label)
])
moods = normalize_tags([format_mood_label(value.label) for value in result.moods])
```

- [x] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2. Expected: all focused label and analysis-service tests pass.

- [x] **Step 5: Review readability and commit**

Confirm that raw prediction handling, label formatting, and validation remain separate responsibilities. Commit:

```text
feat: split hierarchical genre predictions
```

---

### Task 2: Idempotent Legacy Draft Reconciliation

**Files:**
- Modify: `backend/essentia_studio/domain/tag_labels.py`
- Modify: `backend/essentia_studio/repositories/results.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `tests/repositories/test_results.py`

**Interfaces:**
- Consumes: `split_genre_label`, `legacy_genre_label`
- Produces: `rewrite_legacy_genres(draft_values: list[str], raw_labels: list[str]) -> list[str]`
- Produces: `ResultRepository.reconcile_hierarchical_genres() -> int`

- [x] **Step 1: Write failing reconciliation tests**

Add pure behavior coverage:

```python
def test_rewrite_replaces_only_exact_model_derived_values() -> None:
    assert rewrite_legacy_genres(
        ["Funk / Soul; Contemporary R&B", "Manual; Value"],
        ["Funk / Soul---Contemporary R&B"],
    ) == ["Funk / Soul", "Contemporary R&B", "Manual; Value"]
```

Add a repository integration test that inserts an analysis result with raw label
`Electronic---House`, changes its draft to include both the legacy combined value and
`Manual; Value`, records `selected`, `dirty`, and `status`, calls reconciliation twice,
and asserts:

```python
assert first_count == 1
assert second_count == 0
assert stored.draft.genres == ["Electronic", "House", "Manual; Value"]
assert selected_dirty_and_status_are_unchanged
```

- [x] **Step 2: Run the focused repository test and verify RED**

Run:

```text
.venv/bin/python -m pytest -q tests/repositories/test_results.py -k hierarchical
```

Expected: failure because the rewrite and repository method do not exist.

- [x] **Step 3: Implement exact-match rewriting**

Build replacements only from raw labels that expand to more than one value:

```python
def rewrite_legacy_genres(draft_values: list[str], raw_labels: list[str]) -> list[str]:
    replacements = {
        legacy_genre_label(raw): split_genre_label(raw)
        for raw in raw_labels
        if len(split_genre_label(raw)) > 1
    }
    expanded = [
        value
        for draft in draft_values
        for value in replacements.get(draft, [draft])
    ]
    return deduplicate_labels(expanded)
```

Keep the case-insensitive stable deduplication pure in `domain/tag_labels.py` so the
repository does not import a service. In `ResultRepository.reconcile_hierarchical_genres`,
select `result_id`, `raw_genres`, and draft `genres`, compute changed rows in Python,
and update only the `genres` column inside one `engine.begin()` transaction. Do not
touch `dirty`, `selected`, `status`, or `updated_at`.

- [x] **Step 4: Invoke reconciliation during startup**

Immediately after constructing `ResultRepository` in the FastAPI lifespan, call:

```python
result_repository.reconcile_hierarchical_genres()
```

This occurs after schema migrations and before job/automation threads start.

- [x] **Step 5: Run focused tests twice and verify idempotence**

Run:

```text
.venv/bin/python -m pytest -q tests/repositories/test_results.py -k hierarchical
```

Expected: all reconciliation tests pass, including the second no-op call.

- [x] **Step 6: Review transaction scope and commit**

Confirm there is one short transaction, no audio access, and no mutation of unrelated
draft fields. Commit:

```text
fix: reconcile legacy hierarchical genre drafts
```

---

### Task 3: Read-Only Model Tag Catalog API

**Files:**
- Create: `backend/essentia_studio/services/tag_catalog.py`
- Create: `backend/essentia_studio/schemas/tag_options.py`
- Create: `backend/essentia_studio/api/routes/tag_options.py`
- Modify: `backend/essentia_studio/api/dependencies.py`
- Modify: `backend/essentia_studio/api/router.py`
- Modify: `backend/essentia_studio/main.py`
- Create: `tests/services/test_tag_catalog.py`
- Create: `tests/api/test_tag_options.py`

**Interfaces:**
- Produces: `TagOptions(genres: list[str], moods: list[str])`
- Produces: `TagCatalogService(model_dir: Path).load() -> TagOptions`
- Produces: `GET /api/tag-options`

- [x] **Step 1: Write failing service tests with synthetic catalogs**

Create temporary JSON files with `classes` arrays and assert:

```python
assert service.load().genres == ["Contemporary R&B", "Funk / Soul", "Rock"]
assert service.load().moods == ["Happy", "Sad"]
```

Use duplicated and hierarchical source labels to prove sorting and deduplication. Add
missing-file and invalid-JSON cases expecting `AppError.code == "tag_catalog_unavailable"`
and a German message naming the unavailable catalog, without exposing a host path.

- [x] **Step 2: Run service tests and verify RED**

Run:

```text
.venv/bin/python -m pytest -q tests/services/test_tag_catalog.py
```

Expected: import failure because `TagCatalogService` does not exist.

- [x] **Step 3: Implement catalog loading**

Read exactly:

```text
genre_discogs400-discogs-effnet-1.json
mtg_jamendo_moodtheme-discogs-effnet-1.json
```

Validate that the JSON root contains `classes: list[str]`. Expand genres with
`split_genre_label`, format moods with `format_mood_label`, deduplicate
case-insensitively, and sort with `str.casefold`. Convert `OSError`, `JSONDecodeError`,
and invalid structure into the stable `AppError`.

- [x] **Step 4: Write the failing API contract test**

Configure a test app with temporary model metadata and assert:

```python
response = client.get("/api/tag-options")
assert response.status_code == 200
assert response.json() == {
    "genres": ["Contemporary R&B", "Funk / Soul"],
    "moods": ["Happy"],
}
```

Also assert the standard error envelope and code for missing metadata.

- [x] **Step 5: Wire the typed route and dependency**

Instantiate one `TagCatalogService(runtime_config.model_dir)` in lifespan state. Add a
dependency getter, typed `TagOptions` response model, router module, and include it in
the existing `/api` router without changing `/api/capabilities`.

- [x] **Step 6: Run service and API tests, then commit**

Run:

```text
.venv/bin/python -m pytest -q tests/services/test_tag_catalog.py tests/api/test_tag_options.py
```

Expected: all catalog tests pass. Commit:

```text
feat: expose model-backed tag options
```

---

### Task 4: Workbench Catalog State

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/features/workbench/useTagOptions.ts`
- Create: `frontend/src/features/workbench/useTagOptions.test.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Modify: `frontend/src/features/workbench/ResultTable.tsx`
- Modify: `frontend/src/features/workbench/ResultTable.test.tsx`

**Interfaces:**
- Consumes: `GET /api/tag-options`
- Produces: `TagOptions { genres: string[]; moods: string[] }`
- Produces: `useTagOptions() -> { options: TagOptions; error: string | null }`
- Extends: `ResultTableProps` with `tagOptions: TagOptions`

- [x] **Step 1: Write failing hook tests**

Mock a successful fetch and assert normalized response storage. Mock the API error and
assert the hook returns empty lists plus the German non-blocking message:

```text
Tag-Vorschläge konnten nicht geladen werden. Freie Eingaben sind weiterhin möglich.
```

- [x] **Step 2: Run hook tests and verify RED**

Run:

```text
npm --prefix frontend test -- --run src/features/workbench/useTagOptions.test.tsx
```

Expected: import failure because the hook does not exist.

- [x] **Step 3: Implement one catalog request per Workbench mount**

Use `apiRequest<TagOptions>('/api/tag-options')` inside an effect with an active flag.
Keep `{ genres: [], moods: [] }` as the fallback and never block result editing.

- [x] **Step 4: Pass options through the existing table boundary**

`WorkbenchView` calls the hook once, renders a compact `notice notice--error` when the
catalog fails, and passes `tagOptions` to `ResultTable`. `ResultTable` passes
`tagOptions.genres` to Genre editors and `tagOptions.moods` to Mood editors. Update
existing table fixtures to provide empty option arrays.

- [x] **Step 5: Run focused tests and commit**

Run:

```text
npm --prefix frontend test -- --run src/features/workbench/useTagOptions.test.tsx src/features/workbench/ResultTable.test.tsx
```

Expected: all focused Workbench tests pass. Commit:

```text
feat: load tag options in the workbench
```

---

### Task 5: Accessible Free-Form Tag Combobox

**Files:**
- Create: `frontend/src/features/workbench/TagCombobox.tsx`
- Create: `frontend/src/features/workbench/TagCombobox.test.tsx`
- Modify: `frontend/src/features/workbench/TagEditor.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Produces: `TagCombobox({ kind, options, selectedValues, onAdd })`
- Consumes: catalog strings and the existing `TagEditor.onChange` callback
- Preserves: maximum tag length `120`, case-insensitive duplicate prevention, Plus button

- [x] **Step 1: Write failing interaction tests**

Cover these user-visible behaviors with Testing Library and `userEvent`:

```text
- focus opens an unfiltered list excluding already selected values;
- typing "contemp" finds "Contemporary R&B";
- prefix matches precede substring matches;
- ArrowDown/ArrowUp updates aria-activedescendant;
- Enter adds the active option and clears the input;
- Enter with no active option adds "Eigener Stil";
- Escape closes without clearing typed text;
- clicking an option adds it;
- the Plus button is disabled for blank input;
- a case-insensitive duplicate is not emitted;
- blur closes the list.
```

- [x] **Step 2: Run combobox tests and verify RED**

Run:

```text
npm --prefix frontend test -- --run src/features/workbench/TagCombobox.test.tsx
```

Expected: import failure because the component does not exist.

- [x] **Step 3: Implement filtering and keyboard state directly**

Use at most eight visible suggestions. Compute two stable groups from unselected values:
prefix matches first, then other substring matches, each retaining catalog order. Track
`open`, `inputValue`, and `activeIndex`; clamp/reset the active index whenever the
filtered list changes.

The input must declare:

```tsx
role="combobox"
aria-autocomplete="list"
aria-expanded={open}
aria-controls={listboxId}
aria-activedescendant={activeOptionId}
```

Render the popup as `role="listbox"` and each entry as `role="option"` with
`aria-selected`. Use `onMouseDown(event.preventDefault())` before selection so a mouse
choice does not lose focus before it is applied.

- [x] **Step 4: Integrate with TagEditor**

Keep chips/removal in `TagEditor`. Replace only its form/input logic with
`TagCombobox`. On add, append when no case-insensitive duplicate exists, call the
existing `onChange`, then let the combobox clear itself.

- [x] **Step 5: Add theme-safe popup styles**

Make `.tag-editor__form` the positioning context. Add a popup below the input with
`position: absolute`, `z-index`, `max-height`, internal scroll, `var(--surface)`,
`var(--line)`, `var(--ink)`, and `var(--shadow-panel)`. Style the active option with
`var(--selection-surface)` and `var(--selection-line)`. Use the existing blue/purple
`data-kind` accents and do not add hard-coded light colors.

- [x] **Step 6: Run component tests, typecheck, and commit**

Run:

```text
npm --prefix frontend test -- --run src/features/workbench/TagCombobox.test.tsx src/features/workbench/ResultTable.test.tsx
npm --prefix frontend run typecheck
```

Expected: component tests and typecheck pass. Commit:

```text
feat: add tag suggestion combobox
```

---

### Task 6: Browser, Source Gate, and Local Container Verification

**Files:**
- Create: `frontend/e2e/tag-suggestions.spec.ts`
- Modify: `scripts/e2e_server.py` only if synthetic model catalogs are not already available to the E2E app
- Modify: `docs/superpowers/plans/2026-07-17-hierarchical-genres-tag-suggestions.md` (check completed tasks and record evidence)

**Interfaces:**
- Verifies: backend expansion, legacy reconciliation, catalog API, combobox interaction, themes, and Docker packaging

- [x] **Step 1: Write the failing Playwright workflow**

The test must analyze a fixture whose fake backend returns `Electronic---House`, then
assert separate `Electronic` and `House` chips. It opens the Genre combobox, selects a
catalog value by keyboard, adds a free value, opens the Mood combobox and selects a
mood by mouse, and verifies the draft API contains separate arrays.

Record the result-row bounding box before and after opening the popup and assert its
height is unchanged. Select dark theme and assert the listbox background has all RGB
channels below `100`; repeat in light theme and assert readable foreground/background
contrast is not identical.

- [x] **Step 2: Run Playwright and verify RED before final fixture wiring**

Run:

```text
npm --prefix frontend run e2e -- tag-suggestions.spec.ts
```

Expected: failure until the E2E model catalogs and final selectors are connected.

- [x] **Step 3: Add only the required synthetic E2E catalogs**

Create temporary genre and mood JSON metadata inside the E2E server's existing temp
root and point `ESSENTIA_MODEL_DIR` at it. Do not add real model metadata to the repo.

- [x] **Step 4: Run focused browser and complete source gates**

Run:

```text
npm --prefix frontend run e2e -- tag-suggestions.spec.ts
.venv/bin/python scripts/verify.py
```

Expected: Playwright passes; all Python tests, Ruff, ESLint, Vitest, TypeScript, and
production build pass.

- [x] **Step 5: Build and replace the Apple Container**

Preserve the current `/Users/justus/Music:/music` and
`/Users/justus/EssentiaStudio/data:/data` mounts, 4 CPUs, 4 GB RAM, and port mapping:

```text
container build --arch amd64 -f Dockerfile -t essentia-studio:local-cpu .
container stop essentia-studio
container run --arch amd64 --rm -d --name essentia-studio --cpus 4 --memory 4g -p 0.0.0.0:8090:8000 --volume /Users/justus/Music:/music --volume /Users/justus/EssentiaStudio/data:/data -e ESSENTIA_DATA_DIR=/data essentia-studio:local-cpu
```

- [x] **Step 6: Verify the real mounted workflow in the integrated browser**

Open `http://localhost:8090/`, confirm the existing `Funk / Soul; Contemporary R&B`
draft is now two chips without reanalysis, exercise Genre and Mood suggestions plus a
free value, remove the temporary manual changes before leaving the page, and inspect
container logs for API or reconciliation errors. Capture light/dark screenshots.

- [ ] **Step 7: Update evidence, commit, and push**

Check every completed plan item, record exact test counts and container/browser
evidence, run `git diff --check`, then commit:

```text
docs: record tag suggestion verification
```

Push `feat/metadata-automation-benchmark` to the private origin and confirm the draft
PR receives the new commits.

#### Verification evidence (2026-07-17)

- Focused Playwright: `tag-suggestions.spec.ts` passed in Chromium (1 test).
- Complete source gate: 182 Python tests passed, 1 skipped; Ruff and ESLint passed;
  46 Vitest tests passed; TypeScript typecheck and production build passed.
- Apple Container image `essentia-studio:local-cpu` built for `amd64` and replaced on
  port `8090` with 4 CPUs, 4 GB RAM, and the existing `/music` and `/data` mounts.
- Integrated browser confirmed two independent `Funk / Soul` and `Contemporary R&B`
  chips without reanalysis, catalog Genre/Mood selection, a free Genre value, and the
  Escape-then-click popup regression in both themes.
- Temporary manual values were removed. The API contains only the original separated
  genres and moods for `The Waves`; final container logs contain successful requests
  and no application, catalog, reconciliation, or API errors.
