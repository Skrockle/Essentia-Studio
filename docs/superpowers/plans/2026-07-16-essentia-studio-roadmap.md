# Essentia Studio Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement the linked plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the complete approved Essentia Studio product through four independently reviewable implementation plans.

**Architecture:** Build a modular FastAPI/React/SQLite foundation first, then add the analysis and tag-writing workflow, the complete Navidrome smart-playlist module, and finally production containers and GitHub delivery. Every plan leaves the repository in a working, testable state and consumes only interfaces established by earlier plans.

**Tech Stack:** Python 3.10, FastAPI 0.136.3, Pydantic 2, SQLAlchemy 2, React 19.2.7, TypeScript, Vite 8.1.5, Vitest, Playwright, SQLite, Mutagen, Essentia TensorFlow, OCI containers, GitHub Actions, Release Please, GHCR.

## Global Constraints

- The product is a trusted-LAN application with no authentication in the first release.
- Media is accessed only beneath the container-visible `/music` root; application state defaults to `/data/essentia-studio.db`.
- The default compute and image variant is CPU; CUDA is an explicit NVIDIA-only image variant.
- Both production images target `linux/amd64`; Apple Container runs the CPU image with `--arch amd64` through Rosetta.
- Windows 11 development is supported through Docker Desktop/WSL2 and native PowerShell-compatible development commands.
- The complete upstream playlist catalog, including every preset and every “This is …” mode, must be retained without simplification.
- Analysis never writes tags. Only an explicit, selected write operation may mutate audio metadata.
- Managed tags are captured before writes, verified after writes, and restored only when undo fingerprint checks pass.
- Source provenance and the MIT, AGPL-3.0, and CC BY-NC-ND 4.0 licensing constraints remain visible.
- `AGENTS.md` is the single canonical collaboration contract; tool-specific AI files are thin pointers and may not duplicate project rules.
- Hand-written Python and TypeScript functions must remain straightforward and pass a cyclomatic-complexity limit of 10; every task includes a readability review after tests.

---

## Execution order

1. [Platform Foundation Plan](./2026-07-16-essentia-studio-foundation.md)
   - Repository hygiene, Python/Node projects, SQLite migrations, settings, app factory, API errors, capability preflight, frontend shell, and cross-platform developer commands.
2. [Analysis Workbench Plan](./2026-07-16-essentia-studio-analysis-workbench.md)
   - Safe scan, persisted jobs/SSE, Essentia model adapter, drafts, multi-selection, tag write verification, undo, and the complete Workbench UI.
3. [Smart Playlist Plan](./2026-07-16-essentia-studio-smart-playlists.md)
   - Exact upstream catalog extraction, typed rule validation, all presets and “This is …” modes, atomic `.nsp` persistence, API, and browser editors.
4. [Delivery and Release Plan](./2026-07-16-essentia-studio-delivery.md)
   - CPU/CUDA images, Apple Container, Windows/Linux deployment, CI, Release Please, private GHCR publication, private repository creation, documentation, and release verification.

## Design coverage matrix

| Approved design requirement | Implemented by |
|---|---|
| Private standalone repository, provenance, licenses | Delivery Tasks 5–6 |
| Modular FastAPI/React/SQLite foundation | Foundation Tasks 1–4 |
| Human-readable code and multi-agent files | Foundation Task 0 and complexity gates in every plan |
| Settings, preflight, CPU/CUDA capability | Foundation Tasks 2–4; Delivery Task 2 |
| Mounted-library scan and path confinement | Analysis Tasks 1–2 |
| Persisted jobs, cancellation, resume, SSE | Analysis Task 2 |
| Real Essentia genre/mood analysis | Analysis Task 3 |
| Draft preview, manual genre/mood edits, multi-select/select-all | Analysis Task 4 |
| Verified selective writes and tag-level undo | Analysis Tasks 5–6 |
| Complete preset/rule/“This is …” catalog | Smart Playlist Tasks 1–2 |
| Atomic `.nsp` create/edit/delete and conflict handling | Smart Playlist Tasks 3–5 |
| Approved studio UI, jobs, settings, About | Foundation Task 4; Analysis Tasks 4 and 6; Smart Playlist Task 5; Delivery Task 6 |
| Apple Container, Windows 11/WSL2, Linux Docker | Foundation Task 5; Delivery Tasks 1–4 |
| CI, Release Please, GitHub Release, private GHCR variants | Delivery Tasks 4–6 |
| Full unit/API/component/E2E/container/GPU evidence | Completion gates in all four plans |

## Cross-plan completion gate

After all four plans, run the requirement-by-requirement audit from the approved design document. A green unit-test subset or successful image build is not sufficient evidence for the full product. The release is complete only after the real CPU flow, real CUDA inference, full playlist parity, private repository, GitHub Release, and all GHCR tags have each been observed directly.
