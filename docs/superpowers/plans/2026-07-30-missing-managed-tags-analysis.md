# Missing Managed Tags Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Filter the scanned library by genuinely missing file-level genre and mood tags, and analyze only the missing classification heads for each selected track.

**Architecture:** Persist a read-only managed-tag inventory with every scanned library track and use it as the indexed filter source. Re-read selected files when admitting an analysis job, snapshot per-path head decisions in the job configuration, preserve existing file tags in drafts, and update the inventory only after verified writes or undo operations.

**Tech Stack:** Python 3.10, FastAPI 0.136.3, Pydantic 2, SQLAlchemy 2 with SQLite JSON1, Mutagen, React 19.2.7, TypeScript, Vitest, Playwright.

## Global Constraints

- A filter is based on managed tags actually read from the audio file, never on predictions or draft values.
- With both quick filters enabled, use OR semantics: include a track if genre or mood or both are missing.
- Scan and analysis admission are read-only; neither may write audio tags.
- A managed-tag read error is not equivalent to an empty tag list and must not make a track eligible for analysis.
- The API must reject or skip fully tagged tracks even if a client bypasses the browser controls.
- Per track, enable only a requested classification head whose corresponding file tag list is empty.
- Existing file tags must be copied into the draft and must survive overwrite-mode writes.
- Update stored file-tag inventory only from a successful read, verified write, or verified undo.
- Keep canonical path confinement, fingerprint checks, per-item failure isolation, and German user-facing errors with stable machine codes.
- Keep hand-written Python and TypeScript cyclomatic complexity at or below 10.

---

### Task 1: Persist a read-only managed-tag inventory during library scans

**Files:**
- Create: `backend/essentia_studio/db/migrations/0013_managed_tag_inventory.sql`
- Modify: `backend/essentia_studio/domain/tracks.py`
- Create: `backend/essentia_studio/services/managed_tag_inventory.py`
- Modify: `backend/essentia_studio/services/scanner.py`
- Modify: `backend/essentia_studio/repositories/tracks.py`
- Modify: `backend/essentia_studio/main.py`
- Test: `tests/services/test_scanner.py`
- Test: `tests/repositories/test_tracks.py`
- Test: `tests/db/test_migrations.py`

**Interfaces:**
- Consumes: `TagAdapterRegistry.for_path(path).read(path) -> ManagedTagSnapshot` and the existing canonical scan traversal.
- Produces: `ManagedTagInventory`, `read_managed_tag_inventory(path, registry)`, persisted `managed_genres`, `managed_moods`, `managed_tags_status`, and `managed_tags_error_code` fields on `LibraryTrack`.

- [ ] **Step 1: Write failing scan and repository tests**

Add a recording adapter and prove that successful reads, empty values, and read failures remain distinct:

```python
class InventoryAdapter:
    def __init__(self, snapshots: dict[str, ManagedTagSnapshot | Exception]) -> None:
        self.snapshots = snapshots
        self.write_calls = 0

    def read(self, path: Path) -> ManagedTagSnapshot:
        result = self.snapshots[path.name]
        if isinstance(result, Exception):
            raise result
        return result

    def write(self, *_args) -> None:
        self.write_calls += 1


def test_scan_records_managed_tags_without_writing(tmp_path) -> None:
    path = tmp_path / "tagged.flac"
    path.write_bytes(b"audio")
    adapter = InventoryAdapter({
        "tagged.flac": ManagedTagSnapshot("vorbis", {
            "genres": [" Rock ", "rock"], "moods": ["Calm"]
        })
    })

    [track] = scan_music_root(tmp_path, tag_registry=TagAdapterRegistry(adapter))

    assert track.managed_tags == ManagedTagInventory(["Rock"], ["Calm"], "ok", None)
    assert adapter.write_calls == 0


def test_scan_does_not_treat_tag_read_error_as_empty(tmp_path) -> None:
    path = tmp_path / "broken.flac"
    path.write_bytes(b"audio")
    adapter = InventoryAdapter({"broken.flac": ValueError("invalid")})

    [track] = scan_music_root(tmp_path, tag_registry=TagAdapterRegistry(adapter))

    assert track.managed_tags.status == "error"
    assert track.managed_tags.error_code == "managed_tags_unreadable"
```

