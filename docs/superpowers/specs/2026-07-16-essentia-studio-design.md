# Essentia Studio – Product Design

**Status:** Approved design

**Date:** 2026-07-16
**Upstream sources:**

- `WB2024/Essentia-to-Metadata`
- `WB2024/Navidrome-SmartPlaylist-Generator-nsp`

## 1. Product goal

Essentia Studio turns the command-line Essentia tagger into a self-contained web application for a locally mounted music library. It analyzes genre and mood with the existing Essentia TensorFlow models, keeps every result as a reviewable draft, supports manual corrections, and writes only explicitly selected results. The same application also exposes the complete Navidrome Smart Playlist Generator feature set for creating and managing `.nsp` files.

The initial deployment targets a trusted local network. It has no login screen or user accounts. The default image uses CPU inference; a separate NVIDIA CUDA image provides GPU inference on compatible Linux hosts.

## 2. Scope

### Included

- Private, standalone GitHub repository retaining the original Git history and a read-only `upstream` remote.
- One FastAPI application serving a compiled React/Vite frontend and a JSON API.
- SQLite persistence for settings, jobs, drafts, audit history, and original tags.
- Library scanning exclusively beneath a configured container mount, default `/music`.
- Genre and mood analysis using the existing Discogs EffNet and MTG-Jamendo models.
- Live job progress, cancellation, partial-result retention, and resumable incomplete jobs.
- Result preview with per-track selection, multi-select, and select-all.
- Manual addition and removal of genre and mood values before writing.
- Selective tag writes, write verification, conflict detection, and tag-level undo.
- Full Navidrome Smart Playlist Generator behavior: all fields, operators, sorts, presets, nested rule groups, all “This is …” methods, and create/edit/delete management.
- CPU and NVIDIA CUDA OCI images.
- Local Apple Container instructions, Windows 11/Docker Desktop development instructions, and Linux Docker Compose examples.
- CI, automated release PRs, GitHub Releases, and private GHCR images.

### Explicitly excluded from the first release

- User accounts, authentication, roles, or internet-facing hardening.
- Browser uploads or copying music into the container.
- A remote OpenAI-, Ollama-, or vLLM-based inference mode.
- Apple Metal acceleration.
- Full audio-file backups. Undo restores only the tag fields managed by the application.
- Native Linux ARM64 images while the required `essentia-tensorflow` Linux wheel remains x86-64-only.

## 3. Repository and licensing model

GitHub does not permit a private fork of a public repository in the normal fork network. The project is therefore a private standalone copy:

- `origin` points to the private repository `Skrockle/Essentia-Studio`.
- `upstream` points to `WB2024/Essentia-to-Metadata`.
- The original commit history is retained.
- The playlist generator is imported with clear source attribution and its license retained.
- Upstream synchronization is deliberate: fetch from `upstream`, review, then merge or cherry-pick.

The product source follows the upstream MIT licensing notices. Documentation must separately disclose that Essentia itself is AGPL-3.0 and that the bundled pretrained models are distributed under CC BY-NC-ND 4.0 and are not licensed for commercial use. Image labels and the About view link to all applicable notices.

## 4. System architecture

The application is a modular monolith. A single container serves the frontend and API, while module boundaries keep analysis, tag writing, playlists, and platform concerns independently testable.

### 4.1 Runtime components

1. **React/Vite frontend**
   - Compiled to static assets during the image build.
   - Served by FastAPI from the same origin.
   - Uses HTTP for commands and Server-Sent Events for job progress.

2. **FastAPI service**
   - Owns validation, persistence, orchestration, and API contracts.
   - Exposes health, capability, library, analysis, write, undo, settings, and playlist endpoints.

3. **Job coordinator**
   - Executes one ordered queue of scan, analysis, write, undo, and playlist jobs.
   - Uses a configurable worker count for analysis.
   - Persists state transitions before broadcasting progress.

