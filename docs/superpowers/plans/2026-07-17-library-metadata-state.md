# Library Metadata and State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show artist, title, album, duration, and a reliable processing state for every scanned track while keeping path fallbacks and analysis history safe.

**Architecture:** A focused `MetadataService` enriches immutable scan records before `TrackRepository` persists them. `TrackStateService` derives state from the current fingerprint, latest analysis, job item, and verified write; API schemas expose these values and the React tables render them without merging analysis-selection and write-selection state.

**Tech Stack:** Python 3.10, Mutagen 1.47, SQLAlchemy 2.0, FastAPI/Pydantic 2, React 19, TypeScript, Vitest.

## Global Constraints

- Embedded tags win over filename, directory, and fallback values.
- Supported extensions remain `aac`, `aif`, `aiff`, `ape`, `dsf`, `flac`, `m4a`, `m4b`, `mp+`, `mp3`, `mp4`, `mpc`, `oga`, `ogg`, `opus`, `wav`, `wma`, and `wv`.
- Scanning never writes to audio files.
- Automation may skip current tracks later, but manual analysis remains possible.
- Existing library, analysis, write, and undo rows must migrate without data loss.
- Standard result queries return only the newest relevant analysis per track.

---

### Task 1: Metadata value object and fallback parser

**Files:**
- Modify: `backend/essentia_studio/domain/tracks.py`
- Create: `backend/essentia_studio/services/metadata.py`
- Create: `tests/services/test_metadata.py`

**Interfaces:**
- Produces: `TrackMetadata(artist: str, title: str, album: str | None, duration_seconds: float | None, source: MetadataSource)`.
- Produces: `MetadataService.read(path: Path, relative_path: str) -> TrackMetadata`.
- Consumes: Mutagen `File(path, easy=True)` and `audio.info.length`.

- [ ] **Step 1: Write failing parser tests**

```python
def test_filename_and_directory_fallbacks() -> None:
    assert metadata_from_path(Path("Bastille/Doom Days/Bastille - 01 - Joy.flac")) == TrackMetadata(
        artist="Bastille", title="Joy", album="Doom Days", duration_seconds=None,
        source="filename",
    )
    assert metadata_from_path(Path("Underworld/Album/08 - Rez.flac")).artist == "Underworld"
    assert metadata_from_path(Path("loose-file.wav")).artist == "Unbekannter Interpret"
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `.venv/bin/python -m pytest tests/services/test_metadata.py -q`

Expected: import failure for `essentia_studio.services.metadata`.

- [ ] **Step 3: Implement deterministic path parsing**

```python
MetadataSource = Literal["embedded", "filename", "directory", "fallback"]

@dataclass(frozen=True, slots=True)
class TrackMetadata:
    artist: str
    title: str
    album: str | None
    duration_seconds: float | None
    source: MetadataSource

def metadata_from_path(relative_path: Path) -> TrackMetadata:
    # Strip extension and a leading numeric track token; recognize two dash-separated forms.
    # Use parent[-2] as artist and parent[-1] as album when the filename has no artist.
```

- [ ] **Step 4: Add failing embedded-tag tests with a real temporary ID3 file**

```python
def test_embedded_tags_override_path(tmp_path: Path) -> None:
    path = tmp_path / "Wrong" / "Album" / "wrong.mp3"
    path.parent.mkdir(parents=True)
    ID3().save(path)
    tags = ID3(path)
    tags.add(TPE1(encoding=3, text=["Correct Artist"]))
    tags.add(TIT2(encoding=3, text=["Correct Title"]))
    tags.add(TALB(encoding=3, text=["Correct Album"]))
    tags.save(path)
    metadata = MetadataService().read(path, "Wrong/Album/wrong.mp3")
    assert (metadata.artist, metadata.title, metadata.album, metadata.source) == (
        "Correct Artist", "Correct Title", "Correct Album", "embedded"
    )
```

- [ ] **Step 5: Implement safe Mutagen reading and duration**

Use `mutagen.File(path, easy=True)`, select the first nonblank tag value, join multiple artists with `; `, read `audio.info.length` when finite and positive, and fall back per field without throwing for unsupported or malformed metadata.

- [ ] **Step 6: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/services/test_metadata.py -q`

Expected: all metadata tests pass.