Extend `test_replace_scan_persists_and_updates_metadata` to assert that a second scan replaces both managed tag lists and clears a previous read error after a successful read.

- [ ] **Step 2: Run the focused tests and confirm the missing inventory model fails**

Run:

```powershell
python -m pytest tests/services/test_scanner.py tests/repositories/test_tracks.py tests/db/test_migrations.py -q --basetemp=.pytest-tmp/missing-tags-task1
```

Expected: FAIL importing `ManagedTagInventory` or reading absent migration columns.

- [ ] **Step 3: Add the migration and domain model**

Create migration `0013_managed_tag_inventory.sql`:

```sql
ALTER TABLE library_tracks ADD COLUMN managed_genres TEXT NOT NULL DEFAULT '[]';
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN managed_moods TEXT NOT NULL DEFAULT '[]';
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN managed_tags_status TEXT NOT NULL DEFAULT 'unknown'
  CHECK (managed_tags_status IN ('unknown', 'ok', 'error'));
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN managed_tags_error_code TEXT;
-- migrate:split
CREATE INDEX library_tracks_managed_tag_status_idx
ON library_tracks(present, managed_tags_status);
```

Add the focused domain type and attach it to both scanned and stored tracks:

```python
ManagedTagReadStatus = Literal["unknown", "ok", "error"]


@dataclass(frozen=True, slots=True)
class ManagedTagInventory:
    genres: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    status: ManagedTagReadStatus = "unknown"
    error_code: str | None = None
```

Add `managed_tags: ManagedTagInventory = ManagedTagInventory()` to `ScannedTrack` and `LibraryTrack`.

- [ ] **Step 4: Implement normalized read-only inventory collection**

In `services/managed_tag_inventory.py`, implement NFKC normalization, whitespace trimming, and case-insensitive deduplication without the draft's 64-value limit:

```python
def normalize_inventory_values(values: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    identities: set[str] = set()
    for value in values:
        cleaned = unicodedata.normalize("NFKC", str(value)).strip()
        if cleaned and cleaned.casefold() not in identities:
            normalized.append(cleaned)
            identities.add(cleaned.casefold())
    return normalized


def inventory_from_snapshot(snapshot: ManagedTagSnapshot) -> ManagedTagInventory:
    return ManagedTagInventory(
        genres=normalize_inventory_values(snapshot.fields.get("genres", [])),
        moods=normalize_inventory_values(snapshot.fields.get("moods", [])),
        status="ok",
    )


def read_managed_tag_inventory(path: Path, registry: TagAdapterRegistry) -> ManagedTagInventory:
    try:
        return inventory_from_snapshot(registry.for_path(path).read(path))
    except Exception:
        return ManagedTagInventory(status="error", error_code="managed_tags_unreadable")
```

Pass an injected `TagAdapterRegistry` into `scan_music_root`, populate `ScannedTrack.managed_tags`, and wire the application registry through `refresh_library()`. Do not log an absolute host path or call `write`, `restore`, or `audio.save()`.

- [ ] **Step 5: Persist and hydrate the inventory**

Extend `UPSERT_TRACK`, `_parameters`, all library-track selects, and `_track_from_row` to JSON-serialize and hydrate the two lists and status fields. Add:

```python
def update_managed_tags(self, track_id: int, inventory: ManagedTagInventory) -> None:
    if inventory.status != "ok":
        raise ValueError("Only successfully read managed tags may replace file state")
    with self._engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE library_tracks
                SET managed_genres = :genres, managed_moods = :moods,
                    managed_tags_status = 'ok', managed_tags_error_code = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :track_id
            """),
            {"track_id": track_id, "genres": json.dumps(inventory.genres),
             "moods": json.dumps(inventory.moods)},
        )
```