4. **Essentia analysis adapter**
   - Extracts the reusable model-loading and inference behavior from `tag_music.py`.
   - Loads the embedding, genre, and mood models once per worker.
   - Produces normalized domain results without writing tags.

5. **Tag service**
   - Reads and writes format-specific genre, mood, and optional confidence tags with Mutagen.
   - Captures exact managed tag values before a write.
   - Re-reads the file after a write and verifies the requested values.

6. **Smart playlist service**
   - Extracts the playlist generator's catalogs and rule engine from its terminal UI.
   - Preserves every upstream preset, field, operator, sort option, and “This is …” method.
   - Validates and atomically persists `.nsp` JSON files.

7. **SQLite repository**
   - Uses one database at `/data/essentia-studio.db` by default.
   - Applies ordered schema migrations at startup.
   - Uses foreign keys, WAL mode, and short transactions.

### 4.2 Module boundaries

The analysis adapter never writes files. The tag service never invokes machine learning. The playlist service operates only on playlist definitions and `.nsp` files. API routes depend on application services rather than Mutagen, Essentia, or raw SQL directly. This prevents the original large scripts from becoming a new monolithic backend file.

## 5. Persistent data model

The database contains the following concepts:

- **settings** – music root, playlist directory, worker count, maximum audio duration, thresholds, genre count, confidence-tag setting, overwrite policy, and compute preference.
- **library_tracks** – stable identifier, relative path, extension, size, modification time, and last-seen timestamp. Absolute host paths are never stored.
- **jobs** – type, status, progress counts, timestamps, configuration snapshot, error summary, and cancellation flag.
- **analysis_results** – track, job, raw model scores, formatted suggestions, analyzed fingerprint, and model identifiers.
- **tag_drafts** – editable genre and mood arrays, dirty state, validation state, and selection state.
- **write_operations** – requested values, original managed tags, pre-write fingerprint, post-write fingerprint, verification result, and per-file error.
- **playlist_records** – file name, display name, parsed definition, on-disk fingerprint, source mode, and last operation.
- **events** – bounded job event history for reconnecting clients and audit display.

Genre and mood values are stored as JSON arrays at the domain boundary, never as pre-joined strings. Each format adapter performs its own final serialization.

## 6. Core workflows

### 6.1 Startup and preflight

At startup the service:

1. Migrates the database.
2. Confirms that `/music` exists and is readable.
3. Checks whether the configured playlist directory exists or can be created.
4. Confirms model files and their expected identifiers.
5. Detects the image variant and available TensorFlow devices.
6. Exposes all findings through `/api/capabilities` and the Settings view.

A CPU image reports CPU as its only compute mode. A CUDA image permits `auto`, `cpu`, or `cuda`; `auto` selects CUDA only when TensorFlow actually reports a GPU. Selecting unavailable CUDA is rejected with a precise diagnostic.

### 6.2 Library scan

The scan walks only beneath the canonical configured music root. Symlinks resolving outside that root are excluded. Supported audio files are recorded by relative path and fingerprint. Missing files are marked absent rather than immediately deleting their history. A rescan is read-only and does not start analysis automatically.

### 6.3 Analysis

The user filters and selects tracks, chooses genre/mood options, and starts a job. The coordinator snapshots all analysis settings. Workers load models once, process tracks independently, and persist each result immediately. One track failure increments the error count but does not stop the batch. Cancellation stops scheduling new tracks; completed results remain reviewable. Resuming creates a linked job for unfinished tracks using the same settings snapshot.

### 6.4 Review and manual editing

Analysis results enter the Workbench as drafts. The table supports individual checkboxes, range/multi-selection, and select-all for the current filtered result set. Genre and mood chips can be removed; free-form values can be added and normalized. Bulk edits apply only to selected rows and always show the affected count before confirmation. Nothing in this workflow modifies an audio file.

### 6.5 Selective write

