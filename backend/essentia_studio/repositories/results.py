import json
from dataclasses import asdict
from uuid import uuid4

from sqlalchemy import Engine, text

from essentia_studio.domain.analysis import (
    AnalysisResult,
    Prediction,
    StoredAnalysis,
    TagDraft,
)
from essentia_studio.domain.tracks import LibraryTrack, TrackFingerprint


class ResultRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(
        self,
        track: LibraryTrack,
        result: AnalysisResult,
        genres: list[str],
        moods: list[str],
        job_id: str | None = None,
    ) -> StoredAnalysis:
        result_id = str(uuid4())
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO analysis_results (
                      id, track_id, job_id, raw_genres, raw_moods, model_ids,
                      analyzed_size, analyzed_mtime_ns
                    ) VALUES (
                      :id, :track_id, :job_id, :genres, :moods, :model_ids, :size, :mtime_ns
                    )
                    """
                ),
                {
                    "id": result_id,
                    "track_id": track.id,
                    "job_id": job_id,
                    "genres": json.dumps([asdict(value) for value in result.genres]),
                    "moods": json.dumps([asdict(value) for value in result.moods]),
                    "model_ids": json.dumps(result.model_ids),
                    "size": track.fingerprint.size,
                    "mtime_ns": track.fingerprint.mtime_ns,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO tag_drafts (result_id, genres, moods)
                    VALUES (:result_id, :genres, :moods)
                    """
                ),
                {
                    "result_id": result_id,
                    "genres": json.dumps(genres),
                    "moods": json.dumps(moods),
                },
            )
        return self.get(result_id)

    def get(self, result_id: str) -> StoredAnalysis:
        with self._engine.connect() as connection:
            row = connection.execute(
                self._select_result("ar.id = :value"),
                {"value": result_id},
            ).one()
        return self._from_row(row)

    def get_by_path(self, relative_path: str) -> StoredAnalysis:
        with self._engine.connect() as connection:
            row = connection.execute(
                self._select_result("lt.relative_path = :value", order_latest=True),
                {"value": relative_path},
            ).one()
        return self._from_row(row)

    @staticmethod
    def _select_result(condition: str, order_latest: bool = False):
        order = "ORDER BY ar.created_at DESC, ar.id DESC LIMIT 1" if order_latest else ""
        return text(
            f"""
            SELECT ar.id, ar.track_id, lt.relative_path, ar.raw_genres, ar.raw_moods,
                   ar.model_ids, ar.analyzed_size, ar.analyzed_mtime_ns,
                   td.genres, td.moods, td.selected, td.dirty
            FROM analysis_results ar
            JOIN library_tracks lt ON lt.id = ar.track_id
            JOIN tag_drafts td ON td.result_id = ar.id
            WHERE {condition} {order}
            """
        )

    @staticmethod
    def _from_row(row) -> StoredAnalysis:
        return StoredAnalysis(
            id=row.id,
            track_id=row.track_id,
            relative_path=row.relative_path,
            fingerprint=TrackFingerprint(row.analyzed_size, row.analyzed_mtime_ns),
            result=AnalysisResult(
                genres=[Prediction(**value) for value in json.loads(row.raw_genres)],
                moods=[Prediction(**value) for value in json.loads(row.raw_moods)],
                model_ids=json.loads(row.model_ids),
            ),
            draft=TagDraft(
                genres=json.loads(row.genres),
                moods=json.loads(row.moods),
                selected=bool(row.selected),
                dirty=bool(row.dirty),
            ),
        )
