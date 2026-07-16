from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ManagedTagSnapshot:
    format: str
    fields: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DesiredTags:
    genres: list[str]
    moods: list[str]
    genre_confidence: str | None = None
    mood_confidence: str | None = None


class TagAdapter(Protocol):
    def read(self, path: Path) -> ManagedTagSnapshot: ...

    def write(self, path: Path, desired: DesiredTags, overwrite: bool) -> None: ...

    def restore(self, path: Path, snapshot: ManagedTagSnapshot) -> None: ...