Before writing each selected track, the service compares its current size and modification time with the analyzed fingerprint and re-reads the managed tags. If the file changed, that row becomes a conflict and is skipped until re-analyzed or explicitly refreshed.

For a valid row the service stores the original managed tag fields, writes the requested values, reopens the file, and verifies the result. Successes and failures are recorded per track. A failed file does not roll back successful files in the same batch. No database record claims success until read-back verification passes.

### 6.6 Undo

Undo is available for a verified write operation while the file still matches the recorded post-write fingerprint. It restores the exact managed genre, mood, and application confidence-tag values captured before that write. It does not restore unrelated metadata or damaged audio content. Undo itself is verified and audited as a new operation.

### 6.7 Smart playlists

The Playlist area supports four entry paths:

- browse and instantiate any upstream preset;
- build arbitrary nested `all`/`any` rule groups;
- create any supported “This is …” playlist;
- open and edit an existing `.nsp` file.

The browser editor is driven by the extracted field/operator catalog, so value controls match field types. The API validates rule structure and allowed operators. File names are sanitized and confined to the configured playlist directory. Save writes UTF-8 JSON to a temporary sibling file, flushes it, then atomically renames it. Edit and delete require an unchanged on-disk fingerprint to prevent overwriting external modifications.

## 7. API shape

The public API is versioned below `/api` and grouped by capability:

- `GET /health` and `GET /api/capabilities`
- `GET/PUT /api/settings`
- `POST /api/library/scan`, `GET /api/library/tracks`
- `POST /api/analysis/jobs`, `GET /api/jobs`, `GET /api/jobs/{id}`
- `POST /api/jobs/{id}/cancel`, `POST /api/jobs/{id}/resume`
- `GET /api/jobs/{id}/events` as Server-Sent Events
- `GET/PATCH /api/results` for filtering, selection, and draft edits
- `POST /api/writes`, `POST /api/writes/{id}/undo`
- `GET /api/playlists/catalog`, including presets and rule metadata
- `GET/POST /api/playlists`, `GET/PUT/DELETE /api/playlists/{name}`

All mutation endpoints use typed request models. Track and playlist paths are relative identifiers resolved server-side beneath approved roots. Error responses use one consistent structure with a machine-readable code, user-facing German message, and optional field details.

## 8. Frontend design

The approved visual direction is a modern studio workbench rather than a generic admin dashboard.

### 8.1 Visual language

- Cool paper-gray surfaces with ink-blue structure.
- Blue genre accents, purple mood accents, and signal-orange status accents.
- Space Grotesk headings, Manrope body text, and IBM Plex Mono for technical values.
- Dense but calm information hierarchy, generous alignment, and waveform-inspired details.
- Accessible focus rings, keyboard operation, reduced-motion support, and meaningful empty states.

### 8.2 Primary areas

1. **Workbench** – scan controls, filters, job state, result table, selection toolbar, inline tag editor, and write preview.
2. **Playlists** – preset browser, “This is …” builder, nested custom rule editor, preview, and existing-file management.
3. **Jobs & history** – active queue, per-file errors, completed writes, and undo actions.
4. **Settings** – paths, analysis defaults, worker limits, compute capability, model identifiers, and storage health.
5. **About** – version, image variant, upstream revisions, and licenses.

The interface is responsive for desktop and tablet. Phones receive a functional stacked layout, but wide result editing remains optimized for desktop use.

## 9. Error handling and concurrency

Job status follows `queued → running → completed|completed_with_errors|cancelled|failed`. Per-item status is independent. Unexpected worker termination marks only its active item failed and permits the coordinator to continue or stop cleanly according to worker health.

Only one filesystem-mutating job runs at a time. Analysis may use multiple processes, but write, undo, and playlist mutation are serialized. SQLite transactions never span model inference or filesystem writes. The event stream is reconstructible from persisted job state after a browser reconnect.

