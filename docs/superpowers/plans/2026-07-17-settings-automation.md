# Settings and Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist human-readable settings in `/data/settings.yaml`, overlay every setting from ENV, and process new or changed tracks through a safe watcher-or-schedule automation pipeline.

**Architecture:** `SettingsService` is the single source of effective configuration and reports each value's source. `AutomationService` accepts watcher and cron triggers, debounces fingerprints, scans metadata, and submits only new/changed tracks to the existing job infrastructure; optional automatic writes reuse `TagOperationService` and its verification/undo path.

**Tech Stack:** Python 3.10, PyYAML 6, croniter 6, watchdog 6, FastAPI/Pydantic 2, React 19, Vitest.

## Global Constraints

- Precedence is ENV > `/data/settings.yaml` > defaults.
- ENV-controlled fields are read-only in the UI.
- Automatic writing is disabled by default and requires explicit opt-in.
- Watcher off opens schedule settings; watcher failure visibly falls back to schedule.
- Duplicate triggers for one fingerprint create at most one analysis job.
- File size and mtime must remain stable during the configured quiet period.
- Existing SQLite settings migrate once without losing values.
- Cron uses timezone-aware datetimes and strict five-field validation.

---

### Task 1: Define nested settings and environment mapping

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements/runtime.in`
- Modify: `requirements/analysis.in`
- Modify/generated: `requirements/runtime.lock`
- Modify/generated: `requirements/analysis.lock`
- Replace: `backend/essentia_studio/schemas/settings.py`
- Create: `backend/essentia_studio/services/settings.py`
- Create: `tests/services/test_settings_service.py`

**Interfaces:**
- Produces: `AppSettings` with `analysis`, `automation`, and `benchmark` sections.
- Produces: `EffectiveSettings(values: AppSettings, sources: dict[str, Literal["default", "file", "env"]])`.
- Produces: `SettingsService.load()`, `SettingsService.update(patch)`, and `SettingsService.migrate_legacy(legacy)`.

- [ ] **Step 1: Write failing defaults and ENV precedence tests**

```python
def test_env_overrides_yaml_and_reports_source(tmp_path: Path) -> None:
    path = tmp_path / "settings.yaml"
    path.write_text("analysis:\n  workers: 2\n", encoding="utf-8")
    service = SettingsService(path, {"ESSENTIA_ANALYSIS_WORKERS": "4"})
    effective = service.load()
    assert effective.values.analysis.workers == 4
    assert effective.sources["analysis.workers"] == "env"
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/services/test_settings_service.py -q`

- [ ] **Step 3: Add runtime dependencies with exact supported ranges**

```toml
"pyyaml>=6.0,<7",
"croniter>=6.0,<7",
"watchdog>=6.0,<7",
```

Regenerate both hashed lock files with the repository's existing lock command. Do not hand-edit hashes.

- [ ] **Step 4: Implement models and ENV parser**

```python
class AnalysisSettings(BaseModel):
    workers: int = Field(1, ge=1, le=64)
    max_audio_seconds: int = Field(300, ge=1, le=3600)
    compute: Literal["auto", "cpu", "cuda"] = "auto"

class AutomationSettings(BaseModel):
    enabled: bool = False
    watcher: bool = False
    schedule: str = "0 * * * *"
    timezone: str = "UTC"
    mode: Literal["analyze", "analyze_and_write"] = "analyze"
    quiet_seconds: int = Field(30, ge=5, le=3600)
```

Keep thresholds, genre count, confidence tags, and overwrite policy in `AnalysisSettings`. Parse booleans only from `true/false`, `1/0`, `yes/no`, and reject all other values with the exact ENV name.

- [ ] **Step 5: Implement safe YAML load and validation**

Use `yaml.safe_load`; treat an empty file as `{}`; require a mapping root; validate through Pydantic; return dotted source keys for every leaf.

- [ ] **Step 6: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/services/test_settings_service.py -q`

Commit: `feat: load settings from yaml and environment`

---

### Task 2: Atomic persistence and legacy migration

**Files:**
- Modify: `backend/essentia_studio/services/settings.py`
- Modify: `backend/essentia_studio/config.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `backend/essentia_studio/api/dependencies.py`
- Modify: `backend/essentia_studio/api/routes/settings.py`
- Modify: `tests/services/test_settings_service.py`
- Modify: `tests/api/test_settings.py`

**Interfaces:**
- Runtime config gains `settings_path`, defaulting to `${ESSENTIA_DATA_DIR}/settings.yaml`.
- API `GET /api/settings -> EffectiveSettingsResponse`.
- API `PUT /api/settings` accepts a nested partial update and rejects ENV-locked paths with code `setting_locked_by_environment`.

- [ ] **Step 1: Write failing atomic-write and locked-field tests**

```python
def test_update_writes_yaml_atomically_and_preserves_env_override(tmp_path, monkeypatch):
    service = SettingsService(tmp_path / "settings.yaml", {"ESSENTIA_ANALYSIS_WORKERS": "4"})
    with pytest.raises(AppError, match="Umgebungsvariable"):
        service.update({"analysis": {"workers": 2}})
    assert not list(tmp_path.glob("*.tmp"))
