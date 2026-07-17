import json
from typing import Literal

from sqlalchemy import Engine, text

ProcessingState = Literal["new", "current", "changed", "written", "failed"]


def derive_processing_state(
    *,
    analysis_exists: bool = False,
    analysis_matches: bool = False,
    verified_write_matches: bool = False,
    latest_attempt_failed: bool = False,
) -> ProcessingState:
    if latest_attempt_failed:
        return "failed"
    if verified_write_matches:
        return "written"
    if analysis_matches:
        return "current"
    if analysis_exists:
        return "changed"
    return "new"


class TrackStateService:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def states(self, track_ids: list[int]) -> dict[int, ProcessingState]:
        unique_ids = list(dict.fromkeys(track_ids))
        if not unique_ids:
            return {}
        parameters = {f"track_{index}": track_id for index, track_id in enumerate(unique_ids)}
        placeholders = ", ".join(f":{name}" for name in parameters)
        with self._engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""
                    WITH ranked_analysis AS (
                      SELECT ar.*,
                             ROW_NUMBER() OVER (
                               PARTITION BY ar.track_id
                               ORDER BY ar.created_at DESC, ar.id DESC
                             ) AS rank
                      FROM analysis_results ar
                    ),
                    ranked_attempt AS (
                      SELECT lt.id AS track_id, ji.job_id, ji.status,
                             ROW_NUMBER() OVER (
                               PARTITION BY lt.id ORDER BY ji.id DESC
                             ) AS rank
                      FROM library_tracks lt
                      JOIN job_items ji ON ji.value = lt.relative_path
                      JOIN jobs j ON j.id = ji.job_id AND j.type = 'analysis'
                    ),
                    ranked_write AS (
                      SELECT ar.track_id, wo.status, wo.post_write_size,
                             wo.post_write_mtime_ns, wo.requested_tags,
                             ROW_NUMBER() OVER (
                               PARTITION BY ar.track_id
                               ORDER BY wo.created_at DESC, wo.id DESC
                             ) AS rank
                      FROM write_operations wo
                      JOIN analysis_results ar ON ar.id = wo.result_id
                    )
                    SELECT lt.id, lt.size, lt.mtime_ns,
                           ar.id AS analysis_id, ar.job_id AS analysis_job_id,
                           ar.analyzed_size, ar.analyzed_mtime_ns,
                           attempt.job_id AS attempt_job_id,
                           attempt.status AS attempt_status,
                           write.status AS write_status,
                           write.post_write_size, write.post_write_mtime_ns,
                           write.requested_tags,
                           td.genres AS draft_genres, td.moods AS draft_moods
                    FROM library_tracks lt
                    LEFT JOIN ranked_analysis ar ON ar.track_id = lt.id AND ar.rank = 1
                    LEFT JOIN ranked_attempt attempt
                      ON attempt.track_id = lt.id AND attempt.rank = 1
                    LEFT JOIN ranked_write write ON write.track_id = lt.id AND write.rank = 1
                    LEFT JOIN tag_drafts td ON td.result_id = ar.id
                    WHERE lt.id IN ({placeholders})
                    """
                ),
                parameters,
            ).all()
        return {row.id: self._state_from_row(row) for row in rows}

    @staticmethod
    def _state_from_row(row) -> ProcessingState:
        analysis_exists = row.analysis_id is not None
        analysis_matches = analysis_exists and (
            row.analyzed_size == row.size and row.analyzed_mtime_ns == row.mtime_ns
        )
        write_file_matches = row.write_status == "verified" and (
            row.post_write_size == row.size and row.post_write_mtime_ns == row.mtime_ns
        )
        requested_tags_match = TrackStateService._requested_tags_match(row)
        verified_write_matches = write_file_matches and requested_tags_match
        latest_attempt_failed = row.attempt_status == "failed" and (
            not analysis_exists or row.attempt_job_id != row.analysis_job_id
        )
        return derive_processing_state(
            analysis_exists=analysis_exists,
            analysis_matches=analysis_matches or write_file_matches,
            verified_write_matches=verified_write_matches,
            latest_attempt_failed=latest_attempt_failed,
        )

    @staticmethod
    def _requested_tags_match(row) -> bool:
        if row.requested_tags is None:
            return False
        requested = json.loads(row.requested_tags)
        return requested.get("genres") == json.loads(row.draft_genres) and requested.get(
            "moods"
        ) == json.loads(row.draft_moods)
