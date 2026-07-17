from dataclasses import dataclass
from datetime import datetime
from typing import Literal

MetadataSource = Literal["embedded", "filename", "directory", "fallback"]


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


@dataclass(frozen=True, slots=True)
class LibraryTrack:
    id: int
    relative_path: str
    extension: str
    fingerprint: TrackFingerprint
    last_seen: datetime
    present: bool
    metadata: TrackMetadata


@dataclass(frozen=True, slots=True)
class ScanSummary:
    scanned: int
    present: int
    missing: int