```

- [ ] **Step 2: Verify RED, then implement temp-file + `os.replace` persistence**

Write in the settings directory, flush and `os.fsync`, then atomically replace. Preserve file settings not included in a partial update.

- [ ] **Step 3: Add failing one-time migration test**

Start with no YAML and a legacy SQLite settings row; assert the YAML receives equivalent nested values. Start again with an existing YAML and assert legacy values do not overwrite it.

- [ ] **Step 4: Wire `SettingsService` into lifespan and API**

Replace runtime reads of `SettingsRepository.get()` with `settings_service.load().values`. Keep the repository only for one-time migration during this release. Store `app.state.settings_service` and add dependency access.

- [ ] **Step 5: Run focused and full tests, then commit**

Run: `.venv/bin/python -m pytest tests/services/test_settings_service.py tests/api/test_settings.py -q`

Commit: `feat: persist settings yaml atomically`

---

### Task 3: Cron schedule model and status

**Files:**
- Create: `backend/essentia_studio/services/schedule.py`
- Create: `backend/essentia_studio/schemas/automation.py`
- Create: `backend/essentia_studio/api/routes/automation.py`
- Modify: `backend/essentia_studio/api/router.py`
- Create: `tests/services/test_schedule.py`
- Create: `tests/api/test_automation.py`

**Interfaces:**
- Produces: `CronSchedule(expression: str, timezone: str)`.
- Produces: `validate_schedule(expression, timezone) -> None` and `next_runs(..., count=3) -> list[datetime]`.
- `GET /api/automation/status` returns enabled, trigger mode, watcher health, next runs, last run, and last error.

- [ ] **Step 1: Write failing strict-validation and DST-aware next-run tests**

```python
def test_schedule_rejects_impossible_and_returns_aware_runs() -> None:
    with pytest.raises(AppError):
        CronSchedule("0 0 31 2 *", "Europe/Berlin")
    runs = CronSchedule("0 9 * * *", "Europe/Berlin").next_runs(
        datetime(2026, 3, 28, 12, tzinfo=ZoneInfo("Europe/Berlin")), 3
    )
    assert all(run.tzinfo is not None for run in runs)
```

- [ ] **Step 2: Verify RED and implement with current croniter API**

Use `croniter.is_valid(expression, strict=True)` and `croniter(expression, aware_base).get_next(datetime)`. Require exactly five whitespace-separated fields and a valid `zoneinfo.ZoneInfo`.

- [ ] **Step 3: Add status API test and minimal in-memory status store**

The API must work while automation is disabled and must not start a job merely by reading status.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/services/test_schedule.py tests/api/test_automation.py -q`

Commit: `feat: validate automation schedules`

---

### Task 4: File watcher, quiet period, and fallback

**Files:**
- Create: `backend/essentia_studio/services/file_watcher.py`
- Create: `tests/services/test_file_watcher.py`

**Interfaces:**
- Produces: `FileWatcher(root, supported_extensions, quiet_seconds, on_stable_path)`.
- Methods: `start()`, `stop()`, `health() -> Literal["disabled", "starting", "ready", "failed"]`.
- Consumes watchdog `Observer`, recursive `schedule`, and `FileSystemEventHandler` create/modify/move callbacks.

- [ ] **Step 1: Write failing event coalescing test with a fake observer/clock**

```python
def test_watcher_emits_once_after_file_is_stable(fake_clock, tmp_path):
    emitted = []
    watcher = FileWatcher(tmp_path, {".flac"}, 30, emitted.append, clock=fake_clock)
    watcher.record(tmp_path / "song.flac", size=10, mtime_ns=1)
    fake_clock.advance(20)
    watcher.record(tmp_path / "song.flac", size=20, mtime_ns=2)
    fake_clock.advance(30)
    watcher.flush_stable()
    assert emitted == [tmp_path / "song.flac"]
```

- [ ] **Step 2: Verify RED, then implement the pure pending-file state machine**

Keep timing and fingerprint logic independent of watchdog so Windows/macOS/Linux tests do not need native events.

- [ ] **Step 3: Add watchdog adapter and failure test**

Map create, modify, and destination move paths. Ignore directories, symlinks, unsupported extensions, and the application's playlist directory. On observer initialization/start failure, set health `failed`, retain the reason, and invoke the schedule-fallback callback once.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/services/test_file_watcher.py -q`

Commit: `feat: watch stable audio files`

---

### Task 5: Automation pipeline and deduplication

