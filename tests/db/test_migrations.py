from sqlalchemy import text

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations


def test_migrations_are_idempotent(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    apply_migrations(engine)

    with engine.connect() as connection:
        versions = connection.execute(
            text("SELECT version FROM schema_migrations ORDER BY version")
        ).scalars().all()

    assert versions == list(range(1, 12))
    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(job_items)"))
        }
    assert "error_code" in columns


def test_upgrade_deselects_legacy_verified_drafts_that_match_written_tags(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "legacy.db")
    apply_migrations(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO library_tracks (
                  id, relative_path, extension, size, mtime_ns, last_seen
                ) VALUES (1, 'testdateien/song.flac', '.flac', 10, 20, 'now')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO analysis_results (
                  id, track_id, raw_genres, raw_moods, model_ids,
                  analyzed_size, analyzed_mtime_ns
                ) VALUES ('result-1', 1, '[]', '[]', '[]', 10, 20)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO tag_drafts (result_id, genres, moods, selected)
                VALUES ('result-1', '["Ambient"]', '["Calm"]', 1)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO write_operations (
                  id, result_id, relative_path, status, requested_tags,
                  post_write_size, post_write_mtime_ns
                ) VALUES (
                  'write-1', 'result-1', 'testdateien/song.flac', 'verified',
                  '{"genres":["Ambient"],"moods":["Calm"]}', 10, 20
                )
                """
            )
        )
        connection.execute(text("DELETE FROM schema_migrations WHERE version = 10"))

    apply_migrations(engine)

    with engine.connect() as connection:
        selected = connection.execute(
            text("SELECT selected FROM tag_drafts WHERE result_id = 'result-1'")
        ).scalar_one()
    assert selected == 0
