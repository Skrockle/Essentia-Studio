from importlib.resources import files

from sqlalchemy import Engine


def apply_migrations(engine: Engine) -> None:
    migration_dir = files("essentia_studio.db.migrations")
    scripts = sorted(item for item in migration_dir.iterdir() if item.name.endswith(".sql"))

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )
        applied_versions = set(
            connection.exec_driver_sql("SELECT version FROM schema_migrations").scalars()
        )

        for script in scripts:
            version = int(script.name.split("_", 1)[0])
            if version in applied_versions:
                continue

            statements = script.read_text(encoding="utf-8").split("-- migrate:split")
            for statement in statements:
                if statement.strip():
                    connection.exec_driver_sql(statement)

            connection.exec_driver_sql(
                "INSERT INTO schema_migrations(version) VALUES (?)",
                (version,),
            )
