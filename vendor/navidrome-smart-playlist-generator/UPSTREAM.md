# Upstream provenance

- Repository: https://github.com/WB2024/Navidrome-SmartPlaylist-Generator-nsp
- Commit: `b706d70148011093acc69b1e1679029d48d1aea4`
- Imported: 2026-07-16
- License: MIT (see `LICENSE`)

The upstream CLI is retained for provenance and catalog parity. Essentia Studio does not execute
it at runtime. `scripts/import_nsp_catalog.py` extracts its literal fields, operators, sort options,
and presets into a deterministic JSON artifact.