Commit: `feat: read library artist and title metadata`

---

### Task 2: Persist metadata during scans

**Files:**
- Create: `backend/essentia_studio/db/migrations/0006_track_metadata.sql`
- Modify: `backend/essentia_studio/domain/tracks.py`
- Modify: `backend/essentia_studio/services/scanner.py`
- Modify: `backend/essentia_studio/repositories/tracks.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `tests/services/test_scanner.py`
- Modify: `tests/repositories/test_tracks.py`

**Interfaces:**
- `ScannedTrack` and `LibraryTrack` gain `metadata: TrackMetadata`.
- `scan_music_root(root: Path, metadata_service: MetadataService) -> Iterator[ScannedTrack]`.

- [ ] **Step 1: Add failing migration and repository tests**

```python
def test_scan_persists_and_updates_metadata(engine) -> None:
    repository = TrackRepository(engine)
    repository.replace_scan([scanned_track("Artist/Album/song.flac", title="Song")], NOW)
    stored = repository.get_by_path("Artist/Album/song.flac")
    assert stored.metadata.artist == "Artist"
    assert stored.metadata.title == "Song"
    assert stored.metadata.duration_seconds == 185.25
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/repositories/test_tracks.py tests/services/test_scanner.py -q`

Expected: constructors or SQL columns are missing.

- [ ] **Step 3: Add nullable migration columns and repository mapping**

```sql
ALTER TABLE library_tracks ADD COLUMN artist TEXT;
ALTER TABLE library_tracks ADD COLUMN title TEXT;
ALTER TABLE library_tracks ADD COLUMN album TEXT;
ALTER TABLE library_tracks ADD COLUMN duration_seconds REAL;
ALTER TABLE library_tracks ADD COLUMN metadata_source TEXT;
```

Update the UPSERT, all SELECT projections, `_parameters`, and `_track_from_row`. Existing rows remain nullable until the next scan.

- [ ] **Step 4: Inject `MetadataService` into scanning**

Construct it once in `main.py`; the scan handler calls `scan_music_root(music_root, metadata_service)`. Keep extension filtering and symlink rejection unchanged.

- [ ] **Step 5: Run repository, scanner, migration, and full backend tests**

Run: `.venv/bin/python -m pytest tests/repositories/test_tracks.py tests/services/test_scanner.py tests/db -q`

Expected: focused tests pass.

Run: `.venv/bin/python -m pytest -q`

Expected: no regression.

- [ ] **Step 6: Commit**

Commit: `feat: persist scanned track metadata`

---

### Task 3: Derive current processing state and deduplicate results

**Files:**
- Create: `backend/essentia_studio/services/track_state.py`
- Modify: `backend/essentia_studio/repositories/results.py`
- Modify: `backend/essentia_studio/repositories/tracks.py`
- Modify: `backend/essentia_studio/domain/tracks.py`
- Create: `tests/services/test_track_state.py`
- Modify: `tests/repositories/test_results.py`

**Interfaces:**
- Produces: `ProcessingState = Literal["new", "current", "changed", "written", "failed"]`.
- Produces: `TrackStateService.states(track_ids: list[int]) -> dict[int, ProcessingState]` using batched SQL, not per-row queries.
- `ResultRepository.query(...)` returns only the latest result per track by `created_at DESC, id DESC`.

- [ ] **Step 1: Write failing state precedence tests**

```python
@pytest.mark.parametrize(("facts", "expected"), [
    ({}, "new"),
    ({"analysis_matches": True}, "current"),
    ({"analysis_exists": True, "analysis_matches": False}, "changed"),
    ({"analysis_matches": True, "verified_write_matches": True}, "written"),
    ({"last_attempt_failed": True}, "failed"),
])
def test_processing_state_precedence(facts, expected):
    assert derive_processing_state(**facts) == expected
```

- [ ] **Step 2: Verify RED, then implement the pure precedence function**

Run: `.venv/bin/python -m pytest tests/services/test_track_state.py -q`

Expected: missing function; after implementation, PASS.

- [ ] **Step 3: Add failing repository integration tests**

Create two analysis rows for one track and assert the default result query returns exactly the newest one. Create a verified write with matching post-write fingerprint and assert the track state is `written`.

- [ ] **Step 4: Implement batched SQL and latest-result CTE**

Use `ROW_NUMBER() OVER (PARTITION BY ar.track_id ORDER BY ar.created_at DESC, ar.id DESC)` for latest results. Build one state query joining the current track, latest analysis, latest job item, and latest write operation.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/services/test_track_state.py tests/repositories/test_results.py -q`

