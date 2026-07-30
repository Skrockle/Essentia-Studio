from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

MetadataSource = Literal["embedded", "filename", "directory", "fallback"]
ManagedTagReadStatus = Literal["unknown", "ok", "error"]


@dataclass(frozen=True, slots=True)
class TrackFingerprint:
    size: int
    mtime_ns: int


@dataclass(frozen=True, slots=True)
class TrackMetadata:
    artist: str
    title: str
    album: str | None
    duration_seconds: float | None
    source: MetadataSource


@dataclass(frozen=True, slots=True)
class ManagedTagInventory:
    genres: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    status: ManagedTagReadStatus = "unknown"
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class LibraryQuery:
    search: str | None = None
    present: bool | None = True
    extension: str | None = None
    missing_genre: bool = False
    missing_mood: bool = False


@dataclass(frozen=True, slots=True)
class ScannedTrack:
    relative_path: str
    extension: str
    fingerprint: TrackFingerprint
    metadata: TrackMetadata = TrackMetadata(
        artist="Unbekannter Interpret",
        title="Unbekannter Titel",
        album=None,
        duration_seconds=None,
        source="fallback",
    )
    managed_tags: ManagedTagInventory = field(default_factory=ManagedTagInventory)


@dataclass(frozen=True, slots=True)
class LibraryTrack:
    id: int
    relative_path: str
    extension: str
    fingerprint: TrackFingerprint
    last_seen: datetime
    present: bool
    metadata: TrackMetadata
    managed_tags: ManagedTagInventory = field(default_factory=ManagedTagInventory)


@dataclass(frozen=True, slots=True)
class ScanSummary:
    scanned: int
    present: int
    missing: int
