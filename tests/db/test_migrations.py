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

    assert versions == [1, 2, 3, 4, 5, 6, 7]
