# Playlist Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing `.nsp` editor into a complete Playlist Studio with inventory scanning, M3U8 support, materialized mood and hybrid playlists, Navidrome synchronization, conflicts, and recoverable version history.

**Architecture:** Keep the current modular FastAPI/React/SQLite monolith and reuse the existing playlist catalog, validator, storage, repository, job, scheduler, and watcher boundaries. Add separate scanner, materializer, versioning, and adapter modules; Essentia Studio remains authoritative for managed definitions while native-compatible rules continue to export as NSP and concrete memberships synchronize through Navidrome with optional M3U8 backups.

**Tech Stack:** Python 3.10, FastAPI, Pydantic 2, SQLAlchemy/SQLite, httpx, pathlib, React/TypeScript, Vitest, Playwright.

## Global Constraints

- Preserve all existing 298 presets, 111 fields, 20 "This is" methods, custom NSP behavior, and current API compatibility.
- Essentia Studio is the source of truth for managed playlists.
- Scans are read-only; external playlists are never changed before explicit adoption.
- Every mutation requires a preview, creates a version, and uses fingerprint protection.
- M3U8 and NSP writes must use sibling temporary files, flush, `fsync`, and `os.replace`.
- Playlist paths must resolve canonically below configured roots; reject absolute client paths, traversal, and symlink escapes.
- Secrets are write-only, encrypted at rest using the application's secret facility, redacted from API responses, and excluded from logs.
- One playlist may not have two concurrent mutating jobs.
- Hand-written Python and TypeScript functions must keep cyclomatic complexity at or below 10.
- Core verification remains `python scripts/verify.py`; browser workflow changes require Playwright coverage.

---

### Task 1: Managed playlist domain and migrations

**Files:**
- Create: `backend/essentia_studio/db/migrations/0006_playlist_studio.sql`
- Create: `backend/essentia_studio/playlists/domain.py`
- Create: `backend/essentia_studio/repositories/playlist_studio.py`
- Create: `tests/repositories/test_playlist_studio.py`
- Modify: `backend/essentia_studio/playlists/models.py`

**Interfaces:**
- Consumes: existing playlist records, existing track/library identity, shared database session pattern.
- Produces: `ManagedPlaylist`, `PlaylistOverride`, `PlaylistMaterialization`, `PlaylistExportState`, `PlaylistVersion`; `PlaylistStudioRepository` CRUD and immutable version methods.

- [ ] **Step 1: Write failing repository lifecycle tests**

Cover creation of a managed definition, unique slug enforcement, pin/exclude/manual overrides, immutable materialization storage, export-state upsert, and restoration that creates a new version rather than deleting history.

Run: `python -m pytest tests/repositories/test_playlist_studio.py -q`

Expected: FAIL importing `PlaylistStudioRepository`.

- [ ] **Step 2: Add migration**

Create normalized tables:

- `managed_playlists`
- `playlist_track_overrides`
- `playlist_materializations`
- `playlist_materialization_tracks`
- `playlist_exports`
- `playlist_versions`
- `navidrome_profiles`

Use foreign keys with explicit delete behavior, UTC timestamps, unique `(playlist_id, track_id, override_type)`, and indexes for playlist status, adapter, remote ID, and version creation time.

- [ ] **Step 3: Add typed domain models**

Define enums for playlist kind, ownership, sync mode, override type, adapter type, rotation mode, and synchronization status. Use frozen Pydantic models for returned snapshots and validate JSON definitions by kind.

- [ ] **Step 4: Implement repository methods**

Implement focused methods for definition CRUD, override replacement, materialization append/read, export-state upsert, version append/list/read, and transactional restore. Repository methods must not perform filesystem, HTTP, or scoring work.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/repositories/test_playlist_studio.py -q`

Expected: PASS.

Commit: `feat: add playlist studio persistence model`

### Task 2: Portable M3U8 parser and atomic writer

**Files:**
- Create: `backend/essentia_studio/playlists/m3u.py`
- Create: `tests/playlists/test_m3u.py`

**Interfaces:**
- Produces: `parse_m3u(path, music_root) -> ParsedM3U`; `write_m3u8(path, track_paths, music_root) -> PlaylistFile`.

- [ ] **Step 1: Write failing parser and safety tests**

Test UTF-8/BOM input, comments, blank lines, POSIX and Windows separators, relative paths, absolute paths below music root, duplicate preservation during parse, path traversal rejection, outside-root rejection, symlink escape rejection, exact-byte fingerprint, and temp cleanup after failed replacement.

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/playlists/test_m3u.py -q`

