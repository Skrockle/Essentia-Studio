# Essentia Studio Smart Playlists Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the complete WB2024 Navidrome Smart Playlist Generator as a typed web module that preserves every preset, field, operator, sort, “This is …” method, and file-management operation.

**Architecture:** The upstream CLI remains vendored for provenance and parity checks but is not executed by the web service. A deterministic import script extracts literal catalogs into a committed runtime JSON artifact; a pure validator and “This is …” builder own domain behavior; a fingerprint-aware persistence service atomically reads/writes `.nsp` files; FastAPI and React expose the module.

**Tech Stack:** Python standard library, Pydantic 2, FastAPI, SQLite audit records, React/TypeScript, Vitest, Playwright.

## Global Constraints

- Source is `WB2024/Navidrome-SmartPlaylist-Generator-nsp` pinned to commit `b706d70` for this implementation.
- The vendor license and source revision are committed beside the imported source.
- Runtime behavior includes all 100+ fields, field-specific operators, sort options, all 298 presets from pinned commit `b706d70`, every category, and exactly the 20 upstream “This is …” methods.
- Rule nesting depth is at most 12, total condition count at most 500, string values at most 500 characters, playlist limit from 1 to 100000.
- Only canonical `.nsp` names beneath the configured playlist directory are accepted.
- Saves use a sibling temporary file, flush, `fsync`, and `os.replace`; external changes cause a fingerprint conflict rather than overwrite.
- Deletion is explicit, fingerprint-guarded, and recorded in SQLite.
- Vendored/generated catalog size is exempt, but every hand-written validator, builder, storage, API, and UI function must pass the shared complexity limit of 10 and a readability review.

---

### Task 1: Vendor provenance and deterministic catalog extraction

**Files:**
- Create: `vendor/navidrome-smart-playlist-generator/navidrome_smart_playlist_creator.py`
- Create: `vendor/navidrome-smart-playlist-generator/LICENSE`
- Create: `vendor/navidrome-smart-playlist-generator/UPSTREAM.md`
- Create: `scripts/import_nsp_catalog.py`
- Create: `backend/essentia_studio/playlists/catalog.json`
- Create: `backend/essentia_studio/playlists/catalog.py`
- Create: `tests/playlists/test_catalog_parity.py`

**Interfaces:**
- Consumes: pinned upstream source.
- Produces: `PlaylistCatalog.load() -> PlaylistCatalog`; deterministic `catalog.json`; parity test proving no catalog entry was dropped.

- [ ] **Step 1: Copy the pinned source and license with provenance**

Verify the pinned checkout, then mechanically copy only the vendored upstream source and license. Use `apply_patch` for `UPSTREAM.md` and every authored file in this task.

```bash
git -C /tmp/navidrome-nsp-review rev-parse HEAD
mkdir -p vendor/navidrome-smart-playlist-generator
cp /tmp/navidrome-nsp-review/navidrome_smart_playlist_creator.py vendor/navidrome-smart-playlist-generator/navidrome_smart_playlist_creator.py
cp /tmp/navidrome-nsp-review/LICENSE vendor/navidrome-smart-playlist-generator/LICENSE
```

`UPSTREAM.md` records repository URL, commit `b706d70`, import date `2026-07-16`, MIT license, and that runtime code is derived through `scripts/import_nsp_catalog.py`.

- [ ] **Step 2: Write the failing parity test**

```python
# tests/playlists/test_catalog_parity.py
from essentia_studio.playlists.catalog import PlaylistCatalog


def test_catalog_contains_complete_upstream_inventory() -> None:
    catalog = PlaylistCatalog.load()
    assert len(catalog.fields) >= 100
    assert {item.type for item in catalog.fields} == {"string", "number", "boolean", "date", "playlist"}
    assert len(catalog.presets) == 298
    assert len(catalog.this_is_methods) == 20
    assert {method.id for method in catalog.this_is_methods} == {
        "random", "top_rated", "most_played", "recently_played", "recently_added",
        "loved", "deep_cuts", "greatest_hits", "chronological", "reverse_chrono",
        "longest", "shortest", "high_energy", "chill", "lossless_only", "unplayed",
        "rare_gems", "album_openers", "album_closers", "singles",
    }
```

- [ ] **Step 3: Run the parity test and verify missing catalog**

Run: `python -m pytest tests/playlists/test_catalog_parity.py -q`

Expected: FAIL importing `essentia_studio.playlists.catalog`.

- [ ] **Step 4: Implement an AST-based literal importer**

