# Contributing to Essentia Studio

Thank you for improving Essentia Studio. The project accepts human- and AI-assisted contributions under the same review and verification standards.

## Before you change code

1. Read [AGENTS.md](AGENTS.md), which is the canonical contributor contract.
2. Read the [approved product design](docs/superpowers/specs/2026-07-16-essentia-studio-design.md).
3. Find the current task in the [implementation roadmap](docs/superpowers/plans/2026-07-16-essentia-studio-roadmap.md) and its detailed plan.
4. Confirm that your change is inside that task. Propose a design or plan update before changing an approved interface or invariant.

## Development workflow

Use an isolated branch or worktree. For each task:

1. Add the focused test that describes the required behavior.
2. Run it and confirm that it fails for the expected reason.
3. Implement the smallest complete behavior that satisfies the design.
4. Run the focused test.
5. Review the changed code for clear names, direct control flow, single responsibilities, and complexity at or below 10.
6. Run `python scripts/verify.py` after the foundation creates it, plus any browser, container, playlist-parity, or GPU checks required by the detailed plan.
7. Commit with a Conventional Commit message such as `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, or `chore:`.

## Product safety

Treat a mounted music library as user data. Scans and analysis are read-only. Metadata changes require selection, preview, fingerprint checks, original-tag capture, and read-back verification. Tests use generated fixtures rather than personal media.

The first release is intended for a trusted local network and has no authentication. Do not weaken path confinement or describe the service as safe for direct internet exposure.

## Platforms

Support macOS with Apple Container, Windows 11 with PowerShell or Docker Desktop/WSL2, and Linux. Keep core commands cross-platform. If a command differs by host, update the corresponding deployment guide and its documentation tests.

## Pull requests

Keep commits and pull requests focused. Describe the behavior, verification evidence, platform impact, and any remaining limitation. Never claim CUDA support from an image build alone; attach evidence from a real NVIDIA inference run.