Expected: FAIL importing `essentia_studio.playlists.m3u`.

- [ ] **Step 3: Implement parser**

Normalize entries without resolving ambiguous metadata. Return line number, original value, normalized relative path when valid, and a stable error code for invalid entries. Do not mutate files during parse.

- [ ] **Step 4: Implement atomic writer**

Write UTF-8 `#EXTM3U` and music-root-relative POSIX paths. Flush, `fsync`, and atomically replace. Reject empty filenames, non-`.m3u8` destinations, and paths outside the configured playlist directory.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/playlists/test_m3u.py -q`

Expected: PASS.

Commit: `feat: add safe m3u8 playlist storage`

### Task 3: Track resolver and playlist scanner

**Files:**
- Create: `backend/essentia_studio/playlists/resolver.py`
- Create: `backend/essentia_studio/playlists/scanner.py`
- Create: `backend/essentia_studio/repositories/playlist_inventory.py`
- Create: `backend/essentia_studio/db/migrations/0007_playlist_inventory.sql`
- Create: `tests/playlists/test_resolver.py`
- Create: `tests/playlists/test_scanner.py`

**Interfaces:**
- Consumes: library track repository, existing NSP storage, M3U parser, Navidrome connector interface from Task 7 through a protocol.
- Produces: `PlaylistResolver`; `PlaylistScanner.scan(request) -> PlaylistInventoryReport`.

- [ ] **Step 1: Write failing resolution tests**

Cover exact relative path, canonical absolute path below root, normalized artist/album/disc/track/title fallback, ambiguous metadata match, missing track, duplicate source entries, and alternate separators.

- [ ] **Step 2: Write failing scanner classification tests**

Use temporary NSP/M3U8 files and a fake remote connector. Assert classifications: `healthy`, `invalid`, `unresolved`, `duplicate`, `external`, `managed`, `adoptable`, and `conflict`. Assert scanning never changes source timestamps or remote calls beyond reads.

- [ ] **Step 3: Implement resolver**

Resolution order is exact normalized relative path, exact canonical absolute path, then metadata tuple. Ambiguous candidates remain unresolved and include candidate IDs for review.

- [ ] **Step 4: Implement inventory persistence and scanner**

Persist each scan and its entries separately from managed playlist definitions. Fingerprint exact source content. Continue after individual parse or connector failures and report per-source stable error codes.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/playlists/test_resolver.py tests/playlists/test_scanner.py -q`

Expected: PASS.

Commit: `feat: scan and classify playlist inventory`

### Task 4: Materialized selection definitions and scoring

**Files:**
- Create: `backend/essentia_studio/playlists/selection_models.py`
- Create: `backend/essentia_studio/playlists/scoring.py`
- Create: `backend/essentia_studio/playlists/candidates.py`
- Create: `tests/playlists/test_scoring.py`
- Create: `tests/playlists/test_candidates.py`

**Interfaces:**
- Produces: `validate_selection_definition`; `score_track`; `build_candidate_set`.

- [ ] **Step 1: Write failing definition tests**

Cover mood/static/hybrid/discovery/artist-mix/similarity definitions, positive and negative weights, hard ranges, confidence thresholds, target size, seed, and invalid unknown features or weight ranges.

- [ ] **Step 2: Write deterministic scoring tests**

Fixtures must prove normalized `[0,1]` scores, positive/negative contributions, hard rejection before scoring, confidence rejection, stable explanations, and identical output for identical input.

- [ ] **Step 3: Implement typed definitions**

Create small models for weighted features, numeric constraints, categorical constraints, user-state constraints, diversity, rotation, ordering, and export targets. Validation rejects contradictory ranges and impossible target sizes.

- [ ] **Step 4: Implement candidate and scoring services**

