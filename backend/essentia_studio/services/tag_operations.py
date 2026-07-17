from pathlib import Path

from essentia_studio.domain.tracks import TrackFingerprint
from essentia_studio.domain.writes import WriteOperation, WriteTrigger
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.writes import WriteRepository
from essentia_studio.services.path_safety import resolve_track_path
from essentia_studio.tags.protocol import DesiredTags, ManagedTagSnapshot
from essentia_studio.tags.registry import TagAdapterRegistry


class TagOperationService:
    def __init__(
        self,
        results: ResultRepository,
        writes: WriteRepository,
        registry: TagAdapterRegistry,
        music_root: Path,
        overwrite_existing: bool = False,
    ) -> None:
        self._results = results
        self._writes = writes
        self._registry = registry
        self._music_root = music_root
        self._overwrite_existing = overwrite_existing

    def write_one(self, result_id: str, trigger: WriteTrigger = "manual") -> WriteOperation:
        result = self._results.get(result_id)
        path = resolve_track_path(self._music_root, result.relative_path)
        if self._fingerprint(path) != result.fingerprint:
            return self._writes.record_without_write(
                result.id,
                result.relative_path,
                "conflict",
                "track_changed_since_analysis",
                "Die Datei wurde seit der Analyse verändert.",
                trigger,
            )

        adapter = self._registry.for_path(path)
        snapshot = adapter.read(path)
        operation = self._writes.start(result.id, result.relative_path, snapshot, trigger)
        desired = DesiredTags(result.draft.genres, result.draft.moods)
        try:
            adapter.write(path, desired, self._overwrite_existing)
            written = adapter.read(path)
            if not self._contains_desired(written, desired):
                return self._writes.finish(
                    operation.id,
                    "failed",
                    error_code="write_verification_failed",
                    error_message="Die geschriebenen Tags konnten nicht bestätigt werden.",
                )
            return self._writes.finish(operation.id, "verified", self._fingerprint(path))
        except Exception as error:
            return self._writes.finish(
                operation.id,
                "failed",
                error_code="tag_write_failed",
                error_message=str(error),
            )

    def write_many(
        self,
        result_ids: list[str],
        trigger: WriteTrigger = "manual",
    ) -> list[WriteOperation]:
        return [self.write_one(result_id, trigger) for result_id in result_ids]

    def undo(self, operation_id: str) -> WriteOperation:
        operation = self._writes.get(operation_id)
        if not operation.undo_available or operation.original_snapshot is None:
            return self._writes.finish(
                operation.id,
                "conflict",
                error_code="undo_not_available",
                error_message="Für diesen Schreibvorgang ist kein Undo verfügbar.",
            )
        path = resolve_track_path(self._music_root, operation.relative_path)
        if self._fingerprint(path) != operation.post_write_fingerprint:
            return self._writes.finish(
                operation.id,
                "conflict",
                error_code="track_changed_since_write",
                error_message="Die Datei wurde nach dem Schreiben verändert.",
            )
        adapter = self._registry.for_path(path)
        try:
            adapter.restore(path, operation.original_snapshot)
            restored = adapter.read(path)
            if restored != operation.original_snapshot:
                return self._writes.finish(
                    operation.id,
                    "failed",
                    error_code="undo_verification_failed",
                    error_message="Die Wiederherstellung konnte nicht bestätigt werden.",
                )
            return self._writes.finish(operation.id, "undone", self._fingerprint(path))
        except Exception as error:
            return self._writes.finish(
                operation.id,
                "failed",
                error_code="undo_failed",
                error_message=str(error),
            )

    @staticmethod
    def _fingerprint(path: Path) -> TrackFingerprint:
        stat = path.stat()
        return TrackFingerprint(stat.st_size, stat.st_mtime_ns)

    @staticmethod
    def _contains_desired(snapshot: ManagedTagSnapshot, desired: DesiredTags) -> bool:
        def includes(actual: list[str], expected: list[str]) -> bool:
            return {value.casefold() for value in expected}.issubset(
                {value.casefold() for value in actual}
            )

        return includes(snapshot.fields.get("genres", []), desired.genres) and includes(
            snapshot.fields.get("moods", []), desired.moods
        )
