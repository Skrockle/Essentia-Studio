from importlib.resources import files

import pytest
from sqlalchemy import text

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations


@pytest.fixture
def version_10_job_item(tmp_path):
    engine = create_sqlite_engine(tmp_path / "version-10.db")
    migration_dir = files("essentia_studio.db.migrations")
    scripts = sorted(
        script
        for script in migration_dir.iterdir()
        if script.name.endswith(".sql") and int(script.name.split("_", 1)[0]) <= 10
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY)"
        )
        for script in scripts:
            statements = script.read_text(encoding="utf-8").split("-- migrate:split")
            for statement in statements:
                if statement.strip():
                    connection.exec_driver_sql(statement)
            connection.exec_driver_sql(
                "INSERT INTO schema_migrations(version) VALUES (?)",
                (int(script.name.split("_", 1)[0]),),
            )
        connection.execute(
            text(
                "INSERT INTO jobs (id, type, status, configuration, total_items) "
                "VALUES ('job-1', 'analysis', 'queued', '{}', 1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO job_items (id, job_id, position, value) "
                "VALUES (42, 'job-1', 0, 'albums/existing.flac')"
            )
        )
    return engine


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


def test_migration_11_preserves_existing_job_item(version_10_job_item) -> None:
    apply_migrations(version_10_job_item)
    apply_migrations(version_10_job_item)

    with version_10_job_item.connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, job_id, value, status, error_code "
                "FROM job_items WHERE id = 42"
            )
        ).one()

    assert row.id == 42
    assert row.job_id == "job-1"
    assert row.value == "albums/existing.flac"
    assert row.status == "queued"
    assert row.error_code is None


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
