import json

from sqlalchemy import Engine, text


class PlaylistRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record_success(
        self,
        filename: str,
        operation: str,
        source_mode: str,
        definition: dict,
        fingerprint: str | None,
    ) -> None:
        with self._engine.begin() as connection:
            if operation == "delete":
                connection.execute(
                    text("DELETE FROM playlist_records WHERE filename = :filename"),
                    {"filename": filename},
                )
            else:
                connection.execute(
                    text(
                        """
                        INSERT INTO playlist_records (
                          filename, display_name, source_mode, definition, fingerprint
                        ) VALUES (:filename, :display_name, :source_mode, :definition, :fingerprint)
                        ON CONFLICT(filename) DO UPDATE SET
                          display_name = excluded.display_name,
                          source_mode = excluded.source_mode,
                          definition = excluded.definition,
                          fingerprint = excluded.fingerprint,
                          updated_at = CURRENT_TIMESTAMP
                        """
                    ),
                    {
                        "filename": filename,
                        "display_name": definition.get("name", filename),
                        "source_mode": source_mode,
                        "definition": json.dumps(definition, ensure_ascii=False),
                        "fingerprint": fingerprint,
                    },
                )
            self._insert_operation(
                connection,
                filename,
                operation,
                True,
                fingerprint,
                None,
            )

    def record_failure(self, filename: str, operation: str, error_code: str) -> None:
        with self._engine.begin() as connection:
            self._insert_operation(
                connection,
                filename,
                operation,
                False,
                None,
                error_code,
            )

    @staticmethod
    def _insert_operation(
        connection,
        filename: str,
        operation: str,
        success: bool,
        fingerprint: str | None,
        error_code: str | None,
    ) -> None:
        connection.execute(
            text(
                """
                INSERT INTO playlist_operations (
                  filename, operation, success, fingerprint, error_code
                ) VALUES (:filename, :operation, :success, :fingerprint, :error_code)
                """
            ),
            {
                "filename": filename,
                "operation": operation,
                "success": int(success),
                "fingerprint": fingerprint,
                "error_code": error_code,
            },
        )
