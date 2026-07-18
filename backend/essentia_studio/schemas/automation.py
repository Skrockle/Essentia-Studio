from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AutomationStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    trigger_mode: Literal["disabled", "watcher", "schedule", "fallback_schedule"]
    watcher_health: Literal["disabled", "starting", "ready", "failed"]
    next_runs: list[datetime]
    last_run: datetime | None = None
    last_error: str | None = None