Keep raw feature access separate from scoring. Return `ScoredCandidate(track_id, score, contributions, rejection_reasons)` and never discard explanations.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/playlists/test_scoring.py tests/playlists/test_candidates.py -q`

Expected: PASS.

Commit: `feat: score playlist candidates from analysis`

### Task 5: Diversity, deduplication, ordering, and rotation

**Files:**
- Create: `backend/essentia_studio/playlists/deduplication.py`
- Create: `backend/essentia_studio/playlists/diversity.py`
- Create: `backend/essentia_studio/playlists/ordering.py`
- Create: `backend/essentia_studio/playlists/rotation.py`
- Create: `backend/essentia_studio/playlists/materializer.py`
- Create: `tests/playlists/test_materializer.py`

**Interfaces:**
- Produces: `PlaylistMaterializer.preview(definition, context) -> MaterializationPreview`.

- [ ] **Step 1: Write failing full materialization tests**

Cover alternate-version groups, quality preference, artist and album caps, minimum artist gap, fixed manual positions, pins, exclusions, stable seeded selection, exact target size where possible, and each rotation mode: replace, merge, rotate, append.

- [ ] **Step 2: Implement duplicate grouping**

Group by normalized primary artist/title with duration tolerance and release metadata. Select the preferred version from explicit quality, confidence, rating, and definition preference; record rejected version reasons.

- [ ] **Step 3: Implement constraint-aware diversity selection**

Select incrementally while enforcing caps and artist gap. Reconsider skipped candidates to fill target size without violating hard rules. Never remove pins.

- [ ] **Step 4: Implement ordering and rotation**

Support score, metadata fields, seeded shuffle, BPM/energy progression, and manual positions. Rotation compares prior membership and preserves configured percentage plus all pins.

- [ ] **Step 5: Implement materializer orchestration**

The materializer returns ordered selections, scores, explanation, rejected summary, warnings, definition hash, library revision, seed, and content hash. It performs no writes.

- [ ] **Step 6: Verify and commit**

Run: `python -m pytest tests/playlists/test_materializer.py -q`

Expected: PASS.

Commit: `feat: materialize diverse rotating playlists`

### Task 6: Playlist versions, preview, export coordination, and conflicts

**Files:**
- Create: `backend/essentia_studio/playlists/versions.py`
- Create: `backend/essentia_studio/playlists/conflicts.py`
- Create: `backend/essentia_studio/services/playlist_studio.py`
- Create: `tests/services/test_playlist_studio.py`

**Interfaces:**
- Consumes: repository, materializer, NSP storage, M3U8 writer, adapter protocol.
- Produces: `PlaylistStudioService.scan/preview/adopt/export/restore/delete_managed`.

- [ ] **Step 1: Write failing service tests**

Test preview has no writes, adoption snapshots external content, every export creates a version, unchanged destination exports safely, local-only change exports, remote-only change follows sync mode, both-changed creates conflict, failed export preserves prior destination, and restore creates a new version.

- [ ] **Step 2: Implement three-way conflict detection**

Compare last-export fingerprint, current local materialization, and current destination fingerprint. Return stable outcomes instead of booleans.

- [ ] **Step 3: Implement service orchestration**

Select NSP only when the definition is fully catalog-compatible; otherwise synchronize Navidrome and optionally write M3U8. Capture version before mutation and update export state only after all required writes succeed.

- [ ] **Step 4: Add per-playlist mutation lock**

Use the existing job serialization infrastructure and a playlist-ID lock key. Concurrent preview is allowed; concurrent mutation returns `playlist_job_running`.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/services/test_playlist_studio.py -q`

Expected: PASS.

Commit: `feat: coordinate versioned playlist exports`

### Task 7: Navidrome profile and connector

**Files:**
- Create: `backend/essentia_studio/navidrome/__init__.py`
- Create: `backend/essentia_studio/navidrome/models.py`
- Create: `backend/essentia_studio/navidrome/client.py`
- Create: `backend/essentia_studio/navidrome/adapter.py`
- Create: `backend/essentia_studio/repositories/navidrome_profiles.py`
- Create: `tests/navidrome/test_client.py`
- Create: `tests/navidrome/test_adapter.py`

**Interfaces:**
- Produces: `NavidromeClient`; `NavidromePlaylistAdapter`; scanner read protocol and export adapter protocol.

- [ ] **Step 1: Write mocked HTTP contract tests**

Test connection, authentication failure, timeout, bounded retry for transient errors, playlist list/get/create/update/delete, user-specific metadata reads, malformed responses, and redacted exceptions.

- [ ] **Step 2: Implement profile storage**

Store URL, username, encrypted secret, TLS verification, timeout, and enabled state. Responses expose `has_secret` only. Updating non-secret fields does not clear the secret.

- [ ] **Step 3: Implement Subsonic client**

Use `httpx` with explicit connect/read timeouts and application/client version parameters. Parse `subsonic-response.status` and server errors into stable domain codes.

- [ ] **Step 4: Implement playlist adapter**

