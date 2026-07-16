# Essentia Studio Analysis Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the complete mounted-library workflow: safe scan, persisted analysis jobs, live progress, genre/mood drafts, manual editing, selective verified writes, and tag-level undo.

**Architecture:** Domain types and filesystem safety are independent of FastAPI and Essentia. A persisted coordinator schedules scan, analysis, write, and undo work; an analysis protocol allows fast tests and a process-backed Essentia implementation; format adapters isolate Mutagen behavior; React views consume stable paginated APIs and SSE job events.

**Tech Stack:** Foundation stack plus Essentia TensorFlow `2.1b6.dev1389`, Mutagen, NumPy, multiprocessing, FastAPI SSE, React 19, Vitest, Playwright.

## Global Constraints

- Analysis is read-only and never calls a tag writer.
- Only relative paths canonically contained beneath the configured music root are accepted.
- Supported extensions are `.flac`, `.mp3`, `.ogg`, `.oga`, `.opus`, `.m4a`, `.m4b`, `.mp4`, `.aac`, `.wma`, `.aiff`, `.aif`, `.wav`, `.dsf`, `.wv`, `.ape`, `.mpc`, and `.mp+`.
- A track fingerprint is `(size, mtime_ns)`; a write also re-reads the managed tags before mutating.
- Every analysis result is persisted immediately and remains available after cancellation or browser disconnect.
- Select-all applies to the complete filtered result set represented by the current query, not merely the rendered page.
- Genre and mood values are trimmed, Unicode-normalized, case-insensitively deduplicated, limited to 64 values, and limited to 120 characters each.
- One item failure never aborts unrelated items in the same batch.
- A write is successful only after format-specific read-back verification.
- Undo restores only the exact managed tag snapshot and only while the post-write fingerprint still matches.
- Keep orchestration, inference, filesystem, tag-format, and HTTP concerns in separate readable modules; simplify every changed function until it passes the shared complexity limit of 10.

---

### Task 1: Safe paths, fingerprints, library schema, and scanner

**Files:**
- Create: `backend/essentia_studio/domain/tracks.py`
- Create: `backend/essentia_studio/services/path_safety.py`
- Create: `backend/essentia_studio/services/scanner.py`
- Create: `backend/essentia_studio/db/migrations/0002_library_jobs.sql`
- Create: `backend/essentia_studio/repositories/tracks.py`
- Create: `tests/services/test_path_safety.py`
- Create: `tests/services/test_scanner.py`
- Create: `tests/repositories/test_tracks.py`

**Interfaces:**
- Consumes: `RuntimeConfig.music_root`, SQLAlchemy `Engine`.
- Produces: `TrackFingerprint`, `ScannedTrack`, `resolve_track_path(root: Path, relative: str) -> Path`, `scan_music_root(root: Path) -> Iterator[ScannedTrack]`, and `TrackRepository.replace_scan(tracks, seen_at) -> ScanSummary`.

- [ ] **Step 1: Write traversal and scan tests**

```python
# tests/services/test_path_safety.py
import pytest

from essentia_studio.errors import AppError
from essentia_studio.services.path_safety import resolve_track_path


def test_resolve_track_path_rejects_parent_escape(tmp_path) -> None:
    root = tmp_path / "music"
    root.mkdir()
    with pytest.raises(AppError, match="Musikverzeichnis"):
        resolve_track_path(root, "../outside.flac")


def test_resolve_track_path_accepts_nested_relative_path(tmp_path) -> None:
    root = tmp_path / "music"
    track = root / "Artist" / "Album" / "song.flac"
    track.parent.mkdir(parents=True)
    track.touch()
    assert resolve_track_path(root, "Artist/Album/song.flac") == track.resolve()
```

```python
# tests/services/test_scanner.py
from essentia_studio.services.scanner import scan_music_root


def test_scan_returns_only_supported_files_sorted_by_relative_path(tmp_path) -> None:
    (tmp_path / "B").mkdir()
    (tmp_path / "B" / "two.MP3").write_bytes(b"2")
    (tmp_path / "one.flac").write_bytes(b"1")
    (tmp_path / "cover.jpg").write_bytes(b"x")

    tracks = list(scan_music_root(tmp_path))

    assert [track.relative_path for track in tracks] == ["B/two.MP3", "one.flac"]
    assert [track.fingerprint.size for track in tracks] == [1, 1]
```

