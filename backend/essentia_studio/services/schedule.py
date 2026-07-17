from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import CroniterBadCronError, CroniterBadDateError, croniter

from essentia_studio.errors import AppError


@dataclass(frozen=True, slots=True)
class CronSchedule:
    expression: str
    timezone: str
    _zone: ZoneInfo = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.expression.split()) != 5:
            raise AppError(
                "invalid_schedule",
                "Der Zeitplan muss genau fünf Cron-Felder enthalten.",
                422,
            )
        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise AppError(
                "invalid_timezone",
                "Die angegebene Zeitzone ist nicht verfügbar.",
                422,
                {"timezone": self.timezone},
            ) from error
        if not croniter.is_valid(self.expression, strict=True):
            raise AppError(
                "invalid_schedule",
                "Der Cron-Zeitplan ist nicht gültig.",
                422,
                {"expression": self.expression},
            )
        object.__setattr__(self, "_zone", zone)

    def next_runs(self, base: datetime, count: int = 3) -> list[datetime]:
        if base.tzinfo is None:
            raise AppError(
                "invalid_schedule_base",
                "Die Ausgangszeit für den Zeitplan benötigt eine Zeitzone.",
                422,
            )
        localized_base = base.astimezone(self._zone)
        try:
            iterator = croniter(self.expression, localized_base)
            return [iterator.get_next(datetime) for _ in range(count)]
        except (CroniterBadCronError, CroniterBadDateError) as error:
            raise AppError(
                "invalid_schedule",
                "Der Cron-Zeitplan ist nicht gültig.",
                422,
                {"expression": self.expression},
            ) from error


def validate_schedule(expression: str, timezone: str) -> None:
    CronSchedule(expression, timezone)


def next_runs(
    expression: str,
    timezone: str,
    base: datetime,
    count: int = 3,
) -> list[datetime]:
    return CronSchedule(expression, timezone).next_runs(base, count)