- [ ] **Step 6: Run focused verification and commit**

Run:

```powershell
python -m pytest tests/services/test_scanner.py tests/repositories/test_tracks.py tests/db/test_migrations.py -q --basetemp=.pytest-tmp/missing-tags-task1
python -m ruff check backend tests scripts
```

Expected: PASS; scan tests prove zero writes and repository tests prove round-trip persistence.

Commit:

```powershell
git add backend/essentia_studio/db/migrations/0013_managed_tag_inventory.sql backend/essentia_studio/domain/tracks.py backend/essentia_studio/services/managed_tag_inventory.py backend/essentia_studio/services/scanner.py backend/essentia_studio/repositories/tracks.py backend/essentia_studio/main.py tests/services/test_scanner.py tests/repositories/test_tracks.py tests/db/test_migrations.py
git commit -m "feat: inventory managed file tags during scan"
```

### Task 2: Add server-side missing-tag filters and complete filtered selection

**Files:**
- Modify: `backend/essentia_studio/domain/tracks.py`
- Modify: `backend/essentia_studio/repositories/tracks.py`
- Modify: `backend/essentia_studio/schemas/library.py`
- Modify: `backend/essentia_studio/schemas/analysis.py`
- Modify: `backend/essentia_studio/api/routes/library.py`
- Modify: `backend/essentia_studio/api/routes/analysis.py`
- Test: `tests/repositories/test_tracks.py`
- Test: `tests/api/test_library.py`

**Interfaces:**
- Consumes: persisted `LibraryTrack.managed_tags` from Task 1.
- Produces: domain `LibraryQuery`, `LibrarySelectionQuery.to_domain()`, `TrackRepository.query(filters: LibraryQuery, page, page_size)`, and API query parameters `missing_genre` and `missing_mood` with OR semantics.

- [ ] **Step 1: Write failing repository and API filter tests**

Seed four tracks: complete, genre-only, mood-only, and empty. Assert:

```python
def test_missing_tag_filters_use_file_inventory_and_or_semantics(repository) -> None:
    assert paths(repository.query(LibraryQuery(missing_genre=True), 1, 50)) == [
        "empty.flac", "mood-only.flac"
    ]
    assert paths(repository.query(LibraryQuery(missing_mood=True), 1, 50)) == [
        "empty.flac", "genre-only.flac"
    ]
    assert paths(repository.query(
        LibraryQuery(missing_genre=True, missing_mood=True), 1, 50
    )) == ["empty.flac", "genre-only.flac", "mood-only.flac"]
```

Also seed a `managed_tags_status="error"` track and assert that it appears in none of the missing-tag results. At the API layer, assert returned `managed_genres`, `managed_moods`, and `managed_tags_status` fields and the same totals.

- [ ] **Step 2: Run tests and verify the unsupported query parameters fail**

Run:

```powershell
python -m pytest tests/repositories/test_tracks.py tests/api/test_library.py -q --basetemp=.pytest-tmp/missing-tags-task2
```

Expected: FAIL because `LibraryQuery` and missing-tag predicates do not exist.

- [ ] **Step 3: Introduce one domain query and one HTTP selection model**

Add the repository-facing query to `domain/tracks.py` so persistence does not depend on Pydantic:

```python
@dataclass(frozen=True, slots=True)
class LibraryQuery:
    search: str | None = None
    present: bool | None = True
    extension: str | None = None
    missing_genre: bool = False
    missing_mood: bool = False
```

Move the request model into `schemas/library.py`, import it from `schemas/analysis.py`, and map it explicitly:

```python
class LibrarySelectionQuery(BaseModel):
    search: str | None = None
    present: bool | None = True
    extension: str | None = None
    missing_genre: bool = False
    missing_mood: bool = False

    def to_domain(self) -> LibraryQuery:
        return LibraryQuery(**self.model_dump())
```

Extend `TrackResponse` with `managed_genres`, `managed_moods`, `managed_tags_status`, and `managed_tags_error_code`.