`import_nsp_catalog.py` parses the vendored source with `ast.parse`. It finds assignments to `self.fields`, `self.operators`, `self.sort_options`, and class-level `PRESETS`, then uses `ast.literal_eval` only. It flattens fields to objects `{key,label,type,category}`, preserves operator order, transforms tuple presets to `{label,slug,category,definition}`, and appends the exact 20 method metadata records from a literal tuple in the importer.

The output is stable:

```python
payload = {
    "source_commit": "b706d70",
    "fields": fields,
    "operators": operators,
    "sort_options": sort_options,
    "presets": presets,
    "this_is_methods": THIS_IS_METHODS,
}
output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
```

`catalog.py` uses frozen Pydantic models and `importlib.resources.files` to load the artifact. It rejects duplicate field keys, preset slugs, and method IDs at import time.

- [ ] **Step 5: Generate twice, compare, test, and commit**

Run:

```bash
python scripts/import_nsp_catalog.py
cp backend/essentia_studio/playlists/catalog.json /tmp/catalog-first.json
python scripts/import_nsp_catalog.py
cmp /tmp/catalog-first.json backend/essentia_studio/playlists/catalog.json
python -m pytest tests/playlists/test_catalog_parity.py -q
```

Expected: `cmp` exits 0; catalog counts and exact 20-method ID test PASS.

Commit:

```bash
git add vendor/navidrome-smart-playlist-generator scripts/import_nsp_catalog.py backend/essentia_studio/playlists tests/playlists/test_catalog_parity.py
git commit -m "feat: import complete Navidrome playlist catalog"
```

### Task 2: Recursive rule validation and all “This is …” builders

**Files:**
- Create: `backend/essentia_studio/playlists/models.py`
- Create: `backend/essentia_studio/playlists/validation.py`
- Create: `backend/essentia_studio/playlists/this_is.py`
- Create: `tests/playlists/test_validation.py`
- Create: `tests/playlists/test_this_is.py`

**Interfaces:**
- Consumes: `PlaylistCatalog`.
- Produces: `validate_playlist(definition: dict, catalog) -> PlaylistDefinition`; `build_this_is(artist, method, limit, name, comment) -> PlaylistDefinition`.

- [ ] **Step 1: Write recursive validation and representative builder tests**

```python
# tests/playlists/test_validation.py
import pytest

from essentia_studio.errors import AppError
from essentia_studio.playlists.validation import validate_playlist


def test_nested_all_any_rule_is_preserved(catalog) -> None:
    raw = {
        "name": "Great electronic tracks",
        "all": [
            {"contains": {"genre": "Electronic"}},
            {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
        ],
        "sort": "-rating,+artist",
        "limit": 100,
    }
    assert validate_playlist(raw, catalog).model_dump(exclude_none=True) == raw


def test_operator_must_match_field_type(catalog) -> None:
    with pytest.raises(AppError) as error:
        validate_playlist({"name": "Bad", "all": [{"before": {"rating": 3}}]}, catalog)
    assert error.value.code == "invalid_playlist_operator"
```

```python
# tests/playlists/test_this_is.py
from essentia_studio.playlists.this_is import build_this_is


def test_greatest_hits_matches_upstream_rule() -> None:
    playlist = build_this_is("Björk", "greatest_hits", 50)
    assert playlist.model_dump(exclude_none=True)["all"] == [
        {"is": {"albumartist": "Björk"}},
        {"any": [
            {"is": {"loved": True}},
            {"gt": {"rating": 3}},
            {"gt": {"playcount": 9}},
        ]},
    ]
```

- [ ] **Step 2: Run tests and verify missing validator**

Run: `python -m pytest tests/playlists/test_validation.py tests/playlists/test_this_is.py -q`

Expected: FAIL during import.

- [ ] **Step 3: Implement bounded recursive validation**

`PlaylistDefinition` has `name`, optional `comment`, optional `all`/`any` lists of JSON rule objects, optional `sort`, optional `order` (`asc|desc`), and optional bounded `limit`. `validate_playlist` walks raw dictionaries without using recursive Pydantic forward models:

```python
def validate_group(items: object, *, depth: int, counter: list[int], catalog: PlaylistCatalog) -> list[dict]:
    if depth > 12 or not isinstance(items, list) or not items:
        raise AppError("invalid_playlist_group", "Die Regelgruppe ist ungültig.", 422)
    validated = []
    for item in items:
        counter[0] += 1
        if counter[0] > 500 or not isinstance(item, dict) or len(item) != 1:
            raise AppError("invalid_playlist_rule", "Die Playlist enthält ungültige Regeln.", 422)
        operator, operand = next(iter(item.items()))
        if operator in {"all", "any"}:
            validated.append({operator: validate_group(operand, depth=depth + 1, counter=counter, catalog=catalog)})
            continue
        validated.append(validate_condition(operator, operand, catalog))
    return validated
```

