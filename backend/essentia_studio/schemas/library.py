from datetime import datetime

from pydantic import BaseModel

from essentia_studio.domain.tracks import LibraryTrack
from essentia_studio.services.track_state import ProcessingState


class TrackResponse(BaseModel):
    id: int
    relative_path: str
    extension: str
    size: int
    mtime_ns: int
    last_seen: datetime
    present: bool
    artist: str
    title: str
    album: str | None
    duration_seconds: float | None
    metadata_source: str
    processing_state: ProcessingState

    @classmethod
    def from_record(
        cls,
        track: LibraryTrack,
        processing_state: ProcessingState = "new",
    ) -> "TrackResponse":
        return cls(
            id=track.id,
            relative_path=track.relative_path,
            extension=track.extension,
            size=track.fingerprint.size,
            mtime_ns=track.fingerprint.mtime_ns,
            last_seen=track.last_seen,
            present=track.present,
            artist=track.metadata.artist,
            title=track.metadata.title,
            album=track.metadata.album,
            duration_seconds=track.metadata.duration_seconds,
            metadata_source=track.metadata.source,
            processing_state=processing_state,
        )


class TrackPage(BaseModel):
    items: list[TrackResponse]
    total: int
    page: int
    page_size: int
