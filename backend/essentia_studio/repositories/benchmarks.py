from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Engine, text

from essentia_studio.domain.benchmarks import (
    BenchmarkRun,
    ComputeMeasurement,
    canonical_snapshot,
    snapshot_hash,
)


class BenchmarkRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(
        self,
        *,
        snapshot: dict[str, object],
        sample_track_id: int | None,
        sample_relative_path: str | None,
        sample_seconds: float = 60,
    ) -> BenchmarkRun:
        run_id = str(uuid4())
        serialized = canonical_snapshot(snapshot)
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO benchmark_runs (
                      id, status, sample_track_id, sample_relative_path, sample_seconds,
                      snapshot_json, snapshot_hash
                    ) VALUES (
                      :id, 'running', :track_id, :relative_path, :seconds, :snapshot, :hash
                    )
                    """
                ),
                {
                    "id": run_id,
                    "track_id": sample_track_id,
                    "relative_path": sample_relative_path,
                    "seconds": sample_seconds,
                    "snapshot": serialized,
                    "hash": snapshot_hash(snapshot),
                },
            )
        return self.get(run_id)

    def record_measurement(
        self,
        run_id: str,
        measurement: ComputeMeasurement,
    ) -> BenchmarkRun:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO benchmark_measurements (
                      run_id, compute, initialization_seconds, warmup_seconds,
                      measured_seconds_json, baseline_peak_bytes, worker_peak_bytes,
                      model_ids_json
                    ) VALUES (
                      :run_id, :compute, :initialization, :warmup, :measured,
                      :baseline, :worker, :models
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "compute": measurement.compute,
                    "initialization": measurement.initialization_seconds,
                    "warmup": measurement.warmup_seconds,
                    "measured": json.dumps(measurement.measured_seconds),
                    "baseline": measurement.baseline_peak_bytes,
                    "worker": measurement.worker_peak_bytes,
                    "models": json.dumps(measurement.model_ids),
                },
            )
        return self.get(run_id)

    def finish(self, run_id: str, recommended_workers: int) -> BenchmarkRun:
        return self._finish(run_id, "completed", recommended_workers, None)

    def fail(self, run_id: str, error: str) -> BenchmarkRun:
        return self._finish(run_id, "failed", None, error)

    def cancel(self, run_id: str) -> BenchmarkRun:
        return self._finish(run_id, "cancelled", None, "Benchmark abgebrochen")

    def get(self, run_id: str) -> BenchmarkRun:
        with self._engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM benchmark_runs WHERE id = :id"),
                {"id": run_id},
            ).one()
            measurements = self._measurements(connection, run_id)
        return self._from_row(row, measurements)

    def list(self, limit: int = 50) -> list[BenchmarkRun]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT * FROM benchmark_runs "
                    "ORDER BY created_at DESC, rowid DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).all()
            return [self._from_row(row, self._measurements(connection, row.id)) for row in rows]

    def current_for(self, expected_snapshot_hash: str) -> BenchmarkRun | None:
        with self._engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT * FROM benchmark_runs
                    WHERE snapshot_hash = :hash AND status = 'completed'
                    ORDER BY created_at DESC, rowid DESC LIMIT 1
                    """
                ),
                {"hash": expected_snapshot_hash},
            ).one_or_none()
            if row is None:
                return None
            measurements = self._measurements(connection, row.id)
        return self._from_row(row, measurements)

    def _finish(
        self,
        run_id: str,
        status: str,
        recommended_workers: int | None,
        error: str | None,
    ) -> BenchmarkRun:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE benchmark_runs SET status = :status,
                      recommended_workers = :workers, error = :error,
                      finished_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "status": status,
                    "workers": recommended_workers,
                    "error": error,
                },
            )
        return self.get(run_id)

    @staticmethod
    def _measurements(connection, run_id: str) -> list[ComputeMeasurement]:
        rows = connection.execute(
            text(
                "SELECT * FROM benchmark_measurements "
                "WHERE run_id = :run_id ORDER BY id"
            ),
            {"run_id": run_id},
        ).all()
        return [
            ComputeMeasurement(
                compute=row.compute,
                initialization_seconds=row.initialization_seconds,
                warmup_seconds=row.warmup_seconds,
                measured_seconds=json.loads(row.measured_seconds_json),
                baseline_peak_bytes=row.baseline_peak_bytes,
                worker_peak_bytes=row.worker_peak_bytes,
                model_ids=json.loads(row.model_ids_json),
            )
            for row in rows
        ]

    @staticmethod
    def _from_row(row, measurements: list[ComputeMeasurement]) -> BenchmarkRun:
        return BenchmarkRun(
            id=row.id,
            status=row.status,
            sample_track_id=row.sample_track_id,
            sample_relative_path=row.sample_relative_path,
            sample_seconds=row.sample_seconds,
            snapshot=json.loads(row.snapshot_json),
            snapshot_hash=row.snapshot_hash,
            recommended_workers=row.recommended_workers,
            error=row.error,
            created_at=datetime.fromisoformat(row.created_at),
            finished_at=datetime.fromisoformat(row.finished_at) if row.finished_at else None,
            measurements=measurements,
        )