`validate_condition` requires one known field, an operator allowed for its catalog type, and coerces values only as follows: booleans must already be bool; numbers must be int/float but not bool; ranges must contain exactly two ordered values; `inTheLast`/`notInTheLast` require positive integer days; strings are trimmed and bounded; playlist IDs are nonempty strings.

- [ ] **Step 4: Port every “This is …” method as explicit pure data**

Create one mapping from the exact 20 IDs to builder functions. Each returns the same base artist rule, additional conditions, default sort/order, default name, and default comment as upstream. Do not combine methods through heuristics. A parametrized test asserts all 20 full definitions against committed expected dictionaries, including multi-field sorts such as `+year,+discnumber,+track`.

```python
def build_this_is(artist: str, method: str, limit: int = 50, name: str | None = None, comment: str | None = None) -> PlaylistDefinition:
    clean_artist = artist.strip()
    if not clean_artist or method not in BUILDERS:
        raise AppError("invalid_this_is_request", "Künstler oder Methode ist ungültig.", 422)
    raw = BUILDERS[method](clean_artist)
    raw["limit"] = limit
    raw["name"] = name.strip() if name and name.strip() else f"This is {clean_artist}"
    raw["comment"] = comment.strip() if comment and comment.strip() else DEFAULT_COMMENTS[method].format(artist=clean_artist)
    return validate_playlist(raw, PlaylistCatalog.load())
```

- [ ] **Step 5: Verify every method and commit**

Run: `python -m pytest tests/playlists/test_validation.py tests/playlists/test_this_is.py -q`

Expected: invalid nesting/type/operator/range tests PASS; parametrized output test covers exactly 20 methods.

Commit:

```bash
git add backend/essentia_studio/playlists/models.py backend/essentia_studio/playlists/validation.py backend/essentia_studio/playlists/this_is.py tests/playlists
git commit -m "feat: validate and build smart playlists"
```

### Task 3: Fingerprint-aware atomic `.nsp` persistence and audit history

**Files:**
- Create: `backend/essentia_studio/playlists/storage.py`
- Create: `backend/essentia_studio/db/migrations/0005_playlists.sql`
- Create: `backend/essentia_studio/repositories/playlists.py`
- Create: `tests/playlists/test_storage.py`
- Create: `tests/repositories/test_playlists.py`

**Interfaces:**
- Consumes: validated playlist definitions and configured playlist root.
- Produces: `PlaylistStorage.list/read/create/update/delete`; `PlaylistFile` with SHA-256 fingerprint; SQLite `playlist_records` and audit rows.

- [ ] **Step 1: Write traversal, atomic update, and stale fingerprint tests**

```python
# tests/playlists/test_storage.py
import pytest

from essentia_studio.errors import AppError


def test_playlist_name_cannot_escape_root(storage) -> None:
    with pytest.raises(AppError) as error:
        storage.read("../secrets.nsp")
    assert error.value.code == "invalid_playlist_name"


def test_update_rejects_external_change(storage, valid_playlist) -> None:
    saved = storage.create("mix.nsp", valid_playlist)
    saved.path.write_text('{"name":"external"}\n', encoding="utf-8")
    with pytest.raises(AppError) as error:
        storage.update("mix.nsp", valid_playlist, expected_fingerprint=saved.fingerprint)
    assert error.value.code == "playlist_changed"
```

- [ ] **Step 2: Run and verify missing storage**

Run: `python -m pytest tests/playlists/test_storage.py -q`

Expected: FAIL importing `PlaylistStorage`.

- [ ] **Step 3: Implement safe names and atomic JSON writes**

Accept names matching `^[A-Za-z0-9][A-Za-z0-9._ -]{0,119}\.nsp$`, reject `.`/`..`, slashes, backslashes, control characters, and resolved paths outside the playlist root.

```python
def atomic_write_json(path: Path, payload: dict) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
```

Fingerprint is SHA-256 of exact bytes. Create refuses an existing name with 409. Update and delete require a matching expected fingerprint. List ignores symlinks and invalid JSON but returns a per-file parse error so one broken file does not hide valid files.

