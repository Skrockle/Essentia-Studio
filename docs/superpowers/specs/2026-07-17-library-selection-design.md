# Library Selection and Host Port 8080 Design

## Goal

Make a completed library scan visible and actionable before analysis. The web
interface must show every scanned track, allow explicit multi-selection, submit
only the selected track IDs for analysis, and report the number of discovered
tracks. Deployment examples use host port 8080 while the container continues to
listen on port 8000.

## Considered approaches

1. **Dedicated library selection above analysis results (chosen).** Keeps the
   pre-analysis selection separate from the existing result selection used for
   metadata writes. This avoids one checkbox having two destructive meanings.
2. **One merged track/result table.** Visually compact, but requires a composite
   backend model and two independent selection states in every row.
3. **Automatically analyze after scanning.** Simple interaction, but removes the
   user's ability to select tracks and may unexpectedly start a long CPU job.

## Interface and data flow

- The workbench loads all present tracks from `/api/library/tracks` in pages of
  200 and combines the pages client-side.
- A focused library table displays relative path, extension, and analysis
  selection. Selection is a client-side set of numeric track IDs.
- “Alle auswählen” targets all tracks matching the current workbench search.
- “Auswahl analysieren” is disabled until at least one library track is selected
  and posts `{ "track_ids": [...] }` to `/api/analysis/jobs`.
- When a scan terminates, the workbench reloads the library, displays
  “Scan abgeschlossen – N Titel gefunden”, clears IDs no longer present, and
  refreshes existing analysis results.
- When analysis terminates, only the result list is refreshed. Existing draft
  selection and tag-writing behavior remain unchanged.

## Deployment port

The application remains bound to container port 8000. Docker Compose and Apple
Container publish host port 8080, configurable in Compose through
`ESSENTIA_PORT`. Documentation and health-check examples use localhost:8080.
Orchard also probes port 8080 for `/v1/models`, so changing the port does not
promise to remove those harmless 404 entries.

## Error handling and tests

- Library-load failures appear as a workbench error without hiding existing
  analysis results.
- An empty analysis selection never produces a request.
- Frontend tests prove scanned tracks are visible, select-all is available, and
  analysis submits only selected numeric IDs.
- Documentation tests prove Compose defaults to host port 8080.
- Existing backend, frontend, lint, type-check, and production-build checks must
  remain green before replacing the local Apple Container image.