- [ ] **Step 4: Implement one reusable repository predicate builder**

Change `TrackRepository.query` to accept `filters: LibraryQuery`, then extract:

```python
@staticmethod
def _where(filters: LibraryQuery) -> tuple[str, dict[str, object]]:
    conditions: list[str] = []
    parameters: dict[str, object] = {}
    if filters.search:
        conditions.append(
            "(LOWER(relative_path) LIKE :search OR LOWER(COALESCE(artist, '')) LIKE :search "
            "OR LOWER(COALESCE(title, '')) LIKE :search "
            "OR LOWER(COALESCE(album, '')) LIKE :search)"
        )
        parameters["search"] = f"%{filters.search.casefold()}%"
    if filters.present is not None:
        conditions.append("present = :present")
        parameters["present"] = int(filters.present)
    if filters.extension:
        conditions.append("extension = :extension")
        parameters["extension"] = filters.extension.casefold()
    missing: list[str] = []
    if filters.missing_genre:
        missing.append("json_array_length(managed_genres) = 0")
    if filters.missing_mood:
        missing.append("json_array_length(managed_moods) = 0")
    if missing:
        conditions.append("managed_tags_status = 'ok'")
        conditions.append(f"({' OR '.join(missing)})")
    return (f"WHERE {' AND '.join(conditions)}" if conditions else ""), parameters
```

Use this builder for count and page queries. Update `/api/library/tracks`, `_selected_tracks`, and all callers to construct the same `LibraryQuery`, ensuring analysis-by-query resolves the exact server-filtered set.

- [ ] **Step 5: Run focused verification and commit**

Run:

```powershell
python -m pytest tests/repositories/test_tracks.py tests/api/test_library.py tests/api/test_analysis.py -q --basetemp=.pytest-tmp/missing-tags-task2
python -m ruff check backend tests scripts
```

Expected: PASS; both-filter results use OR semantics and unreadable inventories are excluded.

Commit:

```powershell
git add backend/essentia_studio/domain/tracks.py backend/essentia_studio/repositories/tracks.py backend/essentia_studio/schemas/library.py backend/essentia_studio/schemas/analysis.py backend/essentia_studio/api/routes/library.py backend/essentia_studio/api/routes/analysis.py tests/repositories/test_tracks.py tests/api/test_library.py tests/api/test_analysis.py
git commit -m "feat: filter library by missing file tags"
```

### Task 3: Admit only incomplete tracks and snapshot per-track analysis heads

**Files:**
- Create: `backend/essentia_studio/services/analysis_admission.py`
- Modify: `backend/essentia_studio/api/dependencies.py`
- Modify: `backend/essentia_studio/api/routes/analysis.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `backend/essentia_studio/services/analysis_jobs.py`
- Modify: `backend/essentia_studio/services/automation.py`
- Test: `tests/services/test_analysis_admission.py`
- Test: `tests/services/test_analysis_jobs.py`
- Test: `tests/services/test_automation.py`
- Test: `tests/api/test_analysis.py`

**Interfaces:**
- Consumes: requested `AnalysisOptions`, selected `LibraryTrack` records, safe path resolution, `TagAdapterRegistry`, and `TrackRepository.update_managed_tags`.
- Produces: `AnalysisWorkItem(relative_path, enable_genres, enable_moods)`, `AnalysisAdmissionService.prepare(tracks, requested)`, immutable `configuration["heads_by_path"]`, and drafts that preserve existing file tags.

- [ ] **Step 1: Write failing admission tests for all four tag states**

```python
def test_admission_enables_only_missing_requested_heads(admission, tracks) -> None:
    admitted = admission.prepare(tracks, AnalysisOptions())

    assert admitted.items == [
        AnalysisWorkItem("empty.flac", True, True),
        AnalysisWorkItem("genre-only.flac", False, True),
        AnalysisWorkItem("mood-only.flac", True, False),
    ]
    assert "complete.flac" in admitted.skipped_complete


