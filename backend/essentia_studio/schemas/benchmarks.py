from datetime import datetime

from pydantic import BaseModel, ConfigDict

from essentia_studio.domain.benchmarks import BenchmarkRun, BenchmarkStatus, ComputeMode


class ComputeMeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    compute: ComputeMode
    initialization_seconds: float
    warmup_seconds: float
    measured_seconds: list[float]
    average_seconds: float
    seconds_per_audio_minute: float
    baseline_peak_bytes: int
    worker_peak_bytes: int
    model_ids: list[str]


class BenchmarkResponse(BaseModel):
    id: str
    status: BenchmarkStatus
    sample_track_id: int | None
    sample_relative_path: str | None
    sample_seconds: float
    snapshot: dict[str, object]
    snapshot_hash: str
    recommended_workers: int | None
    error: str | None
    created_at: datetime | None
    finished_at: datetime | None
    measurements: list[ComputeMeasurementResponse]
    current: bool

    @classmethod
    def from_record(cls, run: BenchmarkRun, current: bool) -> "BenchmarkResponse":
        return cls(
            id=run.id,
            status=run.status,
            sample_track_id=run.sample_track_id,
            sample_relative_path=run.sample_relative_path,
            sample_seconds=run.sample_seconds,
            snapshot=run.snapshot,
            snapshot_hash=run.snapshot_hash,
            recommended_workers=run.recommended_workers,
            error=run.error,
            created_at=run.created_at,
            finished_at=run.finished_at,
            measurements=[
                ComputeMeasurementResponse(
                    **asdict_measurement(measurement),
                    average_seconds=measurement.average_seconds,
                    seconds_per_audio_minute=measurement.average_seconds,
                )
                for measurement in run.measurements
            ],
            current=current,
        )


def asdict_measurement(measurement) -> dict[str, object]:
    return {
        "compute": measurement.compute,
        "initialization_seconds": measurement.initialization_seconds,
        "warmup_seconds": measurement.warmup_seconds,
        "measured_seconds": measurement.measured_seconds,
        "baseline_peak_bytes": measurement.baseline_peak_bytes,
        "worker_peak_bytes": measurement.worker_peak_bytes,
        "model_ids": measurement.model_ids,
    }