Logs use structured fields and never include host paths outside the container-visible mount. User-facing diagnostics explain permission errors, unsupported files, model failures, stale fingerprints, and unavailable GPU devices.

## 10. Container packaging

### 10.1 CPU image

- Default and recommended image.
- Python 3.10 runtime matching the existing application and Essentia GPU guidance.
- Pinned `essentia-tensorflow==2.1b6.dev1389` x86-64 wheel for Python 3.10 and pinned model checksums.
- Published as `latest`, `latest-cpu`, version tag, and version-`cpu` tag.

### 10.2 CUDA image

- NVIDIA CUDA 11.8 and cuDNN 8 runtime base, matching the existing upstream GPU image line.
- Same application, models, and API as the CPU image.
- Startup capability check confirms that TensorFlow sees the requested GPU.
- Published only with explicit `-cuda` tags.

Both images target `linux/amd64`. They run as a non-root application user, expose port `8000`, use `/music` for media and `/data` for persistent application state, and include OCI source/version/license labels. The image build produces the frontend once and copies only production assets into the runtime stage.

### 10.3 Apple Container

Apple Container 1.0.0 is the local macOS runtime. Because the Linux Essentia wheel is x86-64-only, local builds and runs use `--arch amd64` and Rosetta. Documentation provides direct `container build` and `container run` commands with:

- `/music` mounted read/write for approved tag changes and playlists;
- a separate persistent host directory mounted at `/data`;
- port `8000` published to the local network or loopback as chosen by the operator.

Apple Container does not provide NVIDIA CUDA. It validates the complete CPU product and can build the CUDA image, while actual CUDA inference validation requires an NVIDIA Linux host with NVIDIA Container Toolkit.

### 10.4 Windows development and runtime

Windows 11 is a supported development and deployment host. The recommended setup is Docker Desktop with its WSL2 backend and a repository clone inside the WSL2 Linux filesystem for predictable permissions, filesystem event delivery, and bind-mount performance. The project also supports running frontend and backend development commands from PowerShell when their native prerequisites are installed.

The repository avoids platform-specific assumptions:

- Python code uses `pathlib` and never parses paths by splitting on `/` or `\\`.
- API identifiers remain mount-relative POSIX paths; host paths are resolved only by deployment configuration.
- Core development, test, migration, and asset-build commands are exposed through cross-platform Python/npm entry points rather than Bash-only wrappers.
- Documentation provides PowerShell, WSL2, Apple Container, and POSIX shell examples where command syntax differs.
- `.gitattributes` defines stable LF endings for source, shell, Docker, JSON, YAML, and `.nsp` files while allowing Windows launch helpers to use CRLF when required.
- File watching uses polling as a documented fallback for Windows bind mounts.

The CPU image runs unchanged as a `linux/amd64` container in Docker Desktop. CUDA development on Windows requires the Docker Desktop WSL2 backend, current WSL2 components, a compatible NVIDIA GPU, and current NVIDIA Windows drivers with WSL2 GPU support. Compose exposes the GPU only in the CUDA profile; the default profile remains CPU-only.

## 11. CI and release automation

### 11.1 Pull-request and main-branch checks

- Python formatting/static checks and unit/API tests.
- Frontend lint, typecheck, component tests, and production build.
- Browser end-to-end tests against a lightweight test configuration.
- A Windows runner validates checkout line endings, Python path behavior, frontend tests, and non-container development commands.
- CPU image build and health smoke test.
- CUDA image build and non-GPU startup/capability test.
- Playlist catalog parity tests against the imported upstream definitions.

Actions are granted minimal permissions and pinned to immutable commit SHAs. Dependency caches must not contain secrets.

### 11.2 Release flow

Conventional Commits on `main` feed Release Please. Release Please maintains one release PR containing the version and changelog. Merging that PR creates the SemVer tag and GitHub Release. In the same workflow, the `release_created` output gates the CPU and CUDA image build/push jobs so no secondary workflow trigger is required.