def test_admission_excludes_read_failure_instead_of_assuming_empty(admission) -> None:
    admitted = admission.prepare([unreadable_track], AnalysisOptions())
    assert admitted.items == []
    assert admitted.failures[0].code == "managed_tags_unreadable"
```

Assert the adapter is read once per selected file, the repository inventory is refreshed from each successful read, and disabling a requested head never re-enables it automatically.

- [ ] **Step 2: Write failing API and draft-preservation tests**

Extend `tests/api/test_analysis.py` to prove a client-provided complete track ID is not queued and that a fully ineligible request returns:

```python
assert response.status_code == 422
assert response.json()["error"]["code"] == "no_missing_managed_tags"
```

Extend `tests/services/test_analysis_jobs.py`:

```python
def test_mood_only_analysis_preserves_existing_file_genre(service, backend) -> None:
    stored = service.process(
        "genre-only.flac",
        AnalysisOptions(enable_genres=False, enable_moods=True),
    )
    assert backend.options.enable_genres is False
    assert stored.draft.genres == ["Rock"]
    assert stored.draft.moods == ["Happy"]
```

- [ ] **Step 3: Run tests and confirm the admission service is absent**

Run:

```powershell
python -m pytest tests/services/test_analysis_admission.py tests/services/test_analysis_jobs.py tests/services/test_automation.py tests/api/test_analysis.py -q --basetemp=.pytest-tmp/missing-tags-task3
```

Expected: FAIL importing `AnalysisAdmissionService` and because complete tracks are currently submitted.

- [ ] **Step 4: Implement immutable admission results**

Create:

```python
@dataclass(frozen=True, slots=True)
class AnalysisWorkItem:
    relative_path: str
    enable_genres: bool
    enable_moods: bool


@dataclass(frozen=True, slots=True)
class AnalysisAdmission:
    items: list[AnalysisWorkItem]
    skipped_complete: list[str]
    failures: list[AdmissionFailure]