- [ ] **Step 4: Persist audit records after filesystem outcomes**

Migration `0005_playlists.sql` creates `playlist_records` and `playlist_operations`. Storage calls repository methods only after successful create/update/delete; failed attempts record an operation with error code but never update the last-known-good record fingerprint. Store relative file name, display name, source mode (`preset|this_is|custom|existing`), definition JSON, fingerprint, timestamp, and operation.

- [ ] **Step 5: Verify atomic behavior and commit**

Run: `python -m pytest tests/playlists/test_storage.py tests/repositories/test_playlists.py -q`

Expected: traversal, symlink, exact-byte fingerprint, temp cleanup, external-change, create/update/delete, and audit tests PASS.

Commit:

```bash
git add backend/essentia_studio/playlists/storage.py backend/essentia_studio/db/migrations/0005_playlists.sql backend/essentia_studio/repositories/playlists.py tests/playlists/test_storage.py tests/repositories/test_playlists.py
git commit -m "feat: persist smart playlists atomically"
```

### Task 4: Complete playlist API

**Files:**
- Create: `backend/essentia_studio/schemas/playlists.py`
- Create: `backend/essentia_studio/api/routes/playlists.py`
- Modify: `backend/essentia_studio/api/router.py`
- Create: `tests/api/test_playlists.py`

**Interfaces:**
- Consumes: catalog, validator, builders, storage.
- Produces: catalog/preset/this-is/custom/list/read/create/update/delete endpoints.

- [ ] **Step 1: Write the full endpoint contract test**

```python
# tests/api/test_playlists.py
def test_catalog_preset_and_file_lifecycle(client) -> None:
    catalog = client.get("/api/playlists/catalog").json()
    assert len(catalog["presets"]) == 298
    assert len(catalog["this_is_methods"]) == 20

    built = client.post("/api/playlists/from-preset/recently-played", json={
        "filename": "recent.nsp", "overrides": {"limit": 25}
    })
    assert built.status_code == 201
    fingerprint = built.json()["fingerprint"]

    updated = client.put("/api/playlists/recent.nsp", json={
        "expected_fingerprint": fingerprint,
        "definition": {"name": "Recent", "all": [{"inTheLast": {"lastplayed": 7}}]},
    })
    assert updated.status_code == 200
    deleted = client.request("DELETE", "/api/playlists/recent.nsp", json={
        "expected_fingerprint": updated.json()["fingerprint"]
    })
    assert deleted.status_code == 204
```

- [ ] **Step 2: Run and verify endpoint absence**

Run: `python -m pytest tests/api/test_playlists.py -q`

Expected: FAIL because playlist routes return 404.

- [ ] **Step 3: Implement typed request/response models and catalog endpoints**

Expose:

- `GET /api/playlists/catalog`
- `POST /api/playlists/from-preset/{slug}`
- `POST /api/playlists/this-is`
- `GET /api/playlists`
- `POST /api/playlists`
- `GET /api/playlists/{name}`
- `PUT /api/playlists/{name}`
- `DELETE /api/playlists/{name}`

Preset overrides may change `name`, `comment`, `limit`, `sort`, and `order`, then pass the complete result through `validate_playlist`. They cannot replace the preset rules through this endpoint. Custom and update requests accept a complete raw definition and validate it. “This is …” requests call only `build_this_is`.

- [ ] **Step 4: Normalize errors and concurrent modifications**

Return 404 `playlist_not_found`, 409 `playlist_exists`, 409 `playlist_changed`, and 422 rule errors through `AppError`. A broken `.nsp` appears in list results with `status="invalid"` and a parse message, while `GET` returns 422 `invalid_playlist_file`.

- [ ] **Step 5: Verify API and commit**

Run: `python -m pytest tests/api/test_playlists.py tests/playlists -q`

Expected: all catalog, builder, validation, lifecycle, stale-fingerprint, and error tests PASS.

Commit:

```bash
git add backend/essentia_studio/schemas/playlists.py backend/essentia_studio/api/routes/playlists.py backend/essentia_studio/api/router.py tests/api/test_playlists.py
git commit -m "feat: expose smart playlist api"
```

### Task 5: Presets, “This is …”, nested rule editor, and file manager UI

