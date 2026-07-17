from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from zoneinfo import ZoneInfo

from essentia_studio.schemas.automation import AutomationStatus
from essentia_studio.services.schedule import CronSchedule
from essentia_studio.services.settings import SettingsService


class AutomationStatusStore:
    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings
        self._lock = Lock()
        self._watcher_health: str = "starting"
        self._watcher_failed = False
        self._last_run: datetime | None = None
        self._last_error: str | None = None

    def snapshot(self) -> AutomationStatus:
        automation = self._settings.load().values.automation
        with self._lock:
            last_run = self._last_run
            last_error = self._last_error
            watcher_health = self._watcher_health
            watcher_failed = self._watcher_failed

        if not automation.enabled:
            return AutomationStatus(
                enabled=False,
                trigger_mode="disabled",
                watcher_health="disabled",
                next_runs=[],
                last_run=last_run,
                last_error=last_error,
            )
        if automation.watcher and not watcher_failed:
            return AutomationStatus(
                enabled=True,
                trigger_mode="watcher",
                watcher_health=watcher_health,
                next_runs=[],
                last_run=last_run,
                last_error=last_error,
            )

        zone = ZoneInfo(automation.timezone)
        runs = CronSchedule(automation.schedule, automation.timezone).next_runs(
            datetime.now(timezone.utc).astimezone(zone),
            3,
        )
        return AutomationStatus(
            enabled=True,
            trigger_mode="fallback_schedule" if watcher_failed else "schedule",
            watcher_health="failed" if watcher_failed else "disabled",
            next_runs=runs,
            last_run=last_run,
            last_error=last_error,
        )
