# Playlist Studio Design

## Goal

Extend the existing Navidrome Smart Playlist feature into a complete Playlist Studio that can discover, edit, generate, synchronize, version, and repair playlists while keeping Essentia Studio as the canonical source of truth.

## Existing foundation

Essentia Studio already provides:

- Navidrome `.nsp` generation with the full imported field, operator, sort, preset, and "This is" catalog.
- Persistent playlist definitions in SQLite.
- Atomic writes into `${MUSIC_DIR}/SmartPlaylists`.
- Genre and mood analysis with confidence values.
- Persistent jobs, history, scheduler, and filesystem watcher.
- FastAPI, SQLAlchemy, Pydantic, and the current web application shell.

The implementation must extend these systems instead of introducing a second playlist application.

## Product model

Playlist Studio supports these playlist kinds:

- `smart_nsp`: native Navidrome Smart Playlist rules.
- `static`: manually ordered tracks.
- `mood`: materialized selection based on Essentia mood and audio scores.
- `similarity`: materialized selection based on track embeddings or distance features.
- `hybrid`: manual pins combined with generated tracks.
- `discovery`: periodically rotated low-playcount or unfamiliar tracks.
- `artist_mix`: enhanced "This is" playlist.
- `imported`: playlist imported from M3U, M3U8, NSP, or Navidrome.
- `mirror`: synchronized copy of an external or Navidrome playlist.
- `system`: recently added, loved, highly rated, unplayed, and related system lists.

## Source of truth

Essentia Studio is authoritative for every managed playlist. It stores:

- canonical definition;
- ordered materialized membership;
- pins and exclusions;
- target Navidrome profile and user;
- export targets;
- latest source and destination fingerprints;
- synchronization mode;
- version history.

Unmanaged playlists discovered in Navidrome or on disk are never overwritten. A user must explicitly adopt them before Essentia Studio may manage them.

## Export strategy

Playlist Studio uses three output adapters:

1. **NSP writer** for rules Navidrome can evaluate natively.
2. **Navidrome Subsonic connector** for user-specific materialized playlists.
3. **M3U8 writer** as a portable export and recovery copy for concrete track lists.

Selection rules:

- Use NSP when every rule maps to a supported Navidrome field and operator.
- Use the Navidrome API when the result depends on Essentia scores, embeddings, diversity, rotation, pins, exclusions, or user-specific behavior.
- Materialized managed playlists may optionally write M3U8 backups.

## Data model

### PlaylistDefinition

- `id`
- `name`
- `slug`
- `kind`
- `description`
- `enabled`
- `ownership`: `managed`, `adopted`, or `external`
- `sync_mode`: `export_only`, `import_only`, `bidirectional`, `essentia_authoritative`, or `navidrome_authoritative`
- `selection_definition`: versioned JSON object
- `ordering_definition`: versioned JSON object
- `diversity_definition`: versioned JSON object
- `rotation_definition`: versioned JSON object
- `schedule_definition`: versioned JSON object
- `target_profile_id`
- `target_user`
- `created_at`
- `updated_at`

### PlaylistTrackOverride

- playlist ID
- stable local track ID
- override type: `pin`, `exclude`, or `manual`
- optional fixed position
- note
- timestamps

### PlaylistMaterialization

- playlist ID
- generation timestamp
- source library revision
- ordered track IDs
- score and reason per track
- rejected candidates and rejection reason summary
- deterministic seed
- definition hash
- content hash
- status

### PlaylistExport

- playlist ID
- adapter type
- destination identifier
- destination content fingerprint
- last successful sync timestamp
- last observed external fingerprint
- status and error detail

### PlaylistVersion

Immutable snapshot of definition, overrides, materialized membership, and export metadata. Every write or synchronization operation creates a recoverable version.

### NavidromeProfile

- name
- base URL
- username
- encrypted credential or token material
- TLS verification option
- timeout
- enabled state
- last connectivity result

Credentials must never be returned by the API after storage and must not appear in logs.

## Scanner

The general scanner inventories:

- `.nsp` files;
- `.m3u` and `.m3u8` files;
- Navidrome playlists visible to configured profiles;
- managed playlists stored in Essentia Studio.

For each source it records:

- source type and path or remote ID;
- name and owner;
- content fingerprint;
- resolved and unresolved tracks;
- duplicates;
- missing files;
- invalid rules or paths;
- whether the item is managed, adoptable, conflicting, or healthy.

The scanner is read-only. Repair, adoption, deletion, and overwrite are separate explicit actions with previews.

## Track identity and path resolution

Playlist membership uses the existing local library track identity as the stable internal key. Adapters resolve that identity to:

- a relative music-root path for M3U8;
- a Navidrome song ID for API synchronization;
- fields and values for native NSP output.

Resolution order for imported files:

1. exact normalized relative path;
2. exact canonical absolute path under the configured music root;
3. normalized metadata match using artist, album, disc, track number, and title;
4. unresolved item requiring user review.

Ambiguous metadata matches are never selected automatically.

## Mood and materialized selection engine

A materialized playlist definition supports:

- positive weighted features;
- negative weighted features;
- hard minimum and maximum constraints;
- confidence thresholds;
- genre and mood inclusion or exclusion;
- BPM, duration, year, format, rating, playcount, loved status, and recency filters where available;
- maximum tracks per artist and album;
- minimum artist gap;
- duplicate-version suppression;
- deterministic randomization;
- target size;
- replacement or rotation percentage.