```

`AnalysisAdmissionService.prepare` must resolve each relative path beneath the music root, read the current managed snapshot, normalize it through `inventory_from_snapshot`, update the repository, and derive:

```python
enable_genres = requested.enable_genres and not inventory.genres
enable_moods = requested.enable_moods and not inventory.moods
```

Append a work item only when either derived flag is true. Catch errors per track as `AdmissionFailure("managed_tags_unreadable", relative_path)` without exposing the host path.

- [ ] **Step 5: Snapshot per-path decisions in the job and enforce them in the handler**

Inject the admission service into the analysis route. Preserve relative paths as job item values and store decisions separately:

```python
configuration["heads_by_path"] = {
    item.relative_path: {
        "enable_genres": item.enable_genres,
        "enable_moods": item.enable_moods,
    }
    for item in admission.items
}
```

If `admission.items` is empty, raise `AppError("no_missing_managed_tags", "Die ausgewählten Titel enthalten bereits Genre- und Mood-Tags.", 422)` unless every candidate failed, in which case use `managed_tags_unreadable` and report the failure count.

In `main.py`, reject legacy or malformed queued jobs that have no decision for the current path with `AppError("analysis_job_missing_tag_scope", "Der Analyseauftrag enthält keine sichere Tag-Auswahl.", 409)`. Then replace only the two booleans on the job-level options:

```python
heads = job.configuration["heads_by_path"][relative_path]
options = replace(
    AnalysisOptions(**job.configuration["analysis"]),
    enable_genres=heads["enable_genres"],
    enable_moods=heads["enable_moods"],
)
```

Pass the same admission service into `AutomationService`. After its existing scan and state filtering, call `prepare`, reserve only admitted tracks, and submit the identical `heads_by_path` mapping. Extend `tests/services/test_automation.py` so fully tagged changed tracks are not reserved or submitted and partially tagged tracks carry the correct per-path head flags. This keeps scheduled and watcher-triggered analysis inside the same server-side invariant as manual API requests.

- [ ] **Step 6: Preserve existing file tags in drafts**

In `AnalysisJobService.process`, require `track.managed_tags.status == "ok"`. Build predicted lists only for enabled heads, and use the inventory for disabled heads:

```python
draft_genres = predicted_genres if options.enable_genres else track.managed_tags.genres
draft_moods = predicted_moods if options.enable_moods else track.managed_tags.moods
```

Persist the full draft. Existing backend implementations already honor `AnalysisOptions.enable_genres` and `enable_moods`; add assertions to the fake backend test rather than adding a parallel inference path.

- [ ] **Step 7: Run focused verification and commit**

Run:

```powershell
python -m pytest tests/services/test_analysis_admission.py tests/services/test_analysis_jobs.py tests/services/test_automation.py tests/api/test_analysis.py tests/analysis -q --basetemp=.pytest-tmp/missing-tags-task3
python -m ruff check backend tests scripts
```

Expected: PASS; every admitted job item has at least one enabled head and existing tags appear unchanged in the draft.

Commit:

```powershell
git add backend/essentia_studio/services/analysis_admission.py backend/essentia_studio/api/dependencies.py backend/essentia_studio/api/routes/analysis.py backend/essentia_studio/main.py backend/essentia_studio/services/analysis_jobs.py backend/essentia_studio/services/automation.py tests/services/test_analysis_admission.py tests/services/test_analysis_jobs.py tests/services/test_automation.py tests/api/test_analysis.py
git commit -m "feat: analyze only missing managed tags"
```

### Task 4: Synchronize inventory after verified write and undo

**Files:**
- Modify: `backend/essentia_studio/repositories/writes.py`
- Modify: `backend/essentia_studio/services/tag_operations.py`
- Modify: `backend/essentia_studio/main.py`
- Test: `tests/services/test_tag_operations.py`
- Test: `tests/api/test_writes.py`

**Interfaces:**
- Consumes: the post-operation `ManagedTagSnapshot` already read for verification and `inventory_from_snapshot` from Task 1.
- Produces: transactional `WriteRepository.finish_verified(operation_id, fingerprint, inventory)` and `finish_undone(operation_id, fingerprint, inventory)` updates.

- [ ] **Step 1: Write failing write, undo, and failure-state tests**

Extend the existing service fixture with initial library inventory. Assert:

```python
def test_verified_write_updates_current_file_inventory(client, music_root) -> None:
    service, _adapter, result_id, _path, _original = make_service(client, music_root)
    operation = service.write_one(result_id)
    stored = client.app.state.track_repository.get_by_path(operation.relative_path)
    assert stored.managed_tags.genres == ["Ambient"]
    assert stored.managed_tags.moods == ["Calm"]


def test_verified_undo_restores_current_file_inventory(client, music_root) -> None:
    service, _adapter, result_id, _path, original = make_service(client, music_root)
    operation = service.write_one(result_id)
    service.undo(operation.id)
    stored = client.app.state.track_repository.get_by_path(operation.relative_path)
    assert stored.managed_tags == inventory_from_snapshot(original)