- [ ] **Step 2: Run tests and verify missing modules fail**

Run: `python -m pytest tests/services/test_path_safety.py tests/services/test_scanner.py -q`

Expected: FAIL during import.

- [ ] **Step 3: Implement domain types and canonical containment**

```python
# backend/essentia_studio/domain/tracks.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackFingerprint:
    size: int
    mtime_ns: int


@dataclass(frozen=True, slots=True)
class ScannedTrack:
    relative_path: str
    extension: str
    fingerprint: TrackFingerprint
```

```python
# backend/essentia_studio/services/path_safety.py
from pathlib import Path, PurePosixPath

from essentia_studio.errors import AppError


def resolve_track_path(root: Path, relative: str) -> Path:
    logical = PurePosixPath(relative)
    if logical.is_absolute() or ".." in logical.parts or not logical.parts:
        raise AppError("invalid_track_path", "Der Pfad liegt außerhalb des Musikverzeichnisses.", 400)
    resolved_root = root.resolve(strict=True)
    candidate = resolved_root.joinpath(*logical.parts).resolve(strict=True)
    if not candidate.is_relative_to(resolved_root):
        raise AppError("invalid_track_path", "Der Pfad liegt außerhalb des Musikverzeichnisses.", 400)
    return candidate
```

- [ ] **Step 4: Implement deterministic read-only scanning and persistence**

`scan_music_root` must call `root.resolve(strict=True)`, walk with `Path.rglob("*")`, exclude symlinks, filter the exact extension set case-insensitively, call `stat()` once, convert relative paths with `.relative_to(root).as_posix()`, and yield sorted `ScannedTrack` values.

Migration `0002_library_jobs.sql` creates `library_tracks` with unique `relative_path`, size, mtime, last_seen, present flag, and timestamps. `TrackRepository.replace_scan` performs one upsert per scanned track in a single transaction and then marks rows whose `last_seen != seen_at` as `present=0`. It returns scanned/present/missing counts.

- [ ] **Step 5: Verify scanner and commit**

Run: `python -m pytest tests/services/test_path_safety.py tests/services/test_scanner.py tests/repositories/test_tracks.py -q`

Expected: traversal, extension filtering, deterministic ordering, upsert, and missing-file tests PASS.

Commit:

```bash
git add backend/essentia_studio/domain backend/essentia_studio/services backend/essentia_studio/db/migrations/0002_library_jobs.sql backend/essentia_studio/repositories/tracks.py tests/services tests/repositories/test_tracks.py
git commit -m "feat: scan mounted music library safely"
```

### Task 2: Persisted job state, coordinator, cancellation, resume, and SSE

**Files:**
- Create: `backend/essentia_studio/domain/jobs.py`
- Create: `backend/essentia_studio/repositories/jobs.py`
- Create: `backend/essentia_studio/services/jobs.py`
- Create: `backend/essentia_studio/schemas/jobs.py`
- Create: `backend/essentia_studio/api/routes/jobs.py`
- Create: `backend/essentia_studio/schemas/library.py`
- Create: `backend/essentia_studio/api/routes/library.py`
- Create: `tests/services/test_jobs.py`
- Create: `tests/api/test_jobs.py`
- Create: `tests/api/test_library.py`

**Interfaces:**
- Consumes: scan service and engine.
- Produces: `JobType`, `JobStatus`, `JobEvent`, `JobCoordinator.submit()`, `cancel()`, `resume()`, `/api/jobs*` including `EventSourceResponse`, `POST /api/library/scan`, and `GET /api/library/tracks`.

- [ ] **Step 1: Write state-machine and cancellation tests**

```python
# tests/services/test_jobs.py
from threading import Event

from essentia_studio.domain.jobs import JobStatus, JobType
from essentia_studio.services.jobs import JobCoordinator


def test_cancelled_job_keeps_completed_items(job_repository) -> None:
    first_started = Event()

    def handler(item: str, cancelled) -> dict:
        first_started.set()
        if item == "a.flac":
            return {"path": item}
        cancelled.set()
        return {"path": item}

    coordinator = JobCoordinator(job_repository, {JobType.ANALYSIS: handler})
    job = coordinator.submit(JobType.ANALYSIS, ["a.flac", "b.flac", "c.flac"], {})
    coordinator.run_next_for_test()

    saved = job_repository.get(job.id)
    assert saved.status == JobStatus.CANCELLED
    assert saved.completed_items == 2
    assert saved.total_items == 3
```