Scores are normalized to `[0, 1]`. The engine records every selected track's score and reasons so the UI can explain the result.

A generated playlist is stable when the definition, library revision, external user data, and seed are unchanged.

## Diversity and deduplication

Before final ordering, candidate groups identify likely alternate versions using normalized artist/title plus duration tolerance and existing release metadata. The engine keeps the best candidate according to quality, confidence, user rating, and definition-specific preference.

Diversity is applied as a constraint-aware selection pass, not as a post-processing deletion step, so the target size is maintained whenever enough candidates exist.

## Rotation

Rotation modes:

- `replace`: fully regenerate.
- `merge`: preserve all current valid members and add candidates up to target size.
- `rotate`: replace a configured percentage while honoring pins.
- `append`: only add new candidates.

Exclusions persist across all future runs. Pins always remain unless the underlying track no longer exists.

## Navidrome connector

The connector uses Navidrome's supported Subsonic-compatible playlist endpoints and is profile-specific.

Capabilities:

- connection test;
- list playlists;
- fetch playlist content;
- create playlist;
- replace or incrementally update membership;
- delete only managed remote playlists after explicit confirmation;
- resolve local tracks to Navidrome IDs;
- read user-specific rating, starred/loved, playcount, and last-played data where exposed by the configured server.

The connector must use timeouts and bounded retries. Authentication failures disable synchronization for the current job but do not disable or delete the playlist definition.

## Synchronization and conflicts

Every sync compares three fingerprints:

- last successfully exported content;
- current Essentia materialization;
- current destination content.

Outcomes:

- destination unchanged, local changed: export safely;
- destination changed, local unchanged: import or flag according to sync mode;
- both changed: create conflict and do not overwrite;
- destination deleted: recreate only for Essentia-authoritative playlists after preview or configured policy;
- unknown external playlist: scanner-only until adopted.

Bidirectional mode never silently merges reordered playlists. The user receives a three-way membership and order diff.

## Editor

The existing smart-playlist interface becomes Playlist Studio with these areas:

- inventory and health scanner;
- playlist library;
- definition editor;
- track membership editor;
- preview and explanation;
- synchronization status;
- version history and restore.

The definition editor changes by playlist kind:

- NSP rule tree for `smart_nsp`;
- weighted score and constraint editor for mood/similarity/discovery;
- searchable ordered track editor for static playlists;
- generated rules plus pins and exclusions for hybrid playlists.

The preview shows selected tracks, score components, rejected reasons, diversity decisions, output adapter, and destination diff before any write.

## Jobs and automation

Reuse the existing persistent job system, scheduler, and library watcher.

Job types:

- playlist inventory scan;
- preview materialization;
- materialize and export;
- synchronize Navidrome profile;
- repair selected playlist;
- restore playlist version.

Automatic triggers:

- after successful analysis of new or changed tracks;
- configured schedule;
- manual run;
- optional Navidrome resynchronization schedule.

Repeated filesystem events are coalesced using the existing quiet-period mechanism. One playlist cannot have two mutating jobs running concurrently.

## File writes

NSP and M3U8 files are written atomically by writing a sibling temporary file, flushing it, and replacing the destination. Before replacement, the current managed file is captured in PlaylistVersion.

M3U8 files use UTF-8, `#EXTM3U`, and paths relative to the configured music root. Files outside the music root are rejected.

## Safety rules

- Scanner operations never modify files or Navidrome.
- External playlists are never modified before adoption.
- Every mutating action has a preview.
- Managed deletion is explicit and destination-specific.
- Failed exports leave the last valid destination untouched.
- Restore creates a new version instead of deleting history.
- Secrets are write-only and redacted.
- No automatic playlist operation modifies audio tags.

## API boundaries

Backend modules expose domain services independent of FastAPI:

- catalog and definition validation;
- scanner service;
- selection/materialization service;
- version service;
- synchronization coordinator;
- NSP, M3U8, and Navidrome adapters.

HTTP routes call these services and return typed Pydantic schemas. Adapter exceptions are translated into stable domain error codes.

## Testing

Required coverage:

- definition validation for every playlist kind;
- deterministic scoring and selection;
- diversity and deduplication;
- pins, exclusions, and rotation;
- M3U8 parsing and atomic writing;
- NSP compatibility with the existing catalog;
- scanner classification and path resolution;
- Navidrome connector requests using mocked HTTP;
- three-way conflict detection;
- version creation and restore;
- API authorization-independent behavior in the trusted local-network model;
- frontend creation, preview, scanner, conflict, and restore flows.

End-to-end tests use a temporary music tree, temporary SQLite database, mocked Navidrome server, and deterministic analysis fixtures.

## Acceptance criteria

- Existing NSP presets and custom rule editing continue to work unchanged.
- All supported playlist sources appear in one scanner inventory.
- Users can adopt an external playlist without modifying it during scanning.
- Users can create and preview mood, static, hybrid, discovery, artist mix, and similarity definitions.
- Generated playlists explain why each track was selected.
- Materialized playlists synchronize to the selected Navidrome user and optionally produce M3U8 backups.
- Native-compatible definitions continue to export as NSP.
- Pins, exclusions, diversity, deterministic generation, and rotation behave consistently.
- External modifications produce conflicts instead of silent overwrites.
- Every mutation is versioned and restorable.
- Existing jobs, watcher, scheduler, database, and UI patterns are reused.