Resolve local tracks to remote song IDs using a cached library index and exact path/metadata rules. Replace membership deterministically and expose remote fingerprint from ordered song IDs.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/navidrome -q`

Expected: PASS.

Commit: `feat: synchronize playlists with navidrome`

### Task 8: Playlist Studio API

**Files:**
- Create: `backend/essentia_studio/schemas/playlist_studio.py`
- Create: `backend/essentia_studio/api/routes/playlist_studio.py`
- Modify: `backend/essentia_studio/api/router.py`
- Modify: `backend/essentia_studio/api/routes/playlists.py`
- Create: `tests/api/test_playlist_studio.py`

**Interfaces:**
- Produces: typed inventory, definition, preview, adoption, export, conflict, version, restore, and profile endpoints.

- [ ] **Step 1: Write failing endpoint contract tests**

Cover:

- `GET /api/playlist-studio/inventory`
- `POST /api/playlist-studio/scan`
- managed playlist CRUD
- preview
- adopt external playlist
- export/synchronize
- conflicts and conflict resolution
- versions and restore
- Navidrome profile CRUD/test

Assert secrets are never returned and legacy `/api/playlists` behavior remains unchanged.

- [ ] **Step 2: Implement schemas**

Use discriminated unions by playlist kind and adapter type. Response objects include warnings, explanations, fingerprints, status, and available actions.

- [ ] **Step 3: Implement routes**

Routes contain only request mapping and service calls. Scanner and mutating operations submit persistent jobs and return job IDs; read and preview endpoints may execute synchronously within existing limits.

- [ ] **Step 4: Normalize errors**

Add stable codes for invalid selection, unresolved track, playlist conflict, destination unavailable, authentication failure, unsafe path, external playlist not adopted, and concurrent mutation.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/api/test_playlist_studio.py tests/api/test_playlists.py -q`

Expected: PASS.

Commit: `feat: expose playlist studio api`

### Task 9: Scheduler and watcher integration

**Files:**
- Modify: `backend/essentia_studio/services/automation.py`
- Modify: `backend/essentia_studio/jobs/models.py`
- Modify: `backend/essentia_studio/jobs/runner.py`
- Create: `tests/services/test_playlist_automation.py`

**Interfaces:**
- Produces persistent job types for scan, preview, materialize/export, sync, repair, and restore.

- [ ] **Step 1: Write failing automation tests**

Test quiet-period coalescing, analysis-completion trigger, schedule trigger, disabled playlist, failed profile isolation, per-playlist serialization, and retry without duplicate version/export rows.

- [ ] **Step 2: Add job payloads and handlers**

Use stable playlist IDs and profile IDs. Jobs reload current definitions when they start and verify expected definition hash before mutation.

- [ ] **Step 3: Integrate triggers**

After successful analysis, enqueue only enabled playlists whose dependencies intersect changed features. Schedule materialization and optional Navidrome resync separately.

- [ ] **Step 4: Verify and commit**

Run: `python -m pytest tests/services/test_playlist_automation.py -q`

Expected: PASS.

Commit: `feat: automate managed playlist updates`

### Task 10: Playlist Studio frontend shell and inventory

**Files:**
- Create: `frontend/src/features/playlist-studio/PlaylistStudioView.tsx`
- Create: `frontend/src/features/playlist-studio/api.ts`
- Create: `frontend/src/features/playlist-studio/types.ts`
- Create: `frontend/src/features/playlist-studio/InventoryView.tsx`
- Create: `frontend/src/features/playlist-studio/PlaylistLibrary.tsx`
- Create: `frontend/src/features/playlist-studio/HealthBadge.tsx`
- Create: `frontend/src/features/playlist-studio/PlaylistStudioView.test.tsx`
- Modify: `frontend/src/app/App.tsx`

**Interfaces:**
- Consumes Playlist Studio API.
- Produces one unified playlist navigation area while retaining access to existing NSP workflows.

- [ ] **Step 1: Write failing UI tests**

Test inventory filtering, health states, managed/external distinction, read-only scan, adoption preview, and opening existing NSP definitions in the current rule editor.

- [ ] **Step 2: Implement shell and inventory**

Provide sections for library, scanner, editor, synchronization, and versions. Do not duplicate existing preset and NSP rule components; embed or adapt them behind the new shell.

- [ ] **Step 3: Add adoption and repair previews**

Every action shows planned changes, unresolved tracks, destination, and whether the playlist becomes managed.

- [ ] **Step 4: Verify and commit**

Run: `npm --prefix frontend test -- --run src/features/playlist-studio`

Expected: PASS.

Commit: `feat: add playlist studio inventory ui`

### Task 11: Definition, track, mood, and hybrid editors