- [ ] **Step 2: Run and verify missing job domain**

Run: `python -m pytest tests/services/test_jobs.py -q`

Expected: FAIL importing `JobStatus`.

- [ ] **Step 3: Implement explicit job enums and transition validation**

```python
# backend/essentia_studio/domain/jobs.py
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class JobType(StrEnum):
    SCAN = "scan"
    ANALYSIS = "analysis"
    WRITE = "write"
    UNDO = "undo"
    PLAYLIST_WRITE = "playlist_write"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATUSES = {
    JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS,
    JobStatus.CANCELLED, JobStatus.FAILED,
}


@dataclass(frozen=True, slots=True)
class JobEvent:
    sequence: int
    job_id: str
    kind: str
    payload: dict[str, Any]
```

Migration `0002_library_jobs.sql` also creates `jobs`, `job_items`, and `events`. Store UUID strings, JSON configuration snapshots, ordered item positions, per-item status/result/error, and monotonically increasing event sequence IDs.

- [ ] **Step 4: Implement one persisted mutating queue and SSE replay**

`JobCoordinator` accepts `dict[JobType, Callable[[str, threading.Event], dict]]`. `submit` writes the job and all items before enqueuing its ID. The worker processes items in position order, catches exceptions per item, persists a `progress` event after every item, and computes the terminal state from completed/error/cancel flags. `cancel` persists `cancel_requested=1`; the handler receives a shared `Event`. `resume` creates a new linked job containing only queued/failed items and copies the original configuration snapshot.

`JobRepository.append_event` retains at most 10,000 events per job by deleting the oldest rows beyond that limit in the same transaction. Job summary/progress counters remain authoritative even after old event details are pruned.

The SSE route uses FastAPI 0.128's native response:

```python
@router.get("/{job_id}/events", response_class=EventSourceResponse)
async def stream_job_events(job_id: str, after: int = 0) -> AsyncIterable[JobEventResponse]:
    sequence = after
    while True:
        events = repository.events_after(job_id, sequence)
        for event in events:
            sequence = event.sequence
            yield JobEventResponse.model_validate(event)
        if repository.get(job_id).status in TERMINAL_STATUSES and not events:
            return
        await asyncio.sleep(0.25)
```

`POST /api/library/scan` submits one `JobType.SCAN` item whose handler calls `scan_music_root` and `TrackRepository.replace_scan`; it returns HTTP 202 with the persisted job. `GET /api/library/tracks` accepts `search`, `present`, `extension`, `page`, and `page_size` (maximum 200) and returns stable relative-path ordering. Add both routes to the root API router and prove with `tests/api/test_library.py` that scanning does not invoke the analysis backend.

- [ ] **Step 5: Verify queue/API behavior and commit**

Run: `python -m pytest tests/services/test_jobs.py tests/api/test_jobs.py tests/api/test_library.py -q`

Expected: ordered processing, per-item isolation, cancellation, resume, event replay, and terminal SSE tests PASS.

Commit:

```bash
git add backend/essentia_studio/domain/jobs.py backend/essentia_studio/repositories/jobs.py backend/essentia_studio/services/jobs.py backend/essentia_studio/schemas/jobs.py backend/essentia_studio/schemas/library.py backend/essentia_studio/api/routes/jobs.py backend/essentia_studio/api/routes/library.py backend/essentia_studio/db/migrations/0002_library_jobs.sql tests/services/test_jobs.py tests/api/test_jobs.py tests/api/test_library.py
git commit -m "feat: add persisted job coordinator"
```

### Task 3: Pure analysis domain and process-backed Essentia adapter

**Files:**
- Create: `backend/essentia_studio/domain/analysis.py`
- Create: `backend/essentia_studio/services/labels.py`
- Create: `backend/essentia_studio/analysis/protocol.py`
- Create: `backend/essentia_studio/analysis/essentia_backend.py`
- Create: `backend/essentia_studio/analysis/worker.py`
- Create: `backend/essentia_studio/analysis/models.json`
- Create: `backend/essentia_studio/services/analysis_jobs.py`
- Modify: `backend/essentia_studio/services/capabilities.py`
- Create: `backend/essentia_studio/schemas/analysis.py`
- Create: `backend/essentia_studio/api/routes/analysis.py`
- Create: `backend/essentia_studio/db/migrations/0003_analysis.sql`
- Create: `backend/essentia_studio/repositories/results.py`
- Create: `tests/services/test_labels.py`
- Create: `tests/services/test_analysis_jobs.py`
- Create: `tests/api/test_analysis.py`
- Create: `tests/integration/test_model_smoke.py`

