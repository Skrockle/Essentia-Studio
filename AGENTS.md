# Essentia Studio Contributor Contract

## Start here

Read the approved [product design](docs/superpowers/specs/2026-07-16-essentia-studio-design.md) and the current [implementation roadmap](docs/superpowers/plans/2026-07-16-essentia-studio-roadmap.md) before editing. Work from the current repository state, preserve unrelated changes, and keep the active task checklist current.

The detailed implementation plans are:

- [Platform foundation](docs/superpowers/plans/2026-07-16-essentia-studio-foundation.md)
- [Analysis workbench](docs/superpowers/plans/2026-07-16-essentia-studio-analysis-workbench.md)
- [Smart playlists](docs/superpowers/plans/2026-07-16-essentia-studio-smart-playlists.md)
- [Delivery and release](docs/superpowers/plans/2026-07-16-essentia-studio-delivery.md)

Follow the active plan task by task. Start with a focused failing test, make the smallest complete change that satisfies the approved design, run focused verification, review readability, then run the broader gate required by the plan.

## Architecture

Essentia Studio is a modular FastAPI/React/SQLite monolith. The production container serves the compiled frontend and JSON API from one origin.

- `backend/essentia_studio/analysis` loads models and produces read-only analysis results.
- `backend/essentia_studio/tags` owns format-specific managed metadata.
- `backend/essentia_studio/playlists` validates and persists Navidrome `.nsp` files.
- `backend/essentia_studio/services` coordinates domain workflows.
- `backend/essentia_studio/repositories` is the only application SQL boundary.
- `backend/essentia_studio/api` maps typed HTTP contracts to services.
- `frontend/src/features` groups React code by user-facing workflow.

Depend on these public boundaries rather than another module's implementation details. See [docs/architecture.md](docs/architecture.md) for the dependency map and responsibilities.

## Safety invariants

- Resolve media and playlist paths canonically beneath their configured roots. Reject absolute client paths, traversal, and symlink escapes.
- Never write audio tags during scan or analysis.
- Require explicit selection and a write preview before changing metadata.
- Compare fingerprints immediately before writes and undo.
- Capture exact managed tags before mutation and verify them after write or restore.
- Serialize filesystem-mutating jobs. One item failure must not stop unrelated items.
- Write `.nsp` files through a sibling temporary file, `fsync`, and atomic replacement.
- Keep the first release on a trusted LAN without authentication, and never document it as internet-safe.
- Do not place secrets, private host paths, or real music files in commits, logs, tests, or fixtures.

## Readability

Prefer descriptive domain names and direct control flow. Keep one responsibility per module and one abstraction level per function. Cyclomatic complexity may not exceed 10 in hand-written Python or TypeScript.

Avoid generic names such as `data`, `item`, `manager`, or `helper` when a domain name is available. Do not add wrappers that only forward arguments. Extract a function when doing so gives a coherent operation a useful name; do not split code merely to reduce line count. Comments should explain a non-obvious constraint or decision, not restate syntax.

Before committing:

1. Remove dead branches and unnecessary indirection.
2. Replace vague names with domain terms.
3. Split mixed filesystem, persistence, inference, and HTTP responsibilities.
4. Confirm errors explain the user-visible problem in German and retain a stable machine code.
5. Run the focused tests and complexity/static checks.

Vendored upstream source and generated playlist catalogs are exempt from hand-written complexity and size guidance. Never edit generated catalog data by hand; change the importer and regenerate it.

## Platform support

Development must work on:

- macOS with Apple Container 1.0.0; Linux amd64 images run through Rosetta;
- Windows 11 from PowerShell or Docker Desktop/WSL2;
- Linux with Docker Engine; CUDA additionally requires NVIDIA Container Toolkit.

Use `pathlib` for filesystem code and `subprocess` argument lists without `shell=True`. Core development commands must not depend on Bash. Store API paths as mount-relative POSIX paths and resolve host-native paths only at deployment boundaries. Preserve the line-ending rules in `.gitattributes`.

## Verification

Run the narrow test named by the active plan before broader checks. Once the platform foundation exists, the source gate is:

```text
python scripts/verify.py
```

Changes to browser workflows also require the relevant Playwright specification. Changes to playlist catalogs require the parity test. Changes to images require the matching container smoke test. CUDA claims require a recorded real inference run on an NVIDIA host; a successful image build alone is insufficient.

Do not report success from intent, a narrow substitute test, or the absence of obvious errors. Match every completion claim to direct evidence for the requirement.

## Git and scope

Use Conventional Commits. Do not force-push, rewrite user changes, commit secrets, or perform unrelated cleanup. Reserve `origin` for the private `Skrockle/Essentia-Studio` repository.

Make small, reviewable commits at the boundaries specified by the implementation plans. Update the design before changing an approved product decision and update the active plan before changing its interfaces or task order.
