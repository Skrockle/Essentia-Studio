from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

BenchmarkStatus = Literal["running", "completed", "failed", "cancelled"]
ComputeMode = Literal["cpu", "cuda"]


@dataclass(frozen=True, slots=True)
class ComputeMeasurement:
    compute: ComputeMode
    initialization_seconds: float
    warmup_seconds: float
    measured_seconds: list[float]
    baseline_peak_bytes: int
    worker_peak_bytes: int
    model_ids: list[str]

    @property
    def average_seconds(self) -> float:
        return sum(self.measured_seconds) / len(self.measured_seconds)


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    id: str
    status: BenchmarkStatus
    sample_track_id: int | None
    sample_relative_path: str | None
    sample_seconds: float
    snapshot: dict[str, object]
    snapshot_hash: str
    recommended_workers: int | None = None
    error: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None
    measurements: list[ComputeMeasurement] = field(default_factory=list)


def canonical_snapshot(snapshot: dict[str, object]) -> str:
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def snapshot_hash(snapshot: dict[str, object]) -> str:
    return hashlib.sha256(canonical_snapshot(snapshot).encode("utf-8")).hexdigest()