**Interfaces:**
- Consumes: safe resolved track, immutable analysis setting snapshot, JobCoordinator.
- Produces: `AnalysisBackend.analyze(path, options) -> AnalysisResult`; `run_analysis_item(relative_path, cancelled) -> dict`; persisted `analysis_results` and `tag_drafts`; `POST /api/analysis/jobs`.

- [ ] **Step 1: Write failing label and no-write analysis tests**

```python
# tests/services/test_labels.py
from essentia_studio.services.labels import format_genre, format_mood, normalize_tags


def test_discogs_parent_child_format_and_deduplication() -> None:
    assert format_genre("Electronic---House") == "Electronic; House"
    assert normalize_tags([" House ", "house", "Deep House"]) == ["House", "Deep House"]


def test_mood_label_becomes_title_case() -> None:
    assert format_mood("moodtheme---happy") == "Happy"
```

```python
# tests/services/test_analysis_jobs.py
def test_analysis_persists_draft_without_calling_tag_service(fake_backend, result_repository) -> None:
    service = AnalysisJobService(fake_backend, result_repository, music_root)
    service.process("Artist/song.flac", AnalysisOptions())
    result = result_repository.get_by_path("Artist/song.flac")
    assert result.draft.genres == ["Electronic; House"]
    assert result.draft.moods == ["Happy"]
```

- [ ] **Step 2: Run tests and confirm missing analysis modules**

Run: `python -m pytest tests/services/test_labels.py tests/services/test_analysis_jobs.py tests/api/test_analysis.py -q`

Expected: FAIL during import.

- [ ] **Step 3: Extract pure formatting and define backend protocol**

```python
# backend/essentia_studio/analysis/protocol.py
from pathlib import Path
from typing import Protocol

from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


class AnalysisBackend(Protocol):
    def model_inventory(self) -> list[dict[str, str]]: ...
    def available_compute(self) -> list[str]: ...
    def analyze(self, path: Path, options: AnalysisOptions) -> AnalysisResult: ...
```

`format_genre` and `format_mood` must port the exact behavior from the top-level `tag_music.py`. `normalize_tags` performs NFKC normalization, trims whitespace, rejects empty/over-120-character entries, deduplicates with `casefold()`, and raises `AppError("too_many_tags", ..., 422)` after 64 values.

- [ ] **Step 4: Implement model manifest and Essentia inference without tag imports**

`models.json` records exact file names, download URLs, SHA-256 checksums, model roles, and output tensor names for:

- `discogs-effnet-bs64-1.pb`
- `genre_discogs400-discogs-effnet-1.pb` plus metadata JSON
- `mtg_jamendo_moodtheme-discogs-effnet-1.pb` plus metadata JSON

`EssentiaBackend` lazily imports `essentia.standard` inside its constructor so foundation tests run without the wheel. Port only `EssentiaAnalyzer.__init__` and `analyze_file` behavior from `tag_music.py`: mono 16 kHz load, optional maximum-duration truncation, EffNet embeddings, frame means, top genre threshold/count with top-one fallback, and top five moods above threshold. It returns raw score objects and formatted arrays; it must not import `TagWriter` or Mutagen.

The process worker has one module-level backend initialized by:

```python
def initialize_worker(model_dir: str, compute: str) -> None:
    global _backend
    os.environ["CUDA_VISIBLE_DEVICES"] = "" if compute == "cpu" else os.environ.get("CUDA_VISIBLE_DEVICES", "0")
    _backend = EssentiaBackend(Path(model_dir))
```

and rejects calls before initialization. `AnalysisJobService` uses a bounded `ProcessPoolExecutor(max_workers=settings.worker_count, initializer=initialize_worker, initargs=...)` and persists each returned result/draft immediately.

