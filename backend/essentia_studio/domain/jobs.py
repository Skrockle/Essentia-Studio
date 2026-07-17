from dataclasses import dataclass
from enum import Enum
from typing import Any


class JobType(str, Enum):
    SCAN = "scan"
    ANALYSIS = "analysis"
    WRITE = "write"
    UNDO = "undo"
    PLAYLIST_WRITE = "playlist_write"
    BENCHMARK = "benchmark"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATUSES = {
    JobStatus.COMPLETED,
    JobStatus.COMPLETED_WITH_ERRORS,
    JobStatus.CANCELLED,
    JobStatus.FAILED,
}


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: str
    type: JobType
    status: JobStatus
    configuration: dict[str, Any]
    parent_job_id: str | None
    total_items: int
    completed_items: int
    failed_items: int
    cancel_requested: bool


@dataclass(frozen=True, slots=True)
class JobItem:
    id: int
    value: str
    position: int
    status: str


@dataclass(frozen=True, slots=True)
class JobEvent:
    sequence: int
    job_id: str
    kind: str
    payload: dict[str, Any]