```

Add a verification-failure adapter and assert its stored inventory remains unchanged.

- [ ] **Step 2: Run tests and observe stale inventory**

Run:

```powershell
python -m pytest tests/services/test_tag_operations.py tests/api/test_writes.py -q --basetemp=.pytest-tmp/missing-tags-task4
```

Expected: FAIL because write completion currently updates only the fingerprint.

- [ ] **Step 3: Update write completion transactionally**

Extend `WriteRepository.finish_verified` to accept `ManagedTagInventory`, update `library_tracks.managed_genres`, `managed_moods`, status, error code, size, and mtime in the same database transaction that marks the operation verified and deselects its draft.

Add `finish_undone` with the same inventory/fingerprint update and `status='undone'`. Do not call either method until read-back equality or desired-tag containment has passed.

- [ ] **Step 4: Pass verified snapshots from the service**

Change the success paths only:

```python
return self._writes.finish_verified(
    operation.id,
    self._fingerprint(path),
    inventory_from_snapshot(written),
)
```

and:

```python
return self._writes.finish_undone(
    operation.id,
    self._fingerprint(path),
    inventory_from_snapshot(restored),
)
```

Keep conflict and exception paths on `finish` so they cannot alter the inventory.

- [ ] **Step 5: Run focused verification and commit**

Run:

```powershell
python -m pytest tests/services/test_tag_operations.py tests/api/test_writes.py -q --basetemp=.pytest-tmp/missing-tags-task4
python -m ruff check backend tests scripts
```

Expected: PASS; successful write and undo change inventory, failed verification does not.

Commit:

```powershell
git add backend/essentia_studio/repositories/writes.py backend/essentia_studio/services/tag_operations.py backend/essentia_studio/main.py tests/services/test_tag_operations.py tests/api/test_writes.py
git commit -m "feat: sync managed tag inventory after writes"
```

### Task 5: Add accessible quick filters to the Workbench library

**Files:**
- Modify: `frontend/src/features/workbench/types.ts`
- Modify: `frontend/src/features/workbench/useLibraryTracks.ts`
- Create: `frontend/src/features/workbench/MissingTagFilters.tsx`
- Create: `frontend/src/features/workbench/MissingTagFilters.test.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.test.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: `GET /api/library/tracks?missing_genre=true&missing_mood=true` and the existing explicit track-ID analysis request.
- Produces: `LibraryQuery`, `MissingTagFilters`, server-filtered library loading, selection reset on query changes, and German status copy for skipped complete tracks.

- [ ] **Step 1: Write failing component and Workbench tests**

Test the filter component as two toggle buttons:

```tsx
test('toggles missing genre and mood independently', async () => {
  const onChange = vi.fn()
  render(<MissingTagFilters value={{ missingGenre: false, missingMood: false }} onChange={onChange} />)
  await userEvent.click(screen.getByRole('button', { name: 'Ohne Genre' }))
  expect(onChange).toHaveBeenCalledWith({ missingGenre: true, missingMood: false })
})
```

In `WorkbenchView.test.tsx`, capture library request URLs and assert both toggles produce both query parameters, filtered `Alle auswählen` selects only returned IDs, and the analysis request contains only those IDs. Assert the selection clears whenever either quick filter changes.

- [ ] **Step 2: Run frontend tests and verify the controls are absent**

Run:

```powershell
npm --prefix frontend test -- --run src/features/workbench/MissingTagFilters.test.tsx src/features/workbench/WorkbenchView.test.tsx
```

Expected: FAIL importing `MissingTagFilters` or finding the two buttons.

- [ ] **Step 3: Add typed query loading**

Add:

```typescript
export interface LibraryQuery {
  search: string
  missingGenre: boolean
  missingMood: boolean
}
```

Change `useLibraryTracks(search)` to `useLibraryTracks(query)`, memoize the query in `WorkbenchView`, and map camel-case state to API parameters:

```typescript
if (query.missingGenre) parameters.set('missing_genre', 'true')
if (query.missingMood) parameters.set('missing_mood', 'true')
```

Keep page loading server-side so totals and all-selection represent the full filtered library.

- [ ] **Step 4: Implement accessible quick-filter buttons**

Render the component beside the search field:

```tsx
<button
  aria-pressed={value.missingGenre}
  className="quick-filter"
  onClick={() => onChange({ ...value, missingGenre: !value.missingGenre })}
  type="button"
>
  Ohne Genre
</button>
```

Repeat for Mood. Use the existing genre blue and mood purple tokens for active states, retain visible focus rings, and ensure the controls wrap on tablet widths. Do not hide them inside the existing details menu.

When either filter changes, clear `analysisSelection`. Keep `selectAllForAnalysis` based on the tracks returned by the server.

- [ ] **Step 5: Run component tests, lint, and commit**

Run:

```powershell
npm --prefix frontend test -- --run src/features/workbench/MissingTagFilters.test.tsx src/features/workbench/WorkbenchView.test.tsx
npm --prefix frontend run lint
npm --prefix frontend run typecheck
```

Expected: PASS with no accessibility-role or type failures.

