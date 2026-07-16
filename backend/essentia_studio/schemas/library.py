from datetime import datetime

from pydantic import BaseModel

from essentia_studio.domain.tracks import LibraryTrack


class TrackResponse(BaseModel):
    id: int
    relative_path: str
    extension: str
    size: int
    mtime_ns: int
    last_seen: datetime
    present: bool

    @classmethod
    def from_record(cls, track: LibraryTrack) -> "TrackResponse":
        return cls(
            id=track.id,
            relative_path=track.relative_path,
            extension=track.extension,
            size=track.fingerprint.size,
            mtime_ns=track.fingerprint.mtime_ns,
            last_seen=track.last_seen,
            present=track.present,
        )


class TrackPage(BaseModel):
    items: list[TrackResponse]
    total: int
    page: int
    page_size: int
