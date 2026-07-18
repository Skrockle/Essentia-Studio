# Genre suggestion semantics

**Status:** Approved in conversation on 2026-07-17

## Problem

The analysis setting currently called `Anzahl Genres` limits raw Discogs model
predictions before hierarchical labels are split. It therefore does not limit the
genre chips visible to the user. When every prediction is below the configured
threshold, the backend also promotes the best prediction as a normal result. A
configured maximum of three can consequently produce two visible tags from one
below-threshold prediction, which makes both settings misleading.

## Considered approaches

1. Rename the setting while retaining the current model-level behavior. This is
   technically small but preserves the surprising output.
2. Always fill the configured count with the strongest predictions. This makes
   the count predictable but silently weakens the confidence threshold.
3. Apply the threshold strictly and limit the normalized, visible genre tags.
   Preserve the best rejected prediction only as explicitly uncertain context.

Approach 3 is selected because it gives both settings one stable user-facing
meaning without discarding potentially useful review information.

## Behavior

- `Maximale Genres` is an upper bound for the distinct genre tags placed in a
  new draft after hierarchical Discogs labels have been split and normalized.
- Only model predictions at or above `Genre-Schwelle` may populate the draft.
- The accepted predictions are processed by descending confidence. Their split
  tags are deduplicated in stable order and truncated to the configured maximum.
- The application never promises to fill the maximum. A title may receive fewer
  genres or none when the model is not sufficiently confident.
- If no prediction reaches the threshold, the draft remains empty. The strongest
  prediction is retained as an uncertain candidate and presented separately from
  editable draft tags with its confidence and an explicit `Unter der Schwelle`
  label. It is never written unless the user deliberately adds or accepts it.
- Manually edited drafts are authoritative. An uncertain candidate must not be
  inferred merely because a user removed all genre tags.
- Existing stored drafts are not rewritten automatically. Re-analysis applies
  the corrected selection rules without changing audio metadata.

## Interfaces and data flow

The Essentia adapter returns ranked genre candidates without promoting a rejected
candidate. The analysis service turns accepted candidates into the bounded draft
tag list and stores the strongest rejected candidate as analysis evidence. The
results API exposes uncertainty explicitly rather than making the frontend infer
it from an empty draft. The Workbench renders uncertain evidence separately and
keeps the normal genre editor unchanged.

The Settings view uses `Maximale Genres` and explains that the value is an upper
bound after splitting; the threshold may result in fewer suggestions.

## Verification

- Backend tests cover strict threshold behavior, hierarchical splitting,
  deduplication, visible-tag limiting, and the uncertain best candidate.
- API tests prove that uncertainty is explicit and cannot be confused with a
  manually emptied draft.
- Component tests cover the revised setting text and separate uncertain state.
- The Workbench Playwright flow analyzes a fixture and verifies that normal chips
  never exceed the configured maximum and that a rejected candidate is visibly
  marked instead of appearing as a draft genre.
