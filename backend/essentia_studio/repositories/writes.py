import json
from uuid import uuid4

from sqlalchemy import Engine, text

from essentia_studio.domain.tracks import TrackFingerprint
from essentia_studio.domain.writes import WriteOperation, WriteStatus, WriteTrigger
from essentia_studio.tags.protocol import DesiredTags, ManagedTagSnapshot


class WriteRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def start(
        self,
        result_id: str,
        relative_path: str,
        snapshot: ManagedTagSnapshot,
        requested_tags: DesiredTags,
        trigger: WriteTrigger = "manual",
    ) -> WriteOperation:
        operation_id = str(uuid4())
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO write_operations (
                      id, result_id, relative_path, status, original_snapshot,
                      requested_tags, trigger
                    ) VALUES (
                      :id, :result_id, :relative_path, 'started', :snapshot,
                      :requested_tags, :trigger
                    )
                    """
                ),
                {
                    "id": operation_id,
                    "result_id": result_id,
                    "relative_path": relative_path,
                    "snapshot": json.dumps(
                        {"format": snapshot.format, "fields": snapshot.fields}
                    ),
                    "requested_tags": json.dumps(
                        {"genres": requested_tags.genres, "moods": requested_tags.moods}
                    ),
                    "trigger": trigger,
                },
            )
        return self.get(operation_id)

    def finish_verified(
        self,
        operation_id: str,
        fingerprint: TrackFingerprint,
    ) -> WriteOperation:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE write_operations SET
                      status = 'verified',
                      post_write_size = :size,
                      post_write_mtime_ns = :mtime_ns,
                      error_code = NULL,
                      error_message = NULL,
                      updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {
                    "id": operation_id,
                    "size": fingerprint.size,
                    "mtime_ns": fingerprint.mtime_ns,
                },
            )
            connection.execute(
                text(
                    """
                    UPDATE tag_drafts
                    SET selected = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE result_id = (
                      SELECT result_id FROM write_operations WHERE id = :id
                    )
                    """
                ),
                {"id": operation_id},
            )
            connection.execute(
                text(
                    """
                    UPDATE library_tracks
                    SET size = :size, mtime_ns = :mtime_ns,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = (
                      SELECT analysis_results.track_id
                      FROM analysis_results
                      JOIN write_operations
                        ON write_operations.result_id = analysis_results.id
                      WHERE write_operations.id = :id
                    )
                    """
                ),
                {
                    "id": operation_id,
                    "size": fingerprint.size,
                    "mtime_ns": fingerprint.mtime_ns,
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
        requested_data = json.loads(row.requested_tags) if row.requested_tags else None
        requested_tags = (
            DesiredTags(requested_data["genres"], requested_data["moods"])
            if requested_data
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
            requested_tags=requested_tags,
            post_write_fingerprint=fingerprint,
            error_code=row.error_code,
            error_message=row.error_message,
            trigger=row.trigger,
        )