**Files:**
- Create: `frontend/src/features/playlist-studio/DefinitionEditor.tsx`
- Create: `frontend/src/features/playlist-studio/MoodEditor.tsx`
- Create: `frontend/src/features/playlist-studio/DiversityEditor.tsx`
- Create: `frontend/src/features/playlist-studio/RotationEditor.tsx`
- Create: `frontend/src/features/playlist-studio/TrackEditor.tsx`
- Create: `frontend/src/features/playlist-studio/MaterializationPreview.tsx`
- Create: `frontend/src/features/playlist-studio/ScoreExplanation.tsx`
- Create: `frontend/src/features/playlist-studio/DefinitionEditor.test.tsx`

**Interfaces:**
- Produces creation/editing for all playlist kinds and preview-first mutation requests.

- [ ] **Step 1: Write failing editor tests**

Cover weighted positive/negative features, hard constraints, artist/album caps, minimum artist gap, target size, seed, rotation, track search, drag ordering, pins, exclusions, manual tracks, validation errors, and preview explanation.

- [ ] **Step 2: Implement kind-aware definition editor**

Reuse existing NSP RuleBuilder for `smart_nsp`. Use catalog and API capabilities rather than hardcoded feature names. Preserve unknown future definition fields when editing supported sections.

- [ ] **Step 3: Implement track membership editor**

Support search, filters, add/remove, drag reorder, pin, exclude, fixed position, and reason display. Mark generated versus manual membership clearly.

- [ ] **Step 4: Implement preview and diff**

Show selected scores, contribution details, rejection summary, diversity decisions, output adapter, files/remote target, and changes from current membership.

- [ ] **Step 5: Verify and commit**

Run: `npm --prefix frontend test -- --run src/features/playlist-studio`

Expected: PASS.

Commit: `feat: edit materialized and hybrid playlists`

### Task 12: Navidrome profiles, conflicts, versions, and E2E

**Files:**
- Create: `frontend/src/features/playlist-studio/NavidromeProfiles.tsx`
- Create: `frontend/src/features/playlist-studio/SyncStatus.tsx`
- Create: `frontend/src/features/playlist-studio/ConflictResolver.tsx`
- Create: `frontend/src/features/playlist-studio/VersionHistory.tsx`
- Create: `frontend/e2e/playlist-studio.spec.ts`
- Modify: `README.md`
- Modify: `docs/architecture.md`

**Interfaces:**
- Completes configuration, conflict resolution, restore, documentation, and browser workflow.

- [ ] **Step 1: Write failing profile/conflict/version tests**

Assert secret redaction, connection status, three-way diff, no silent overwrite, restore preview, and restored version creation.

- [ ] **Step 2: Implement profile and sync UI**

Credentials are write-only fields. Test connection is explicit. Show profile user ownership and destination status per playlist.

- [ ] **Step 3: Implement conflict and version UI**

Display base/local/remote memberships and order. Provide explicit actions allowed by sync mode. Restore always previews and creates a new version.

- [ ] **Step 4: Add Playwright end-to-end workflow**

The E2E test must scan temporary NSP/M3U8 sources, adopt a playlist, create a mood/hybrid definition, preview, export to a mocked Navidrome server, simulate an external modification, detect conflict, resolve it explicitly, and restore a previous version.

- [ ] **Step 5: Update documentation**

Document playlist kinds, source-of-truth rules, NSP/API/M3U8 adapter selection, Navidrome profile setup, automation, conflict behavior, backup/restore, and trusted-LAN security.

- [ ] **Step 6: Run complete verification**

Run:

```text
python scripts/verify.py
npm --prefix frontend run e2e -- e2e/playlists.spec.ts e2e/playlist-studio.spec.ts
```

Expected: all source, migration, catalog parity, existing playlist, new Playlist Studio, and browser tests PASS.

- [ ] **Step 7: Commit**

Commit: `feat: complete navidrome playlist studio`

## Completion evidence

- Existing NSP catalog parity and all legacy playlist tests pass.
- Scanner inventories NSP, M3U/M3U8, Navidrome, and managed definitions without mutation.
- Materialization is deterministic and explains selection and rejection.
- Pins, exclusions, diversity, deduplication, ordering, and all rotation modes have focused tests.
- Native rules export as NSP; concrete memberships synchronize to a selected Navidrome profile and optionally write M3U8.
- Three-way fingerprints prevent silent overwrite.
- Every mutation is versioned and restorable.
- Full `scripts/verify.py` and both playlist Playwright suites pass.