Commit: `feat: derive current track processing state`

---

### Task 4: Expose metadata and state through APIs

**Files:**
- Modify: `backend/essentia_studio/schemas/library.py`
- Modify: `backend/essentia_studio/api/routes/library.py`
- Modify: `backend/essentia_studio/schemas/results.py`
- Modify: `backend/essentia_studio/api/routes/results.py`
- Modify: `backend/essentia_studio/api/dependencies.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `tests/api/test_library.py`
- Modify: `tests/api/test_results.py`

**Interfaces:**
- Track/result responses add `artist`, `title`, `album`, `duration_seconds`, `metadata_source`, and `processing_state`.
- Library/result `search` matches artist, title, album, and relative path case-insensitively.

- [ ] **Step 1: Write failing API response and search tests**

```python
def test_library_returns_metadata_and_searches_artist(client, scanned_library):
    response = client.get("/api/library/tracks", params={"search": "bastille"})
    item = response.json()["items"][0]
    assert item["artist"] == "Bastille"
    assert item["title"] == "Joy"
    assert item["processing_state"] == "new"
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/api/test_library.py tests/api/test_results.py -q`

- [ ] **Step 3: Implement schema fields, service injection, and expanded search**

Keep page size limits and current filter semantics unchanged. State lookup must be batched for the page.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/api/test_library.py tests/api/test_results.py -q`

Commit: `feat: expose track metadata and processing state`

---

### Task 5: Render artist/title and truthful analysis status

**Files:**
- Modify: `frontend/src/features/workbench/types.ts`
- Modify: `frontend/src/features/workbench/LibraryTable.tsx`
- Modify: `frontend/src/features/workbench/ResultTable.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.tsx`
- Modify: `frontend/src/features/workbench/WorkbenchView.test.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Library and result rows use metadata returned by Task 4.
- Terminal job copy uses `event.payload.status` and `failed_items`; `completed_with_errors` must never say only `Analyse abgeschlossen`.

- [ ] **Step 1: Write failing frontend tests**

```tsx
test('shows artist and title instead of using the full path as title', async () => {
  render(<WorkbenchView />)
  expect(await screen.findByText('Quarter Past Midnight')).toBeVisible()
  expect(screen.getByText('Bastille')).toBeVisible()
})

test('reports failed analysis instead of success', async () => {
  // Emit terminal payload with completed_with_errors and failed_items: 1.
  expect(await screen.findByText('Analyse beendet – 1 Titel fehlgeschlagen')).toBeVisible()
})
```

- [ ] **Step 2: Verify RED**

Run: `npm --prefix frontend test -- --run WorkbenchView.test.tsx`

- [ ] **Step 3: Implement table columns, state badges, secondary paths, and terminal copy**

Artist/title are primary; album, format, state, and path remain visible without making the table wider than its scroll container. Preserve all checkbox accessible names.

- [ ] **Step 4: Run frontend verification and commit**

Run: `npm --prefix frontend run lint && npm --prefix frontend test -- --run && npm --prefix frontend run typecheck && npm --prefix frontend run build`

Commit: `feat: show library artist title and state`

---

### Task 6: Metadata integration verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/deployment/apple-container.md`
- Modify: `docs/deployment/linux-docker.md`
- Modify: `docs/deployment/windows.md`
- Modify: `tests/docs/test_commands.py`

- [ ] **Step 1: Add failing documentation assertions**

Assert the supported extension list and metadata fallback order are documented once in README or linked deployment documentation.

- [ ] **Step 2: Update documentation**

Describe embedded-tag precedence, path fallbacks, derived processing states, and the fact that scanning does not modify files.

- [ ] **Step 3: Run full source verification**

Run: `.venv/bin/python scripts/verify.py`

Expected: pytest, Ruff, ESLint, Vitest, TypeScript, and Vite all exit 0.

- [ ] **Step 4: Commit**

Commit: `docs: explain library metadata and processing states`
