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

        return LibraryTrack(
            id=row.id,
            relative_path=row.relative_path,
            extension=row.extension,
            fingerprint=TrackFingerprint(size=row.size, mtime_ns=row.mtime_ns),
            last_seen=datetime.fromisoformat(row.last_seen),
            present=bool(row.present),
        )

    @staticmethod
    def _parameters(track: ScannedTrack, seen_value: str) -> dict[str, object]:
        return {
            "relative_path": track.relative_path,
            "extension": track.extension,
            "size": track.fingerprint.size,
            "mtime_ns": track.fingerprint.mtime_ns,
            "last_seen": seen_value,
        }
