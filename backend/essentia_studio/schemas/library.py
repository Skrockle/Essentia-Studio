from datetime import datetime

from pydantic import BaseModel, ConfigDict

from essentia_studio.domain.tracks import LibraryQuery, LibraryTrack
from essentia_studio.services.track_state import ProcessingState


class LibrarySelectionQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str | None = None
    present: bool | None = True
    extension: str | None = None
    missing_genre: bool = False
    missing_mood: bool = False

    def to_domain(self) -> LibraryQuery:
        return LibraryQuery(**self.model_dump())


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
    managed_genres: list[str]
    managed_moods: list[str]
    managed_tags_status: str
    managed_tags_error_code: str | None

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
            managed_genres=track.managed_tags.genres,
            managed_moods=track.managed_tags.moods,
            managed_tags_status=track.managed_tags.status,
            managed_tags_error_code=track.managed_tags.error_code,
        )


class TrackPage(BaseModel):
    items: list[TrackResponse]
    total: int
    page: int
    page_size: int
