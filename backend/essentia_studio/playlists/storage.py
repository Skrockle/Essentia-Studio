import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from essentia_studio.errors import AppError
from essentia_studio.playlists.models import PlaylistDefinition
from essentia_studio.repositories.playlists import PlaylistRepository

PLAYLIST_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,119}\.nsp$")


@dataclass(frozen=True, slots=True)
class PlaylistFile:
    name: str
    path: Path
    definition: dict | None
    fingerprint: str
    status: str = "valid"
    error: str | None = None


class PlaylistStorage:
    def __init__(
        self,
        root: Path,
        repository: PlaylistRepository | None = None,
    ) -> None:
        self._root = root
        self._repository = repository
        if self._root.parent.is_dir():
            self._root.mkdir(exist_ok=True)

    def list(self) -> list[PlaylistFile]:
        if not self._root.is_dir():
            return []
        files: list[PlaylistFile] = []
        for path in sorted(self._root.glob("*.nsp"), key=lambda item: item.name.casefold()):
            if path.is_symlink() or not path.is_file():
                continue
            raw = path.read_bytes()
            try:
                definition = json.loads(raw)
                if not isinstance(definition, dict):
                    raise ValueError("Die Datei enthält kein JSON-Objekt.")
                files.append(self._file(path, raw, definition))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                files.append(
                    PlaylistFile(
                        path.name,
                        path,
                        None,
                        self._fingerprint(raw),
                        "invalid",
                        str(error),
                    )
                )
        return files

    def read(self, name: str) -> PlaylistFile:
        path = self._path(name)
        if not path.is_file() or path.is_symlink():
            raise AppError("playlist_not_found", "Die Playlist wurde nicht gefunden.", 404)
        raw = path.read_bytes()
        try:
            definition = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AppError(
                "invalid_playlist_file",
                "Die Playlist-Datei enthält kein gültiges JSON.",
                422,
            ) from error
        if not isinstance(definition, dict):
            raise AppError(
                "invalid_playlist_file",
                "Die Playlist-Datei enthält kein JSON-Objekt.",
                422,
            )
        return self._file(path, raw, definition)

    def create(
        self,
        name: str,
        definition: PlaylistDefinition | dict,
        source_mode: str = "custom",
    ) -> PlaylistFile:
        path = self._path(name)
        payload = self._payload(definition)
        self._ensure_root()
        if path.exists():
            self._failure(name, "create", "playlist_exists")
            raise AppError("playlist_exists", "Die Playlist existiert bereits.", 409)
        self._atomic_write(path, payload)
        saved = self.read(name)
        self._success(saved, "create", source_mode)
        return saved

    def update(
        self,
        name: str,
        definition: PlaylistDefinition | dict,
        expected_fingerprint: str,
        source_mode: str = "custom",
    ) -> PlaylistFile:
        current = self.read(name)
        if current.fingerprint != expected_fingerprint:
            self._failure(name, "update", "playlist_changed")
            raise AppError(
                "playlist_changed",
                "Die Playlist wurde außerhalb von Essentia Studio verändert.",
                409,
            )
        self._atomic_write(current.path, self._payload(definition))
        saved = self.read(name)
        self._success(saved, "update", source_mode)
        return saved

    def delete(self, name: str, expected_fingerprint: str) -> None:
        current = self.read(name)
        if current.fingerprint != expected_fingerprint:
            self._failure(name, "delete", "playlist_changed")
            raise AppError(
                "playlist_changed",
                "Die Playlist wurde außerhalb von Essentia Studio verändert.",
                409,
            )
        current.path.unlink()
        if self._repository:
            self._repository.record_success(
                name,
                "delete",
                "existing",
                current.definition or {},
                None,
            )

    def _path(self, name: str) -> Path:
        if not PLAYLIST_NAME.fullmatch(name) or "/" in name or "\\" in name:
            raise AppError("invalid_playlist_name", "Der Playlist-Dateiname ist ungültig.", 422)
        path = self._root / name
        if path.parent.resolve() != self._root.resolve():
            raise AppError("invalid_playlist_name", "Der Playlist-Dateiname ist ungültig.", 422)
        return path

    def _ensure_root(self) -> None:
        if not self._root.parent.is_dir():
            raise AppError(
                "playlist_mount_missing",
                "Das Playlist-Verzeichnis ist nicht verfügbar.",
                409,
            )
        self._root.mkdir(exist_ok=True)

    @staticmethod
    def _atomic_write(path: Path, payload: dict) -> None:
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _payload(definition: PlaylistDefinition | dict) -> dict:
        if isinstance(definition, PlaylistDefinition):
            return definition.model_dump(exclude_none=True)
        return definition

    @staticmethod
    def _fingerprint(raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    def _file(self, path: Path, raw: bytes, definition: dict) -> PlaylistFile:
        return PlaylistFile(path.name, path, definition, self._fingerprint(raw))

    def _success(self, saved: PlaylistFile, operation: str, source_mode: str) -> None:
        if self._repository:
            self._repository.record_success(
                saved.name,
                operation,
                source_mode,
                saved.definition or {},
                saved.fingerprint,
            )

    def _failure(self, name: str, operation: str, error_code: str) -> None:
        if self._repository:
            self._repository.record_failure(name, operation, error_code)
