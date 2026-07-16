from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Engine, text

from essentia_studio.domain.tracks import (
    LibraryTrack,
    ScannedTrack,
    ScanSummary,
    TrackFingerprint,
)

UPSERT_TRACK = text(
    """
    INSERT INTO library_tracks (
      relative_path, extension, size, mtime_ns, last_seen, present
    ) VALUES (
      :relative_path, :extension, :size, :mtime_ns, :last_seen, 1
    )
    ON CONFLICT(relative_path) DO UPDATE SET
      extension = excluded.extension,
      size = excluded.size,
      mtime_ns = excluded.mtime_ns,
      last_seen = excluded.last_seen,
      present = 1,
      updated_at = CURRENT_TIMESTAMP
    """
)


class TrackRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def replace_scan(self, tracks: Iterable[ScannedTrack], seen_at: datetime) -> ScanSummary:
        scanned_tracks = list(tracks)
        seen_value = seen_at.isoformat()
        parameters = [self._parameters(track, seen_value) for track in scanned_tracks]

        with self._engine.begin() as connection:
            if parameters:
                connection.execute(UPSERT_TRACK, parameters)
            connection.execute(
                text("UPDATE library_tracks SET present = 0 WHERE last_seen != :last_seen"),
                {"last_seen": seen_value},
            )
            counts = connection.execute(
                text(
                    """
                    SELECT
                      SUM(CASE WHEN present = 1 THEN 1 ELSE 0 END) AS present_count,
                      SUM(CASE WHEN present = 0 THEN 1 ELSE 0 END) AS missing_count
                    FROM library_tracks
                    """
                )
            ).one()

        return ScanSummary(
            scanned=len(scanned_tracks),
            present=counts.present_count or 0,
            missing=counts.missing_count or 0,
        )

    def get_by_path(self, relative_path: str) -> LibraryTrack:
        with self._engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT id, relative_path, extension, size, mtime_ns, last_seen, present
                    FROM library_tracks
                    WHERE relative_path = :relative_path
                    """
                ),
                {"relative_path": relative_path},
            ).one()

        return self._track_from_row(row)

    def query(
        self,
        search: str | None = None,
        present: bool | None = True,
        extension: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[LibraryTrack], int]:
        conditions: list[str] = []
        parameters: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if search:
            conditions.append("LOWER(relative_path) LIKE :search")
            parameters["search"] = f"%{search.casefold()}%"
        if present is not None:
            conditions.append("present = :present")
            parameters["present"] = int(present)
        if extension:
            conditions.append("extension = :extension")
            parameters["extension"] = extension.casefold()

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._engine.connect() as connection:
            total = connection.execute(
                text(f"SELECT COUNT(*) FROM library_tracks {where_clause}"),
                parameters,
            ).scalar_one()
            rows = connection.execute(
                text(
                    f"""
                    SELECT id, relative_path, extension, size, mtime_ns, last_seen, present
                    FROM library_tracks {where_clause}
                    ORDER BY relative_path, id LIMIT :limit OFFSET :offset
                    """
                ),
                parameters,
            ).all()
        return [self._track_from_row(row) for row in rows], total

    def get_by_ids(self, track_ids: list[int]) -> list[LibraryTrack]:
        if not track_ids:
            return []
        placeholders = ", ".join(f":id_{index}" for index in range(len(track_ids)))
        parameters = {f"id_{index}": track_id for index, track_id in enumerate(track_ids)}
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""
                    SELECT id, relative_path, extension, size, mtime_ns, last_seen, present
                    FROM library_tracks
                    WHERE id IN ({placeholders}) AND present = 1
                    ORDER BY relative_path, id
                    """
                ),
                parameters,
            ).all()
        return [self._track_from_row(row) for row in rows]

    @staticmethod
    def _parameters(track: ScannedTrack, seen_value: str) -> dict[str, object]:
        return {
            "relative_path": track.relative_path,
            "extension": track.extension,
            "size": track.fingerprint.size,
            "mtime_ns": track.fingerprint.mtime_ns,
            "last_seen": seen_value,
        }

    @staticmethod
    def _track_from_row(row) -> LibraryTrack:
        return LibraryTrack(
            id=row.id,
            relative_path=row.relative_path,
            extension=row.extension,
            fingerprint=TrackFingerprint(size=row.size, mtime_ns=row.mtime_ns),
            last_seen=datetime.fromisoformat(row.last_seen),
            present=bool(row.present),
        )
