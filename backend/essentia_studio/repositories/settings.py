from sqlalchemy import Engine, text

from essentia_studio.schemas.settings import AnalysisSettings


class SettingsRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self) -> AnalysisSettings:
        with self._engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT worker_count, max_audio_seconds, genre_threshold,
                           mood_threshold, genre_count, write_confidence_tags,
                           overwrite_existing, compute_preference
                    FROM app_settings
                    WHERE singleton_id = 1
                    """
                )
            ).one()

        return AnalysisSettings(
            workers=row.worker_count,
            max_audio_seconds=row.max_audio_seconds,
            genre_threshold=row.genre_threshold,
            mood_threshold=row.mood_threshold,
            genre_count=row.genre_count,
            write_confidence_tags=bool(row.write_confidence_tags),
            overwrite_existing=bool(row.overwrite_existing),
            compute=row.compute_preference,
        )

    def replace(self, value: AnalysisSettings) -> AnalysisSettings:
        parameters = value.model_dump()
        parameters["write_confidence_tags"] = int(value.write_confidence_tags)
        parameters["overwrite_existing"] = int(value.overwrite_existing)

        with self._engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE app_settings
                    SET worker_count = :workers,
                        max_audio_seconds = :max_audio_seconds,
                        genre_threshold = :genre_threshold,
                        mood_threshold = :mood_threshold,
                        genre_count = :genre_count,
                        write_confidence_tags = :write_confidence_tags,
                        overwrite_existing = :overwrite_existing,
                        compute_preference = :compute
                    WHERE singleton_id = 1
                    """
                ),
                parameters,
            )

        return self.get()