`POST /api/analysis/jobs` accepts either explicit track IDs or a validated library query, plus `enable_genres`, `enable_moods`, and optional setting overrides. It resolves the selection to a fixed ordered item list, snapshots the effective settings into the job configuration JSON, and returns HTTP 202. Reject an empty selection and reject requests with both analysis heads disabled.

`tests/api/test_analysis.py` asserts the 202 contract, fixed item ordering, settings snapshot, empty-selection 422, and both-heads-disabled 422 without loading real models.

Replace the foundation capability service's empty model inventory with the injected backend's `model_inventory()` and `available_compute()`. The response reports every model filename, role, checksum, and load status plus the selected TensorFlow device; capability inspection itself must not start an analysis job.

- [ ] **Step 5: Verify pure tests and real CPU model smoke test**

Run:

```bash
python -m pytest tests/services/test_labels.py tests/services/test_analysis_jobs.py tests/api/test_analysis.py -q
python -m pytest tests/integration/test_model_smoke.py -q -m model
```

Expected: pure tests PASS. The model test loads a generated one-second 440 Hz WAV, returns at least one genre and one mood score, and is skipped only when `ESSENTIA_MODEL_DIR` is absent outside the image test environment.

Commit:

```bash
git add backend/essentia_studio/analysis backend/essentia_studio/domain/analysis.py backend/essentia_studio/services/labels.py backend/essentia_studio/services/analysis_jobs.py backend/essentia_studio/schemas/analysis.py backend/essentia_studio/api/routes/analysis.py backend/essentia_studio/db/migrations/0003_analysis.sql backend/essentia_studio/repositories/results.py tests/services tests/integration/test_model_smoke.py
git commit -m "feat: add Essentia analysis jobs"
```

### Task 4: Result query, draft editing, bulk selection, and Workbench frontend

**Files:**
- Create: `backend/essentia_studio/schemas/results.py`
- Create: `backend/essentia_studio/api/routes/results.py`
- Create: `frontend/src/features/workbench/types.ts`
- Create: `frontend/src/features/workbench/useResults.ts`
- Create: `frontend/src/features/workbench/WorkbenchView.tsx`
- Create: `frontend/src/features/workbench/ResultTable.tsx`
- Create: `frontend/src/features/workbench/TagEditor.tsx`
- Create: `frontend/src/features/workbench/SelectionToolbar.tsx`
- Create: `frontend/src/features/workbench/WorkbenchView.test.tsx`
- Create: `tests/api/test_results.py`

**Interfaces:**
- Consumes: result/draft repository and job APIs.
- Produces: `GET /api/results`, `PATCH /api/results/{id}/draft`, `POST /api/results/selection`, `POST /api/results/bulk-draft`; frontend `SelectionSpec = {mode:'ids', ids:string[]} | {mode:'query', query:ResultQuery, excludedIds:string[]}`.

- [ ] **Step 1: Write API and select-all semantics tests**

```python
# tests/api/test_results.py
def test_query_selection_selects_all_matching_rows_not_only_page(client, seeded_results) -> None:
    response = client.post("/api/results/selection", json={
        "selection": {"mode": "query", "query": {"mood": "Happy"}, "excluded_ids": []},
        "selected": True,
    })
    assert response.status_code == 200
    assert response.json() == {"affected": 63}


def test_patch_draft_normalizes_manual_tags(client, seeded_results) -> None:
    response = client.patch(f"/api/results/{seeded_results[0]}/draft", json={
        "genres": [" House ", "house", "Ambient"], "moods": ["Calm"]
    })
    assert response.json()["genres"] == ["House", "Ambient"]


def test_bulk_add_genre_changes_only_selected_drafts(client, seeded_results) -> None:
    response = client.post("/api/results/bulk-draft", json={
        "selection": {"mode": "ids", "ids": seeded_results[:2]},
        "operation": "add_genre",
        "value": "Ambient",
    })
    assert response.json() == {"affected": 2}
```

