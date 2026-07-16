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

    def query(
        self,
        filters: dict[str, object],
        page: int,
        page_size: int,
    ) -> tuple[list[StoredAnalysis], int, int]:
        where_clause, parameters = self._where(filters)
        parameters |= {"limit": page_size, "offset": (page - 1) * page_size}
        with self._engine.connect() as connection:
            counts = connection.execute(
                text(
                    f"""
                    SELECT COUNT(*) AS total,
                           COALESCE(SUM(CASE WHEN td.selected = 1 THEN 1 ELSE 0 END), 0)
                             AS selected_count
                    FROM analysis_results ar
                    JOIN library_tracks lt ON lt.id = ar.track_id
                    JOIN tag_drafts td ON td.result_id = ar.id
                    {where_clause}
                    """
                ),
                parameters,
            ).one()
            rows = connection.execute(
                text(self._result_select() + f" {where_clause} ORDER BY lt.relative_path, ar.id "
                     "LIMIT :limit OFFSET :offset"),
                parameters,
            ).all()
        return [self._from_row(row) for row in rows], counts.total, counts.selected_count

    def replace_draft(
        self,
        result_id: str,
        genres: list[str] | None,
        moods: list[str] | None,
    ) -> StoredAnalysis:
        current = self.get(result_id)
        updated_genres = current.draft.genres if genres is None else genres
        updated_moods = current.draft.moods if moods is None else moods
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE tag_drafts SET genres = :genres, moods = :moods,
                                          dirty = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE result_id = :result_id
                    """
                ),
                {
                    "result_id": result_id,
                    "genres": json.dumps(updated_genres),
                    "moods": json.dumps(updated_moods),
                },
            )
        return self.get(result_id)

    def update_selection(self, selection: dict[str, object], selected: bool) -> int:
        result_ids = self._selected_result_ids(selection)
        if not result_ids:
            return 0
        placeholders, parameters = self._id_parameters(result_ids)
        parameters["selected"] = int(selected)
        with self._engine.begin() as connection:
            result = connection.execute(
                text(
                    f"UPDATE tag_drafts SET selected = :selected "
                    f"WHERE result_id IN ({placeholders})"
                ),
                parameters,
            )
        return result.rowcount

    def bulk_update(
        self,
        selection: dict[str, object],
        operation: str,
        value: str,
    ) -> int:
        result_ids = self._selected_result_ids(selection)
        if not result_ids:
            return 0
        placeholders, parameters = self._id_parameters(result_ids)
        with self._engine.begin() as connection:
            rows = connection.execute(
                text(
                    f"SELECT result_id, genres, moods FROM tag_drafts "
                    f"WHERE result_id IN ({placeholders})"
                ),
                parameters,
            ).all()
            updates = [self._bulk_parameters(row, operation, value) for row in rows]
            connection.execute(
                text(
                    """
                    UPDATE tag_drafts SET genres = :genres, moods = :moods,
                                          dirty = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE result_id = :result_id
                    """
                ),
                updates,
            )
        return len(updates)

    def _selected_result_ids(self, selection: dict[str, object]) -> list[str]:
        if selection["mode"] == "ids":
            return list(dict.fromkeys(selection["ids"]))

        filters = selection["query"]
        where_clause, parameters = self._where(filters)
        excluded_ids = selection.get("excluded_ids", [])
        exclusion = ""
        if excluded_ids:
            placeholders, excluded_parameters = self._id_parameters(excluded_ids, "excluded")
            exclusion = f" AND ar.id NOT IN ({placeholders})"
            parameters |= excluded_parameters
        with self._engine.connect() as connection:
            return list(
                connection.execute(
                    text(
                        f"""
                        SELECT ar.id FROM analysis_results ar
                        JOIN library_tracks lt ON lt.id = ar.track_id
                        JOIN tag_drafts td ON td.result_id = ar.id
                        {where_clause}{exclusion}
                        ORDER BY lt.relative_path, ar.id
                        """
                    ),
                    parameters,
                ).scalars()
            )

    @staticmethod
    def _bulk_parameters(row, operation: str, value: str) -> dict[str, str]:
        genres = json.loads(row.genres)
        moods = json.loads(row.moods)
        target = genres if operation.endswith("genre") else moods
        if operation.startswith("add"):
            if value.casefold() not in {entry.casefold() for entry in target}:
                target.append(value)
        else:
            target[:] = [entry for entry in target if entry.casefold() != value.casefold()]
        return {
            "result_id": row.result_id,
            "genres": json.dumps(genres),
            "moods": json.dumps(moods),
        }

    @staticmethod
    def _id_parameters(
        result_ids: list[str],
        prefix: str = "result",
    ) -> tuple[str, dict[str, object]]:
        parameters = {f"{prefix}_{index}": value for index, value in enumerate(result_ids)}
        placeholders = ", ".join(f":{name}" for name in parameters)
        return placeholders, parameters

    @staticmethod
    def _where(filters: dict[str, object]) -> tuple[str, dict[str, object]]:
        conditions: list[str] = []
        parameters: dict[str, object] = {}
        simple_columns = {"job_id": "ar.job_id", "status": "td.status", "selected": "td.selected"}
        for name, column in simple_columns.items():
            if filters.get(name) is not None:
                conditions.append(f"{column} = :{name}")
                parameters[name] = int(filters[name]) if name == "selected" else filters[name]
        if filters.get("search"):
            conditions.append("LOWER(lt.relative_path) LIKE :search")
            parameters["search"] = f"%{str(filters['search']).casefold()}%"
        for name in ("genre", "mood"):
            if filters.get(name):
                conditions.append(
                    f"EXISTS (SELECT 1 FROM json_each(td.{name}s) "
                    f"WHERE LOWER(value) = :{name})"
                )
                parameters[name] = str(filters[name]).casefold()
        return (f"WHERE {' AND '.join(conditions)}" if conditions else ""), parameters

    @staticmethod
    def _result_select() -> str:
        return """
            SELECT ar.id, ar.track_id, lt.relative_path, ar.raw_genres, ar.raw_moods,
                   ar.model_ids, ar.analyzed_size, ar.analyzed_mtime_ns,
                   td.genres, td.moods, td.selected, td.dirty
            FROM analysis_results ar
            JOIN library_tracks lt ON lt.id = ar.track_id
            JOIN tag_drafts td ON td.result_id = ar.id
        """

    @staticmethod
    def _select_result(condition: str, order_latest: bool = False):
        order = "ORDER BY ar.created_at DESC, ar.id DESC LIMIT 1" if order_latest else ""
        return text(
            ResultRepository._result_select() + f" WHERE {condition} {order}"
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
