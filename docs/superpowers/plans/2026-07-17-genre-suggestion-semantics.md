# Genre Suggestion Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the configured genre count limit visible draft tags, enforce the confidence threshold, and expose the strongest rejected prediction as an explicitly uncertain review aid.

**Architecture:** A focused pure selection function converts ranked model scores into accepted or rejected `Prediction` values without importing TensorFlow. The analysis service alone converts accepted hierarchical labels into the bounded draft tag list. The existing result API carries the acceptance state to a small Workbench presentation component; no schema migration is required because `Prediction.accepted` defaults to `True` when old JSON is read.

**Tech Stack:** Python 3.10, NumPy, FastAPI/Pydantic, SQLite JSON fields, React 19, TypeScript, Vitest, Playwright.

## Global Constraints

- `genre_count` is an upper bound for distinct visible draft tags after splitting and normalization.
- `genre_threshold` is strict: rejected predictions never enter a new draft.
- The strongest rejected prediction is review-only and is never written without an explicit user action.
- Existing stored analysis JSON without an acceptance flag remains readable and accepted by default.
- Existing drafts and audio metadata are never rewritten by startup migration.
- Filesystem and database boundaries remain unchanged; no absolute host path enters persisted application data.
- Focused tests precede every production change, and `python scripts/verify.py` plus the relevant serial Playwright flow are required before release.

---

### Task 1: Select model predictions by visible tag budget

**Files:**
- Create: `backend/essentia_studio/analysis/genre_selection.py`
- Modify: `backend/essentia_studio/domain/analysis.py`
- Modify: `backend/essentia_studio/analysis/essentia_backend.py`
- Test: `tests/analysis/test_genre_selection.py`

**Interfaces:**
- Consumes: ranked `labels: list[str]`, `scores: Sequence[float]`, `threshold: float`, and `visible_tag_limit: int`.
- Produces: `select_genre_predictions(labels: Sequence[str], scores: Sequence[float], threshold: float, visible_tag_limit: int) -> list[Prediction]` where accepted candidates have `accepted=True` and the single best rejected fallback has `accepted=False`.

- [x] **Step 1: Write failing selection tests**

```python
def test_selection_counts_split_visible_tags_and_stops_at_limit():
    selected = select_genre_predictions(
        ["Rock---Alternative Rock", "Electronic---House"],
        [0.9, 0.8],
        threshold=0.25,
        visible_tag_limit=3,
    )
    assert selected == [
        Prediction("Rock---Alternative Rock", 0.9),
        Prediction("Electronic---House", 0.8),
    ]


def test_selection_marks_best_below_threshold_as_rejected():
    selected = select_genre_predictions(
        ["Rock---Alternative Rock", "Electronic---House"],
        [0.11, 0.08],
        threshold=0.25,
        visible_tag_limit=3,
    )
    assert selected == [Prediction("Rock---Alternative Rock", 0.11, accepted=False)]
```

- [x] **Step 2: Run the tests and confirm RED**

Run: `python -m pytest tests/analysis/test_genre_selection.py -q`

Expected: collection fails because `genre_selection` and `Prediction.accepted` do not exist.

- [x] **Step 3: Implement the pure selector and wire the adapter**

Implement `Prediction.accepted: bool = True`. Rank candidates by score, accept only candidates meeting the threshold, count their distinct `split_genre_label(prediction.label)` values toward `visible_tag_limit`, and stop once the visible budget is met. If no candidate qualifies, return only the strongest candidate with `accepted=False`. Replace `_predict_genres` score filtering with this function.

- [x] **Step 4: Run focused tests and confirm GREEN**

Run: `python -m pytest tests/analysis/test_genre_selection.py -q`

Expected: all genre-selection tests pass.

- [x] **Step 5: Commit**

```bash
git add backend/essentia_studio/analysis/genre_selection.py backend/essentia_studio/domain/analysis.py backend/essentia_studio/analysis/essentia_backend.py tests/analysis/test_genre_selection.py
git commit -m "fix: enforce visible genre suggestion limits"
```

### Task 2: Keep rejected candidates out of drafts and expose their state

