from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from essentia_studio.errors import AppError
from essentia_studio.services.schedule import CronSchedule


def test_schedule_rejects_impossible_date() -> None:
    with pytest.raises(AppError, match="gültig"):
        CronSchedule("0 0 31 2 *", "Europe/Berlin")


def test_schedule_requires_exactly_five_fields_and_valid_timezone() -> None:
    with pytest.raises(AppError, match="fünf"):
        CronSchedule("0 0 * * * *", "Europe/Berlin")
    with pytest.raises(AppError, match="Zeitzone"):
        CronSchedule("0 9 * * *", "Mars/Olympus")


def test_next_runs_are_timezone_aware_across_dst_change() -> None:
    schedule = CronSchedule("0 9 * * *", "Europe/Berlin")
    base = datetime(2026, 3, 27, 12, tzinfo=ZoneInfo("Europe/Berlin"))

    runs = schedule.next_runs(base, count=3)

    assert [run.hour for run in runs] == [9, 9, 9]
    assert all(run.tzinfo is not None for run in runs)
    assert runs[0].utcoffset() != runs[1].utcoffset()