```tsx
// frontend/src/features/workbench/WorkbenchView.test.tsx
test('select all targets the filtered result set and manual genres remain editable', async () => {
  render(<WorkbenchView />)
  await userEvent.type(await screen.findByLabelText('Ergebnisse filtern'), 'happy')
  await userEvent.click(screen.getByRole('checkbox', { name: 'Alle gefilterten Titel auswählen' }))
  expect(screen.getByText('63 Titel ausgewählt')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Genre zu ausgewählten Titeln hinzufügen' }))
  await userEvent.type(screen.getByLabelText('Genre'), 'Ambient{enter}')
  expect(await screen.findByText('Ambient')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run focused tests and verify route/view absence**

Run:

```bash
python -m pytest tests/api/test_results.py -q
npm --prefix frontend test -- --run src/features/workbench/WorkbenchView.test.tsx
```

Expected: backend 404/collection failure and frontend import failure.

- [ ] **Step 3: Implement paginated queries and transactional draft mutations**

`GET /api/results` accepts `job_id`, `search`, `genre`, `mood`, `status`, `selected`, `page`, and `page_size` (maximum 200), and returns `{items,total,page,page_size,selected_count}`. Sort by relative path then ID for stable pagination.

The draft PATCH replaces only provided genre/mood arrays after `normalize_tags`. Selection updates compile either exact IDs or the same validated result filters into one SQL `UPDATE`; excluded IDs are applied with `NOT IN`. `bulk-draft` supports exactly `add_genre`, `remove_genre`, `add_mood`, and `remove_mood`, normalizes the value once, loads only selected drafts, applies case-insensitive set semantics, and commits all affected drafts in one transaction. Never accept raw SQL or client-provided absolute paths.

- [ ] **Step 4: Implement Workbench selection state and tag chips**

`useResults` owns the query, page, rows, total, and `SelectionSpec`. When select-all is checked it stores query mode and preserves explicit exclusions as rows are unchecked. `SelectionToolbar` shows the server-returned selected count. `TagEditor` uses a form submit, supports Backspace removal, exposes remove buttons as `Genre <value> entfernen` / `Mood <value> entfernen`, and saves through PATCH. Use `useDeferredValue` for the text filter and abort stale fetch requests in effect cleanup.

The Workbench header includes scan/analyze actions, the active job progress bar, and disabled states with German explanations. The result table columns are selection, track, genres, moods, confidence summary, draft/write state, and row actions.

- [ ] **Step 5: Verify API/UI and commit**

Run:

```bash
python -m pytest tests/api/test_results.py -q
npm --prefix frontend test -- --run src/features/workbench
npm --prefix frontend run typecheck
```

Expected: query, selection, edit, keyboard, and type tests PASS.

Commit:

```bash
git add backend/essentia_studio/api/routes/results.py backend/essentia_studio/schemas/results.py frontend/src/features/workbench tests/api/test_results.py
git commit -m "feat: add analysis review workbench"
```

### Task 5: Format-specific managed tag snapshots, verified writes, conflicts, and undo

**Files:**
- Create: `backend/essentia_studio/tags/protocol.py`
- Create: `backend/essentia_studio/tags/mutagen_adapter.py`
- Create: `backend/essentia_studio/tags/registry.py`
- Create: `backend/essentia_studio/services/tag_operations.py`
- Create: `backend/essentia_studio/db/migrations/0004_writes.sql`
- Create: `backend/essentia_studio/repositories/writes.py`
- Create: `backend/essentia_studio/schemas/writes.py`
- Create: `backend/essentia_studio/api/routes/writes.py`
- Create: `tests/tags/test_mutagen_adapter.py`
- Create: `tests/services/test_tag_operations.py`
- Create: `tests/api/test_writes.py`
- Create: `tests/fixtures/generate_audio.py`

**Interfaces:**
- Consumes: selected drafts, safe track resolution, analyzed fingerprints.
- Produces: `ManagedTagSnapshot`, `TagAdapter.read/write/restore`, `TagOperationService.write_selected(selection)`, `undo(operation_id)`, `/api/writes`, `/api/writes/{id}/undo`.

- [ ] **Step 1: Write conflict and exact-restore tests**

```python
# tests/services/test_tag_operations.py
def test_write_skips_track_changed_after_analysis(service, analyzed_track) -> None:
    analyzed_track.path.write_bytes(analyzed_track.path.read_bytes() + b"changed")
    result = service.write_one(analyzed_track.result_id)
    assert result.status == "conflict"
    assert result.error_code == "track_changed_since_analysis"
    assert service.adapter.write_calls == []


def test_undo_restores_exact_managed_snapshot(service, written_track) -> None:
    operation = service.write_one(written_track.result_id)
    restored = service.undo(operation.id)
    assert restored.status == "verified"
    assert service.adapter.read(written_track.path) == written_track.original_snapshot
