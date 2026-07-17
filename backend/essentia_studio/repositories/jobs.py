from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from sqlalchemy import Engine, text

from essentia_studio.domain.jobs import (
    JobEvent,
    JobItem,
    JobItemRecord,
    JobRecord,
    JobStatus,
    JobType,
)


class JobRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(
        self,
        job_type: JobType,
        item_values: Sequence[str],
        configuration: dict[str, Any],
        parent_job_id: str | None = None,
    ) -> JobRecord:
        job_id = str(uuid4())
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO jobs (
                      id, type, status, configuration, parent_job_id, total_items
                    ) VALUES (:id, :type, 'queued', :configuration, :parent_job_id, :total)
                    """
                ),
                {
                    "id": job_id,
                    "type": job_type.value,
                    "configuration": json.dumps(configuration),
                    "parent_job_id": parent_job_id,
                    "total": len(item_values),
                },
            )
            if item_values:
                connection.execute(
                    text(
                        """
                        INSERT INTO job_items (job_id, position, value)
                        VALUES (:job_id, :position, :value)
                        """
                    ),
                    [
                        {"job_id": job_id, "position": position, "value": value}
                        for position, value in enumerate(item_values)
                    ],
                )
            self._insert_event(connection, job_id, "queued", {"total_items": len(item_values)})
        return self.get(job_id)

    def get(self, job_id: str) -> JobRecord:
        with self._engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT id, type, status, configuration, parent_job_id, total_items,
                           completed_items, failed_items, cancel_requested
                    FROM jobs WHERE id = :job_id
                    """
                ),
                {"job_id": job_id},
            ).one()
        return self._job_from_row(row)

    def list(self, limit: int = 100) -> list[JobRecord]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT id, type, status, configuration, parent_job_id, total_items,
                           completed_items, failed_items, cancel_requested
                    FROM jobs ORDER BY created_at DESC, id DESC LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        return [self._job_from_row(row) for row in rows]

    def has_active(self) -> bool:
        with self._engine.connect() as connection:
            return bool(
                connection.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM jobs "
                        "WHERE status IN ('queued', 'running'))"
                    )
                ).scalar_one()
            )

    def start(self, job_id: str) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE jobs SET status = 'running', started_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": job_id},
            )
            self._insert_event(connection, job_id, "started", {})

    def pending_items(self, job_id: str) -> list[JobItem]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT id, value, position, status FROM job_items
                    WHERE job_id = :job_id AND status IN ('queued', 'failed')
                    ORDER BY position
                    """
                ),
                {"job_id": job_id},
            ).all()
        return [JobItem(row.id, row.value, row.position, row.status) for row in rows]

    def list_items(self, job_id: str) -> list[JobItemRecord]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT id, job_id, position, value, status, result, error, error_code
                    FROM job_items WHERE job_id = :job_id ORDER BY position
                    """
                ),
                {"job_id": job_id},
            ).all()
        return [
            JobItemRecord(
                id=row.id,
                job_id=row.job_id,
                position=row.position,
                value=row.value,
                status=row.status,
                result=json.loads(row.result) if row.result is not None else None,
                error=row.error,
                error_code=row.error_code,
            )
            for row in rows
        ]

    def complete_item(self, job_id: str, item_id: int, result: dict[str, Any]) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text("UPDATE job_items SET status = 'completed', result = :result WHERE id = :id"),
                {"id": item_id, "result": json.dumps(result)},
            )
            connection.execute(
                text("UPDATE jobs SET completed_items = completed_items + 1 WHERE id = :id"),
                {"id": job_id},
            )
            self._insert_event(connection, job_id, "progress", self._progress(connection, job_id))

    def fail_item(
        self,
        job_id: str,
        item_id: int,
        error: str,
        error_code: str | None = None,
    ) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE job_items SET status = 'failed', error = :error, "
                    "error_code = :error_code WHERE id = :id"
                ),
                {"id": item_id, "error": error, "error_code": error_code},
            )
            connection.execute(
                text(
                    """
                    UPDATE jobs SET completed_items = completed_items + 1,
                                    failed_items = failed_items + 1
                    WHERE id = :id
                    """
                ),
                {"id": job_id},
            )
            self._insert_event(connection, job_id, "progress", self._progress(connection, job_id))

    def finalize(self, job_id: str, status: JobStatus) -> JobRecord:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE jobs SET status = :status, finished_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": job_id, "status": status.value},
            )
            payload = self._progress(connection, job_id) | {"status": status.value}
            self._insert_event(connection, job_id, "terminal", payload)
        return self.get(job_id)

    def request_cancel(self, job_id: str) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text("UPDATE jobs SET cancel_requested = 1 WHERE id = :id"),
                {"id": job_id},
            )

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._engine.connect() as connection:
            value = connection.execute(
                text("SELECT cancel_requested FROM jobs WHERE id = :id"),
                {"id": job_id},
            ).scalar_one()
        return bool(value)

    def item_values(self, job_id: str, unfinished_only: bool = False) -> list[str]:
        condition = "AND status IN ('queued', 'failed')" if unfinished_only else ""
        with self._engine.connect() as connection:
            return list(
                connection.execute(
                    text(
                        f"""
                        SELECT value FROM job_items
                        WHERE job_id = :job_id {condition}
                        ORDER BY position
                        """
                    ),
                    {"job_id": job_id},
                ).scalars()
            )

    def events_after(self, job_id: str, sequence: int) -> list[JobEvent]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT sequence, job_id, kind, payload FROM events
                    WHERE job_id = :job_id AND sequence > :sequence
                    ORDER BY sequence
                    """
                ),
                {"job_id": job_id, "sequence": sequence},
            ).all()
        return [
            JobEvent(row.sequence, row.job_id, row.kind, json.loads(row.payload))
            for row in rows
        ]

    @staticmethod
    def _job_from_row(row) -> JobRecord:
        return JobRecord(
            id=row.id,
            type=JobType(row.type),
            status=JobStatus(row.status),
            configuration=json.loads(row.configuration),
            parent_job_id=row.parent_job_id,
            total_items=row.total_items,
            completed_items=row.completed_items,
            failed_items=row.failed_items,
            cancel_requested=bool(row.cancel_requested),
        )

    @staticmethod
    def _insert_event(connection, job_id: str, kind: str, payload: dict[str, Any]) -> None:
        connection.execute(
            text("INSERT INTO events (job_id, kind, payload) VALUES (:job_id, :kind, :payload)"),
            {"job_id": job_id, "kind": kind, "payload": json.dumps(payload)},
        )
        connection.execute(
            text(
                """
                DELETE FROM events WHERE job_id = :job_id AND sequence NOT IN (
                  SELECT sequence FROM events WHERE job_id = :job_id
                  ORDER BY sequence DESC LIMIT 10000
                )
                """
            ),
            {"job_id": job_id},
        )

    @staticmethod
    def _progress(connection, job_id: str) -> dict[str, int]:
        row = connection.execute(
            text(
                "SELECT total_items, completed_items, failed_items FROM jobs WHERE id = :id"
            ),
            {"id": job_id},
        ).one()
        return {
            "total_items": row.total_items,
            "completed_items": row.completed_items,
            "failed_items": row.failed_items,
        }
