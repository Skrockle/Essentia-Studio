from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TrackFingerprint:
    size: int
    mtime_ns: int


@dataclass(frozen=True, slots=True)
class ScannedTrack:
    relative_path: str
    extension: str
    fingerprint: TrackFingerprint


@dataclass(frozen=True, slots=True)
class LibraryTrack:
    id: int
    relative_path: str
    extension: str
    fingerprint: TrackFingerprint
    last_seen: datetime
    present: bool


@dataclass(frozen=True, slots=True)
class ScanSummary:
    scanned: int
    present: int
    missing: int