The workflow publishes private packages to `ghcr.io/skrockle/essentia-studio` using `GITHUB_TOKEN` with `packages: write`. Tags are:

- CPU: `latest`, `latest-cpu`, `vX.Y.Z`, `vX.Y.Z-cpu`
- CUDA: `latest-cuda`, `vX.Y.Z-cuda`

The package is linked to the private repository and inherits its access policy. A generated software bill of materials and provenance attestation accompany each released image where GitHub permissions support them.

## 12. Security model

The first release assumes a trusted LAN and deliberately has no authentication. Documentation warns not to expose it directly to the internet. The server binds to `0.0.0.0` in the container so LAN access works through an explicitly published host port.

Filesystem operations use canonical path checks and reject traversal, absolute client paths, and symlink escapes. Playlist names are restricted to safe `.nsp` file names. Uploaded files and arbitrary shell commands do not exist. The API limits page sizes, tag counts, tag lengths, rule depth, and concurrent work. CORS is unnecessary because the frontend is same-origin.

## 13. Testing strategy

1. **Domain unit tests** – thresholds, label formatting, draft edits, fingerprints, state transitions, rule validation, preset transformation, and tag serialization.
2. **Format tests** – generated fixture files for FLAC, MP3, OGG/Opus, MP4/M4A, WMA, AIFF/WAV/DSF, and APEv2 families; verify write and undo behavior without model inference.
3. **Analysis adapter tests** – mocked model tests plus a small licensed/locally generated audio smoke fixture for real model loading in the CPU image.
4. **API tests** – settings, scans, jobs, conflicts, selective writes, undo, playlists, and error envelopes using temporary roots and SQLite databases.
5. **Frontend tests** – selection semantics, select-all over filtered rows, genre/mood chip editing, write preview, nested rule editing, capability display, and reconnect behavior.
6. **End-to-end tests** – scan → analyze → edit → select → write → undo, plus create → edit → delete playlist.
7. **Container tests** – health, static frontend, writable `/data`, mounted `/music`, non-root process, CPU inference, and CUDA capability reporting.
8. **Cross-platform tests** – Windows path and filename cases, PowerShell-documented commands, WSL2/Docker Desktop configuration parsing, and Linux/macOS command parity.

CUDA release acceptance requires one recorded real inference run on an NVIDIA Linux host or a Windows 11 Docker Desktop/WSL2 host with GPU support. Until that test is available, CI may prove that the CUDA image builds and starts but must not claim GPU inference is verified.

## 14. Acceptance criteria

The first release is complete only when all of the following are evidenced:

- The private standalone repository exists with `origin` and `upstream` configured as designed.
- A fresh CPU deployment opens the Workbench without login and scans a mounted library.
- A real track produces genre and mood previews without modifying the file.
- Users can add/remove both genres and moods, select some or all results, and write only those selections.
- Changed files are detected before writing; write errors remain isolated per track.
- A verified write can restore its prior managed tags through Undo.
- Every upstream playlist preset, rule field/operator, sort, and “This is …” mode is available through the web API and interface.
- `.nsp` files can be created, edited, and deleted safely in the mounted playlist directory.
- The CPU image runs through Apple Container on the user's Mac via amd64/Rosetta.
- A clean Windows 11 development setup can run tests and the CPU product through Docker Desktop/WSL2 using the documented commands.
- Windows path, line-ending, and mount behavior passes on a GitHub-hosted Windows runner.
- The CUDA image performs real inference on an NVIDIA Linux or Windows 11 Docker Desktop/WSL2 host.
- Tests cover the critical workflows and pass in CI.
- Merging the Release Please PR produces a GitHub Release and all documented private GHCR tags.
- README and About view document startup, mounts, Apple Container, Windows development, Docker/Compose, CUDA, upgrades, upstream provenance, and licensing constraints.