**Files:**
- Modify: `backend/essentia_studio/services/analysis_jobs.py`
- Modify: `backend/essentia_studio/schemas/results.py`
- Test: `tests/services/test_analysis_jobs.py`
- Test: `tests/api/test_results.py`

**Interfaces:**
- Consumes: `AnalysisResult.genres` with explicit `Prediction.accepted`.
- Produces: drafts containing at most `AnalysisOptions.genre_count` normalized accepted tags and `PredictionResponse.accepted: bool` in `/api/results`.

- [x] **Step 1: Write failing service and API tests**

```python
def test_analysis_excludes_rejected_genre_and_limits_split_draft_tags(tmp_path):
    result = AnalysisResult(genres=[
        Prediction("Rock---Alternative Rock", 0.9),
        Prediction("Electronic---House", 0.8),
        Prediction("Hip Hop---Cloud Rap", 0.1, accepted=False),
    ])
    stored = service.process(path, AnalysisOptions(genre_count=3))
    assert stored.draft.genres == ["Rock", "Alternative Rock", "Electronic"]


def test_results_api_exposes_rejected_prediction_explicitly(client, seeded_results):
    response = client.get("/api/results").json()["items"][0]
    assert response["genres"][0]["accepted"] is False
    assert response["draft"]["genres"] == []
```

- [x] **Step 2: Run the tests and confirm RED**

Run: `python -m pytest tests/services/test_analysis_jobs.py tests/api/test_results.py -q`

Expected: rejected genres enter the draft or the API omits `accepted`.

- [x] **Step 3: Implement draft filtering and API serialization**

Filter `result.genres` by `accepted`, split and normalize them, then slice the final list to `options.genre_count`. Add `accepted: bool` to `PredictionResponse`; old stored predictions remain accepted through the domain default.

- [x] **Step 4: Run focused tests and confirm GREEN**

Run: `python -m pytest tests/services/test_analysis_jobs.py tests/api/test_results.py -q`

Expected: all focused service and API tests pass.

- [x] **Step 5: Commit**

```bash
git add backend/essentia_studio/services/analysis_jobs.py backend/essentia_studio/schemas/results.py tests/services/test_analysis_jobs.py tests/api/test_results.py
git commit -m "fix: separate uncertain genre evidence from drafts"
```

### Task 3: Present uncertainty and correct the Settings language

**Files:**
- Create: `frontend/src/features/workbench/UncertainGenreSuggestion.tsx`
- Create: `frontend/src/features/workbench/UncertainGenreSuggestion.test.tsx`
- Modify: `frontend/src/features/workbench/ResultTable.tsx`
- Modify: `frontend/src/features/workbench/types.ts`
- Modify: `frontend/src/features/settings/SettingsView.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/features/workbench/ResultTable.test.tsx`
- Test: `frontend/src/app/App.test.tsx`

**Interfaces:**
- Consumes: `Prediction.accepted` and the existing `onSaveDraft` callback.
- Produces: a separate `Unter der Schwelle` presentation with confidence and an `Übernehmen` action that adds the split values to the editable draft.

- [x] **Step 1: Write failing component tests**

```tsx
test('shows a rejected candidate separately and accepts its split values', async () => {
  renderTable(resultRow({
    genres: [{ label: 'Rock---Alternative Rock', confidence: 0.116, accepted: false }],
    draft: { genres: [], moods: [], selected: false, dirty: false },
  }))
  expect(screen.getByText('Unter der Schwelle')).toBeVisible()
  expect(screen.getByText('11,6 %')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Unsichere Genres übernehmen' }))
  expect(onSaveDraft).toHaveBeenCalledWith(expect.anything(), ['Rock', 'Alternative Rock'], [])
})
```

Also assert that Settings renders `Maximale Genres` and explains that the threshold can yield fewer tags.

- [x] **Step 2: Run the tests and confirm RED**

Run: `npm --prefix frontend test -- --run ResultTable.test.tsx UncertainGenreSuggestion.test.tsx App.test.tsx`

Expected: the uncertain state and revised label are absent.

- [x] **Step 3: Implement the presentation**

Create a focused component that formats the confidence with the German locale, renders split labels separately, and calls `onAccept(splitValues)`. Render only predictions with `accepted === false`; never infer uncertainty from an empty or dirty draft. Update the Settings copy and add light/dark theme styles using existing CSS variables.