```

- [ ] **Step 2: Run tests and verify missing tag protocol**

Run: `python -m pytest tests/services/test_tag_operations.py -q`

Expected: FAIL importing `ManagedTagSnapshot`.

- [ ] **Step 3: Define managed snapshots and adapter registry**

```python
# backend/essentia_studio/tags/protocol.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ManagedTagSnapshot:
    format: str
    fields: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DesiredTags:
    genres: list[str]
    moods: list[str]
    genre_confidence: str | None
    mood_confidence: str | None


class TagAdapter(Protocol):
    def read(self, path: Path) -> ManagedTagSnapshot: ...
    def write(self, path: Path, desired: DesiredTags, overwrite: bool) -> None: ...
    def restore(self, path: Path, snapshot: ManagedTagSnapshot) -> None: ...
```

The Mutagen adapter uses this explicit mapping:

| Family | Genre | Mood | Confidence |
|---|---|---|---|
| FLAC/OGG/Opus | `GENRE` | `MOOD` | `ESSENTIA_GENRE`, `ESSENTIA_MOOD` |
| MP3/AIFF/WAV/DSF ID3 | `TCON` | `COMM:Essentia Mood:eng` | `COMM:Essentia Genre:eng`, `COMM:Essentia Mood Confidence:eng` |
| MP4/M4A/AAC | `©gen` | `----:com.apple.iTunes:MOOD` | `----:com.apple.iTunes:ESSENTIA_GENRE`, `----:com.apple.iTunes:ESSENTIA_MOOD` |
| WMA/ASF | `WM/Genre` | `WM/Mood` | `Essentia/Genre`, `Essentia/Mood` |
| APEv2 | `Genre` | `Mood` | `Essentia Genre`, `Essentia Mood` |

Snapshots store presence separately from values so restoration can delete fields that were originally absent. ID3 restoration deletes frames by exact frame ID and description before adding captured frames, preventing duplicate mood comments.

- [ ] **Step 4: Implement write transaction boundaries and read-back verification**

`TagOperationService.write_one` performs this exact sequence:

1. resolve path beneath music root;
2. compare current fingerprint to analysis fingerprint;
3. read `original_snapshot`;
4. create a `write_operations` row with status `started`;
5. call adapter `write`;
6. read tags and compare normalized requested genre/mood values;
7. capture post-write fingerprint and mark `verified`, or mark `failed` with code/message.

It does not hold a SQLite transaction across steps 5–6. Undo requires `status=verified` and current fingerprint equal to `post_write_fingerprint`, then restores the captured snapshot and verifies exact managed-field equality.

`generate_audio.py` invokes `ffmpeg` as an argument list to create one-second sine fixtures for MP3, FLAC, OGG, Opus, M4A, WMA, AIFF, WAV, and WavPack. DSF/APE/Musepack serialization paths are tested with isolated Mutagen object doubles when the local ffmpeg lacks an encoder.

- [ ] **Step 5: Verify every format family and API then commit**

Run:

```bash
python tests/fixtures/generate_audio.py
python -m pytest tests/tags tests/services/test_tag_operations.py tests/api/test_writes.py -q
```

Expected: every mapping family has write/read/restore coverage; conflict does not call write; failed files do not stop batch; verified undo restores absence as well as values.

Commit:

```bash
git add backend/essentia_studio/tags backend/essentia_studio/services/tag_operations.py backend/essentia_studio/db/migrations/0004_writes.sql backend/essentia_studio/repositories/writes.py backend/essentia_studio/schemas/writes.py backend/essentia_studio/api/routes/writes.py tests/tags tests/services/test_tag_operations.py tests/api/test_writes.py tests/fixtures/generate_audio.py
git commit -m "feat: add verified tag writes and undo"
```

### Task 6: Write preview, job history, undo UI, and end-to-end workflow

**Files:**
- Create: `frontend/src/features/workbench/WritePreviewDialog.tsx`
- Create: `frontend/src/features/jobs/JobsView.tsx`
- Create: `frontend/src/features/jobs/useJobEvents.ts`
- Create: `frontend/src/features/jobs/JobsView.test.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Modify: `frontend/src/app/App.tsx`
- Create: `frontend/e2e/analysis-workbench.spec.ts`
- Create: `frontend/playwright.config.ts`