**Files:**
- Create: `backend/essentia_studio/services/automation.py`
- Modify: `backend/essentia_studio/services/jobs.py`
- Modify: `backend/essentia_studio/services/tag_operations.py`
- Modify: `backend/essentia_studio/main.py`
- Modify: `backend/essentia_studio/api/routes/automation.py`
- Create: `tests/services/test_automation.py`

**Interfaces:**
- Produces: `AutomationService.start()`, `stop()`, `trigger(reason)`, `status()`.
- Consumes `TrackStateService`, `JobCoordinator`, `MetadataService`, and `TagOperationService`.
- Job configuration records `trigger: watcher|schedule` and `automation_mode`.

- [ ] **Step 1: Write failing selection/deduplication tests**

```python
def test_trigger_submits_only_new_and_changed_fingerprints(harness):
    harness.states = {1: "new", 2: "current", 3: "changed"}
    harness.service.trigger("schedule")
    assert harness.submitted_track_ids == [1, 3]
    harness.service.trigger("watcher")
    assert harness.submitted_track_ids == [1, 3]
```

- [ ] **Step 2: Verify RED and implement one synchronized in-flight fingerprint set**

Release a fingerprint only after its job reaches terminal state. A scan trigger first refreshes metadata, then takes one immutable settings snapshot and submits one analysis batch.

- [ ] **Step 3: Write failing auto-write opt-in tests**

Assert mode `analyze` never calls `TagOperationService`; mode `analyze_and_write` writes only successful current result IDs and records an automatic trigger marker. Fingerprint conflicts stay failed and do not retry in a tight loop.

- [ ] **Step 4: Implement lifecycle and cron thread**

One daemon scheduler thread waits until the next timezone-aware run or a settings-reload event. `stop()` signals and joins it. The lifespan starts automation after the coordinator and stops automation before the coordinator.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/services/test_automation.py tests/services/test_jobs.py -q`

Commit: `feat: automate new track analysis`

---

### Task 6: Settings and automation GUI

**Files:**
- Modify: `frontend/src/api/types.ts`
- Split/modify: `frontend/src/features/settings/SettingsView.tsx`
- Create: `frontend/src/features/settings/SettingField.tsx`
- Create: `frontend/src/features/settings/AutomationSettings.tsx`
- Create: `frontend/src/features/settings/ScheduleEditor.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Create: `frontend/src/features/settings/AutomationSettings.test.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes effective settings values/sources and `/api/automation/status`.
- Emits nested partial settings updates.

- [ ] **Step 1: Write failing locked-field and toggle tests**

```tsx
test('env settings are visible but locked', async () => {
  render(<SettingsView />)
  expect(await screen.findByLabelText('Worker')).toBeDisabled()
  expect(screen.getByText('Durch Umgebungsvariable festgelegt')).toBeVisible()
})

test('turning watcher off opens schedule settings', async () => {
  render(<AutomationSettings value={enabledWatcherSettings} />)
  await userEvent.click(screen.getByRole('checkbox', { name: 'Dateiüberwachung' }))
  expect(screen.getByRole('region', { name: 'Zeitplan' })).toBeVisible()
})
```

- [ ] **Step 2: Verify RED**

Run: `npm --prefix frontend test -- --run AutomationSettings.test.tsx App.test.tsx`

- [ ] **Step 3: Implement focused components**

`SettingField` renders source/lock state. `AutomationSettings` contains enable, watcher, mode, quiet period, status, and fallback warning. `ScheduleEditor` provides interval, daily time, weekdays, advanced cron, readable summary, and three next runs returned by the API.

- [ ] **Step 4: Add failing save/error tests and implement nested partial updates**

Ensure automatic write requires a separate confirmation checkbox within the settings form; saving watcher off includes a valid schedule.

- [ ] **Step 5: Run frontend verification and commit**

Run: `npm --prefix frontend run lint && npm --prefix frontend test -- --run && npm --prefix frontend run typecheck && npm --prefix frontend run build`

Commit: `feat: configure watcher and automation schedule`

---

### Task 7: Deployment configuration and cross-platform docs

**Files:**
- Modify: `README.md`
- Modify: `docker-compose.yml`
- Modify: `compose.cuda.yml`
- Modify: `docs/deployment/apple-container.md`
- Modify: `docs/deployment/linux-docker.md`
- Modify: `docs/deployment/windows.md`
- Modify: `tests/docs/test_commands.py`

- [ ] **Step 1: Add failing docs/config tests**

Assert `/data/settings.yaml` persistence is covered by the existing `/data` mount, ENV names are documented, Apple Container examples include `--memory 4G`, and schedule fallback is described for Desktop/Apple bind mounts.

- [ ] **Step 2: Update examples and environment reference**

Do not bake host-specific paths into images. Explain that native Linux is the preferred watcher platform and schedule mode is the portable fallback.

- [ ] **Step 3: Run complete source verification and commit**

Run: `.venv/bin/python scripts/verify.py`

Commit: `docs: document settings and automation`