- [x] **Step 4: Run the tests and confirm GREEN**

Run: `npm --prefix frontend test -- --run ResultTable.test.tsx UncertainGenreSuggestion.test.tsx App.test.tsx`

Expected: all focused component tests pass.

- [x] **Step 5: Commit**

```bash
git add frontend/src/features/workbench/UncertainGenreSuggestion.tsx frontend/src/features/workbench/UncertainGenreSuggestion.test.tsx frontend/src/features/workbench/ResultTable.tsx frontend/src/features/workbench/types.ts frontend/src/features/settings/SettingsView.tsx frontend/src/styles.css frontend/src/features/workbench/ResultTable.test.tsx frontend/src/app/App.test.tsx
git commit -m "feat: show uncertain genre suggestions explicitly"
```

### Task 4: Browser regression, full gate, and release

**Files:**
- Modify: `backend/essentia_studio/analysis/fake_backend.py`
- Modify: `frontend/e2e/analysis-workbench.spec.ts`
- Modify: `docs/superpowers/plans/2026-07-17-genre-suggestion-semantics.md`

**Interfaces:**
- Consumes: fake-backend results and the public Workbench/API behavior from Tasks 1–3.
- Produces: deterministic Playwright evidence, a green source gate, merged `main`, a GitHub Release, and private CPU/CUDA GHCR images.

- [x] **Step 1: Add a failing deterministic browser case**

Make the fake backend return a rejected hierarchical genre for a fixture path containing `uncertain`, analyze that fixture, and assert that the result has no normal genre chips, displays `Unter der Schwelle`, and becomes an editable draft only after `Übernehmen` is clicked.

- [x] **Step 2: Run the browser case and confirm RED**

Run: `npm --prefix frontend run e2e -- analysis-workbench.spec.ts --workers=1`

Expected: the uncertain marker or explicit acceptance step is missing.

- [x] **Step 3: Complete the test fixture and confirm GREEN**

Run: `npm --prefix frontend run e2e -- analysis-workbench.spec.ts --workers=1`

Expected: the complete Workbench flow passes.

- [x] **Step 4: Run the full source gate**

Run: `python scripts/verify.py`

Expected: Python tests, Ruff, frontend tests, ESLint, TypeScript, and production build all pass.

- [x] **Step 5: Rebuild and verify the local Apple Container**

Rebuild the CPU image from the final source, replace the existing test container on port `8090` with the approved music and data mounts, and use the integrated browser to analyze a real test track. Verify the configured maximum, the strict threshold, explicit uncertainty, manual acceptance, dark mode, and clean application logs.

Local evidence on 2026-07-17:

- Source gate: 195 Python tests passed, 1 skipped; Ruff passed; 49 Vitest tests passed; ESLint, TypeScript, and the production build passed.
- Browser gate: all 6 Playwright flows passed serially in CI mode.
- Apple Container: `essentia-studio:local-cpu` built for `linux/amd64` and runs on port `8090` with 4 CPUs, 4 GB RAM, `/Users/justus/Music:/music`, and `/Users/justus/EssentiaStudio/data:/data`.
- Real inference: `Nocturnal Creatures` produced `Electronic---House` at `0.085770227`, below the active `0.25` threshold. The API returned `accepted: false`, the draft began with no genres, the Workbench showed `Unter der Schwelle`, and explicit acceptance created the editable `Electronic` and `House` tags.
- Dark mode uses the dark warning surface and the browser console contained no warnings or errors. Container logs contained only the expected CPU-image CUDA discovery warnings and successful model loading.

- [ ] **Step 6: Publish through the repository workflow**

Push `feat/metadata-automation-benchmark`, wait for all pull-request checks, mark Draft PR #2 ready, merge it without force-pushing, wait for Release Please to create/update its release PR, merge the release PR after green checks, then wait for the GitHub Release and both private GHCR image jobs.

- [ ] **Step 7: Record final evidence**

Mark this plan complete with exact local test counts, GitHub Actions run URLs, release tag/URL, and CPU/CUDA package publication evidence. Do not create another code commit after the release tag.