**Interfaces:**
- Consumes: selection count, write/undo APIs, job list/detail, SSE events.
- Produces: confirmation preview, reconnecting live jobs, history/undo actions, full browser regression.

- [ ] **Step 1: Write failing write-preview and SSE cleanup tests**

```tsx
// frontend/src/features/jobs/JobsView.test.tsx
test('closes the event stream on unmount and exposes verified undo', async () => {
  const close = vi.fn()
  vi.stubGlobal('EventSource', vi.fn(() => ({ close, addEventListener: vi.fn() })))
  const { unmount } = render(<JobsView />)
  expect(await screen.findByRole('button', { name: 'Tags wiederherstellen' })).toBeEnabled()
  unmount()
  expect(close).toHaveBeenCalledOnce()
})
```

```typescript
// frontend/e2e/analysis-workbench.spec.ts
test('scan, analyze, edit, selectively write, and undo', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Bibliothek scannen' }).click()
  await expect(page.getByText('Scan abgeschlossen')).toBeVisible()
  await page.getByRole('button', { name: 'Auswahl analysieren' }).click()
  await expect(page.getByText('Analyse abgeschlossen')).toBeVisible()
  await page.getByRole('button', { name: 'Genre hinzufügen' }).first().click()
  await page.getByLabel('Genre').fill('Ambient')
  await page.getByLabel('Genre').press('Enter')
  await page.getByRole('checkbox', { name: /song-one/ }).check()
  await page.getByRole('button', { name: '1 Titel schreiben' }).click()
  await page.getByRole('button', { name: 'Schreiben bestätigen' }).click()
  await expect(page.getByText('1 verifiziert')).toBeVisible()
  await page.getByRole('button', { name: 'Tags wiederherstellen' }).click()
  await expect(page.getByText('Wiederherstellung verifiziert')).toBeVisible()
})
```

- [ ] **Step 2: Run tests and verify missing components**

Run: `npm --prefix frontend test -- --run src/features/jobs`

Expected: FAIL importing `JobsView`.

- [ ] **Step 3: Implement preview and reconnecting EventSource hook**

`WritePreviewDialog` loads the selected count plus the first 20 before/after rows, lists conflicts separately, and requires an explicit “Schreiben bestätigen” button. It never treats opening the dialog as consent.

`useJobEvents(jobId)` creates `new EventSource('/api/jobs/'+jobId+'/events?after='+lastSequence)`, parses typed events, ignores sequence IDs already applied, closes on cleanup, and retries through the browser EventSource reconnect behavior. On terminal events it closes immediately and refetches authoritative job state.

- [ ] **Step 4: Implement Jobs/history and undo interaction**

JobsView groups running, completed-with-errors, and completed jobs. Per-file error details are expandable. A verified write shows Undo only when the API reports `undo_available=true`; stale writes display the conflict reason. After an undo request, the view follows the returned undo job through SSE.

Configure `frontend/playwright.config.ts` with two `webServer` entries: from the repository root launch `python scripts/dev.py backend`, and from `frontend` launch `npm run dev`. Use `reuseExistingServer: !process.env.CI`, Chromium as the only first-release project, and base URL `http://127.0.0.1:5173`. The E2E fixture starts with a temporary music root, temporary database, generated audio, and a deterministic fake analysis backend selected by `ESSENTIA_ANALYSIS_BACKEND=fake`.

- [ ] **Step 5: Run the full analysis gate and commit**

Run:

```bash
python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run e2e -- e2e/analysis-workbench.spec.ts
```

Expected: complete scan-to-undo workflow passes, EventSource is cleaned up, and all prior foundation tests remain green.

Commit:

```bash
git add frontend/src/features frontend/src/app/App.tsx frontend/e2e frontend/playwright.config.ts
git commit -m "feat: complete analysis workbench workflow"
```

## Analysis completion evidence

- A real mounted audio fixture produces genre and mood drafts without changing file bytes or metadata.
- Query-based select-all operates across more rows than one page.
- Manual genres and moods survive reload and are the values written.
- Fingerprint conflicts skip files before mutation.
- Read-back verification and exact managed-tag undo pass for every supported tag family.
- Cancellation preserves completed drafts and resume processes only unfinished items.
- Browser E2E proves scan → analyze → edit → select → preview → write → undo.
