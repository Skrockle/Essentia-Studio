from typing import Any, Literal

from pydantic import BaseModel, Field

from essentia_studio.playlists.storage import PlaylistFile


class PlaylistFileResponse(BaseModel):
    name: str
    definition: dict[str, Any] | None
    fingerprint: str
    status: str
    error: str | None

    @classmethod
    def from_record(cls, record: PlaylistFile) -> "PlaylistFileResponse":
        return cls(
            name=record.name,
            definition=record.definition,
            fingerprint=record.fingerprint,
            status=record.status,
            error=record.error,
        )


class CustomPlaylistRequest(BaseModel):
    filename: str
    definition: dict[str, Any]
    source_mode: Literal["preset", "this_is", "custom", "existing"] = "custom"


class PresetRequest(BaseModel):
    filename: str
    overrides: dict[str, Any] = Field(default_factory=dict)


class ThisIsRequest(BaseModel):
    filename: str
    artist: str
    method: str
    limit: int = Field(default=50, ge=1, le=100_000)
    name: str | None = None
    comment: str | None = None


class PlaylistUpdateRequest(BaseModel):
    expected_fingerprint: str
    definition: dict[str, Any]


class PlaylistDeleteRequest(BaseModel):
    expected_fingerprint: str
