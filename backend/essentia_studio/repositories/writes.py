import json
from uuid import uuid4

from sqlalchemy import Engine, text

from essentia_studio.domain.tracks import TrackFingerprint
from essentia_studio.domain.writes import WriteOperation, WriteStatus, WriteTrigger
from essentia_studio.tags.protocol import ManagedTagSnapshot


class WriteRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def start(
        self,
        result_id: str,
        relative_path: str,
        snapshot: ManagedTagSnapshot,
        trigger: WriteTrigger = "manual",
    ) -> WriteOperation:
        operation_id = str(uuid4())
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO write_operations (
                      id, result_id, relative_path, status, original_snapshot, trigger
                    ) VALUES (:id, :result_id, :relative_path, 'started', :snapshot, :trigger)
                    """
                ),
                {
                    "id": operation_id,
                    "result_id": result_id,
                    "relative_path": relative_path,
                    "snapshot": json.dumps(
                        {"format": snapshot.format, "fields": snapshot.fields}
                    ),
                    "trigger": trigger,
                },
            )
        return self.get(operation_id)

    def record_without_write(
        self,
        result_id: str,
        relative_path: str,
        status: WriteStatus,
        error_code: str,
        error_message: str,
        trigger: WriteTrigger = "manual",
    ) -> WriteOperation:
        operation_id = str(uuid4())
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO write_operations (
                      id, result_id, relative_path, status, error_code, error_message, trigger
                    ) VALUES (
                      :id, :result_id, :relative_path, :status, :code, :message, :trigger
                    )
                    """
                ),
                {
                    "id": operation_id,
                    "result_id": result_id,
                    "relative_path": relative_path,
                    "status": status,
                    "code": error_code,
                    "message": error_message,
                    "trigger": trigger,
                },
            )
        return self.get(operation_id)

    def finish(
        self,
        operation_id: str,
        status: WriteStatus,
        fingerprint: TrackFingerprint | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WriteOperation:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE write_operations SET
                      status = :status,
                      post_write_size = :size,
                      post_write_mtime_ns = :mtime_ns,
                      error_code = :error_code,
                      error_message = :error_message,
                      updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {
                    "id": operation_id,
                    "status": status,
                    "size": fingerprint.size if fingerprint else None,
                    "mtime_ns": fingerprint.mtime_ns if fingerprint else None,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
        return self.get(operation_id)

    def get(self, operation_id: str) -> WriteOperation:
        with self._engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM write_operations WHERE id = :id"),
                {"id": operation_id},
            ).one()
        return self._from_row(row)

    def list(self, limit: int = 100) -> list[WriteOperation]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT * FROM write_operations
                    ORDER BY created_at DESC, id DESC LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row) -> WriteOperation:
        snapshot_data = json.loads(row.original_snapshot) if row.original_snapshot else None
        snapshot = (
            ManagedTagSnapshot(snapshot_data["format"], snapshot_data["fields"])
            if snapshot_data
            else None
        )
        fingerprint = (
            TrackFingerprint(row.post_write_size, row.post_write_mtime_ns)
            if row.post_write_size is not None
            else None
        )
        return WriteOperation(
            id=row.id,
            result_id=row.result_id,
            relative_path=row.relative_path,
            status=row.status,
            original_snapshot=snapshot,
            post_write_fingerprint=fingerprint,
            error_code=row.error_code,
            error_message=row.error_message,
            trigger=row.trigger,
        )