**Files:**
- Create: `frontend/src/features/playlists/PlaylistsView.tsx`
- Create: `frontend/src/features/playlists/PresetBrowser.tsx`
- Create: `frontend/src/features/playlists/ThisIsBuilder.tsx`
- Create: `frontend/src/features/playlists/RuleBuilder.tsx`
- Create: `frontend/src/features/playlists/RuleGroup.tsx`
- Create: `frontend/src/features/playlists/PlaylistPreview.tsx`
- Create: `frontend/src/features/playlists/PlaylistManager.tsx`
- Create: `frontend/src/features/playlists/rules.ts`
- Create: `frontend/src/features/playlists/PlaylistsView.test.tsx`
- Modify: `frontend/src/app/App.tsx`
- Create: `frontend/e2e/playlists.spec.ts`

**Interfaces:**
- Consumes: complete playlist API.
- Produces: all four approved entry paths and browser lifecycle management.

- [ ] **Step 1: Write failing nested-editor and lifecycle tests**

```tsx
// frontend/src/features/playlists/PlaylistsView.test.tsx
test('builds a nested any group with field-specific controls', async () => {
  render(<PlaylistsView />)
  await userEvent.click(await screen.findByRole('tab', { name: 'Eigene Regeln' }))
  await userEvent.click(screen.getByRole('button', { name: 'ODER-Gruppe hinzufügen' }))
  await userEvent.selectOptions(screen.getAllByLabelText('Feld')[0], 'rating')
  expect(screen.getAllByLabelText('Operator')[0]).toHaveTextContent('Ist größer als')
  expect(screen.getAllByLabelText('Wert')[0]).toHaveAttribute('type', 'number')
})
```

```typescript
// frontend/e2e/playlists.spec.ts
test('creates, edits, and deletes a playlist', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Playlists' }).click()
  await page.getByRole('tab', { name: 'This is …' }).click()
  await page.getByLabel('Album-Künstler').fill('Björk')
  await page.getByLabel('Methode').selectOption('greatest_hits')
  await page.getByRole('button', { name: 'Vorschau erzeugen' }).click()
  await expect(page.getByText('This is Björk')).toBeVisible()
  await page.getByLabel('Dateiname').fill('this-is-bjork.nsp')
  await page.getByRole('button', { name: 'Playlist speichern' }).click()
  await expect(page.getByText('this-is-bjork.nsp')).toBeVisible()
  await page.getByRole('button', { name: 'Playlist löschen' }).click()
  await page.getByRole('button', { name: 'Löschen bestätigen' }).click()
  await expect(page.getByText('this-is-bjork.nsp')).not.toBeVisible()
})
```

- [ ] **Step 2: Run tests and verify missing UI**

Run: `npm --prefix frontend test -- --run src/features/playlists`

Expected: FAIL importing `PlaylistsView`.

- [ ] **Step 3: Implement catalog-driven controls and immutable rule helpers**

`rules.ts` exports `addCondition`, `addGroup`, `updateCondition`, `removeNode`, and `moveNode` that return new rule trees and address nodes by arrays of indices. `RuleBuilder` never hardcodes the field list or operators: it filters catalog operators by the selected field type. String/number/boolean/date/range/playlist controls map to their typed JSON values. Group depth and condition count are shown before API validation limits are reached.

- [ ] **Step 4: Implement the four entry paths and conflict-aware manager**

PresetBrowser filters category/label and paginates the complete catalog. ThisIsBuilder exposes exactly 20 methods. RuleBuilder supports nested `all`/`any`, reorder, remove, sort segments, order, limit, name, and comment. PlaylistManager lists valid/invalid files, opens valid JSON into the custom editor, and sends the last-read fingerprint on update/delete. A 409 conflict reloads external content only after explicit confirmation; it never silently overwrites.

- [ ] **Step 5: Verify frontend, E2E, and parity then commit**

Run:

```bash
npm --prefix frontend test -- --run src/features/playlists
npm --prefix frontend run typecheck
npm --prefix frontend run e2e -- e2e/playlists.spec.ts
python -m pytest tests/playlists/test_catalog_parity.py -q
```

Expected: nested editing, every field type, all four entry paths, create/edit/delete E2E, and catalog parity PASS.

Commit:

```bash
git add frontend/src/features/playlists frontend/src/app/App.tsx frontend/e2e/playlists.spec.ts
git commit -m "feat: add complete smart playlist studio"
```

## Smart-playlist completion evidence

- Runtime catalog counts and IDs exactly match the pinned upstream source.
- Parametrized tests prove all 20 “This is …” definitions.
- Nested rule validation rejects type/operator/depth/count errors.
- Browser tests create nested custom rules and manage real `.nsp` files.
- External edits produce a 409 conflict and no overwritten file.
- Atomic-write tests prove temp cleanup and replacement behavior.
