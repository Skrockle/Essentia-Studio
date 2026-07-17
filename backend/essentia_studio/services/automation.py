from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Literal
from zoneinfo import ZoneInfo

from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.jobs import JobRecord, JobStatus, JobType
from essentia_studio.domain.tracks import LibraryTrack
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.automation_status import AutomationStatusStore
from essentia_studio.services.file_watcher import FileWatcher
from essentia_studio.services.jobs import JobCoordinator
from essentia_studio.services.scanner import SUPPORTED_EXTENSIONS
from essentia_studio.services.schedule import CronSchedule
from essentia_studio.services.settings import SettingsService
from essentia_studio.services.tag_operations import TagOperationService
from essentia_studio.services.track_state import TrackStateService

logger = logging.getLogger(__name__)
TriggerReason = Literal["watcher", "schedule"]
FingerprintKey = tuple[str, int, int]


class AutomationService:
    def __init__(
        self,
        *,
        settings: SettingsService,
        tracks: TrackRepository,
        states: TrackStateService,
        coordinator: JobCoordinator,
        results: ResultRepository,
        tag_operations: TagOperationService,
        refresh_library: Callable[[], object],
        music_root: Path | None = None,
        playlist_dir: Path | None = None,
        status_store: AutomationStatusStore | None = None,
        watcher_factory: type[FileWatcher] = FileWatcher,
    ) -> None:
        self._settings = settings
        self._tracks = tracks
        self._states = states
        self._coordinator = coordinator
        self._results = results
        self._tag_operations = tag_operations
        self._refresh_library = refresh_library
        self._music_root = music_root
        self._playlist_dir = playlist_dir
        self._status_store = status_store
        self._watcher_factory = watcher_factory
        self._trigger_lock = Lock()
        self._inflight_lock = Lock()
        self._inflight: set[FingerprintKey] = set()
        self._job_fingerprints: dict[str, set[FingerprintKey]] = {}
        self._job_modes: dict[str, str] = {}
        self._early_terminal: dict[str, JobRecord] = {}
        self._lifecycle_lock = Lock()
        self._stop_event = Event()
        self._schedule_thread: Thread | None = None
        self._watcher: FileWatcher | None = None
        self._watcher_failed = False
        coordinator.add_terminal_listener(self._on_terminal)

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._schedule_thread is not None:
                return
            self._stop_event.clear()
            self._configure_watcher_locked()
            self._schedule_thread = Thread(
                target=self._schedule_loop,
                name="essentia-automation-scheduler",
                daemon=True,
            )
            self._schedule_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lifecycle_lock:
            watcher = self._watcher
            self._watcher = None
            thread = self._schedule_thread
            self._schedule_thread = None
        if watcher is not None:
            watcher.stop()
        if thread is not None:
            thread.join(timeout=5)

    def reconfigure(self) -> None:
        with self._lifecycle_lock:
            previous = self._watcher
            self._watcher = None
        if previous is not None:
            previous.stop()
        with self._lifecycle_lock:
            self._configure_watcher_locked()

    def trigger(self, reason: TriggerReason) -> JobRecord | None:
        if not self._trigger_lock.acquire(blocking=False):
            return None
        try:
            effective = self._settings.load().values
            if not effective.automation.enabled:
                return None
            self._refresh_library()
            tracks, _total = self._tracks.query(
                present=True,
                page=1,
                page_size=1_000_000,
            )
            states = self._states.states([track.id for track in tracks])
            eligible = [track for track in tracks if states.get(track.id) in {"new", "changed"}]
            selected, fingerprints = self._reserve(eligible)
            if not selected:
                if self._status_store is not None:
                    self._status_store.record_run()
                return None

            analysis = effective.analysis
            options = AnalysisOptions(
                genre_threshold=analysis.genre_threshold,
                mood_threshold=analysis.mood_threshold,
                genre_count=analysis.genre_count,
                max_audio_seconds=analysis.max_audio_seconds,
            )
            try:
                job = self._coordinator.submit(
                    JobType.ANALYSIS,
                    [track.relative_path for track in selected],
                    {
                        "analysis": asdict(options),
                        "trigger": reason,
                        "automation_mode": effective.automation.mode,
                    },
                )
            except BaseException:
                self._release(fingerprints)
                raise
            with self._inflight_lock:
                self._job_fingerprints[job.id] = fingerprints
                self._job_modes[job.id] = effective.automation.mode
                early_terminal = self._early_terminal.pop(job.id, None)
            if early_terminal is not None:
                self._on_terminal(early_terminal)
            if self._status_store is not None:
                self._status_store.record_run()
            return job
        except Exception as error:
            if self._status_store is not None:
                self._status_store.record_run(str(error))
            raise
        finally:
            self._trigger_lock.release()

    def _configure_watcher_locked(self) -> None:
        automation = self._settings.load().values.automation
        self._watcher_failed = False
        if self._status_store is not None:
            self._status_store.set_watcher_health("disabled")
        if not automation.enabled or not automation.watcher or self._music_root is None:
            return

        if self._status_store is not None:
            self._status_store.set_watcher_health("starting")
        excluded = {self._playlist_dir} if self._playlist_dir is not None else set()
        watcher = self._watcher_factory(
            self._music_root,
            SUPPORTED_EXTENSIONS,
            automation.quiet_seconds,
            lambda _path: self._trigger_safely("watcher"),
            excluded_roots=excluded,
            on_fallback=self._watcher_fallback,
        )
        self._watcher = watcher
        watcher.start()
        if watcher.health() == "ready" and self._status_store is not None:
            self._status_store.set_watcher_health("ready")

    def _watcher_fallback(self, reason: str) -> None:
        self._watcher_failed = True
        if self._status_store is not None:
            self._status_store.set_watcher_health("failed", reason)

    def _schedule_loop(self) -> None:
        schedule_key: tuple[str, str] | None = None
        due: datetime | None = None
        while not self._stop_event.wait(0.5):
            automation = self._settings.load().values.automation
            schedule_active = automation.enabled and (
                not automation.watcher or self._watcher_failed
            )
            if not schedule_active:
                schedule_key = None
                due = None
                continue

            key = (automation.schedule, automation.timezone)
            zone = ZoneInfo(automation.timezone)
            now = datetime.now(timezone.utc).astimezone(zone)
            schedule = CronSchedule(*key)
            if key != schedule_key or due is None:
                schedule_key = key
                due = schedule.next_runs(now, 1)[0]
                continue
            if now >= due:
                self._trigger_safely("schedule")
                due = schedule.next_runs(now, 1)[0]

    def _trigger_safely(self, reason: TriggerReason) -> None:
        try:
            self.trigger(reason)
        except Exception:
            logger.exception("Automation trigger %s failed", reason)

    def _reserve(
        self,
        tracks: list[LibraryTrack],
    ) -> tuple[list[LibraryTrack], set[FingerprintKey]]:
        selected: list[LibraryTrack] = []
        fingerprints: set[FingerprintKey] = set()
        with self._inflight_lock:
            for track in sorted(tracks, key=lambda item: item.relative_path):
                fingerprint = self._fingerprint(track)
                if fingerprint in self._inflight:
                    continue
                self._inflight.add(fingerprint)
                selected.append(track)
                fingerprints.add(fingerprint)
        return selected, fingerprints

    def _on_terminal(self, job: JobRecord) -> None:
        with self._inflight_lock:
            fingerprints = self._job_fingerprints.pop(job.id, None)
            mode = self._job_modes.pop(job.id, "analyze")
            if fingerprints is None and job.configuration.get("automation_mode") is not None:
                self._early_terminal[job.id] = job
        if fingerprints is None:
            return
        try:
            if mode != "analyze_and_write" or job.status not in {
                JobStatus.COMPLETED,
                JobStatus.COMPLETED_WITH_ERRORS,
            }:
                return
            results = self._results.for_job(job.id)
            states = self._states.states([result.track_id for result in results])
            current_ids = [
                result.id for result in results if states.get(result.track_id) == "current"
            ]
            if current_ids:
                self._tag_operations.write_many(current_ids, trigger="automation")
        except Exception:
            logger.exception("Automatic tag writing failed for job %s", job.id)
        finally:
            self._release(fingerprints)

    def _release(self, fingerprints: set[FingerprintKey]) -> None:
        with self._inflight_lock:
            self._inflight.difference_update(fingerprints)

    @staticmethod
    def _fingerprint(track: LibraryTrack) -> FingerprintKey:
        return (
            track.relative_path,
            track.fingerprint.size,
            track.fingerprint.mtime_ns,
        )