Commit:

```powershell
git add frontend/src/features/workbench/types.ts frontend/src/features/workbench/useLibraryTracks.ts frontend/src/features/workbench/MissingTagFilters.tsx frontend/src/features/workbench/MissingTagFilters.test.tsx frontend/src/features/workbench/WorkbenchView.tsx frontend/src/features/workbench/WorkbenchView.test.tsx frontend/src/styles/global.css
git commit -m "feat: add missing tag quick filters"
```

### Task 6: Verify the complete filtered analysis workflow

**Files:**
- Modify: `scripts/e2e_server.py`
- Modify: `frontend/e2e/analysis-workbench.spec.ts`
- Modify: `docs/superpowers/plans/2026-07-16-essentia-studio-roadmap.md`
- Modify: `docs/superpowers/plans/2026-07-30-missing-managed-tags-analysis.md`

**Interfaces:**
- Consumes: completed scan inventory, server-side filters, adaptive analysis, and verified inventory synchronization from Tasks 1-5.
- Produces: browser evidence for filter-to-analysis behavior and a current roadmap/task checklist.

- [ ] **Step 1: Extend the Playwright scenario with complete and partially tagged fixtures**

Extend `scripts/e2e_server.py` with tagged fixtures after creating each valid WAV:

```python
def write_fixture_tags(path: Path, genres: list[str], moods: list[str]) -> None:
    MutagenTagAdapter().write(path, DesiredTags(genres, moods), overwrite=True)


create_wave_fixture(music_root / "complete.wav")
write_fixture_tags(music_root / "complete.wav", ["Rock"], ["Calm"])
create_wave_fixture(music_root / "genre-only.wav")
write_fixture_tags(music_root / "genre-only.wav", ["Rock"], [])
create_wave_fixture(music_root / "empty.wav")
```

This creates:

- one file with both Genre and Mood;
- one file with Genre only;
- one file with neither.

Add assertions:

```typescript
await page.getByRole('button', { name: 'Ohne Mood' }).click()
await expect(page.getByRole('checkbox', { name: 'complete.wav analysieren' })).toHaveCount(0)
await expect(page.getByRole('checkbox', { name: 'genre-only.wav analysieren' })).toBeVisible()

await page.getByRole('button', { name: 'Ohne Genre' }).click()
await expect(page.getByRole('checkbox', { name: 'empty.wav analysieren' })).toBeVisible()
await page.getByRole('checkbox', { name: 'Alle gefilterten Titel analysieren' }).check()
await page.getByRole('button', { name: /Titel analysieren/ }).click()
await expect(page.getByText('Analyse abgeschlossen')).toBeVisible()
```

After writing the empty file's result, assert it disappears from the active missing-tag filter without another library scan.

- [ ] **Step 2: Run the browser test and fix only workflow-specific regressions**

Run:

```powershell
npm --prefix frontend run e2e -- analysis-workbench.spec.ts
```

Expected: PASS for filtering, adaptive analysis, write synchronization, and disappearance from the active filter. If the environment cannot start Playwright, record the exact command and error; do not report it as passed.

- [ ] **Step 3: Run the repository source gate**

Run:

```powershell
python scripts/verify.py
```

Expected: PASS for formatting, static checks, Python tests, frontend tests, and build. Use the project-local pytest base temp configured by the script.

- [ ] **Step 4: Review readability and update active checklists**

Confirm every changed Python and TypeScript function stays at complexity 10 or below, error messages are German with stable codes, and no scan or admission path invokes a tag write. Mark this feature plan complete and add the missing-tag analysis feature to the roadmap without reordering the approved four product phases.

- [ ] **Step 5: Commit verification and documentation**

```powershell
git add scripts/e2e_server.py frontend/e2e/analysis-workbench.spec.ts docs/superpowers/plans/2026-07-16-essentia-studio-roadmap.md docs/superpowers/plans/2026-07-30-missing-managed-tags-analysis.md
git commit -m "test: verify missing tag analysis workflow"
```
