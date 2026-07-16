from copy import deepcopy
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from essentia_studio.api.dependencies import get_playlist_storage
from essentia_studio.errors import AppError
from essentia_studio.playlists.catalog import PlaylistCatalog
from essentia_studio.playlists.storage import PlaylistStorage
from essentia_studio.playlists.this_is import build_this_is
from essentia_studio.playlists.validation import validate_playlist
from essentia_studio.schemas.playlists import (
    CustomPlaylistRequest,
    PlaylistDeleteRequest,
    PlaylistFileResponse,
    PlaylistUpdateRequest,
    PresetRequest,
    ThisIsRequest,
)

router = APIRouter(prefix="/playlists")


@router.get("/catalog")
def get_catalog() -> dict:
    return PlaylistCatalog.load().as_dict()


@router.post(
    "/from-preset/{slug}",
    response_model=PlaylistFileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_from_preset(
    slug: str,
    payload: PresetRequest,
    storage: Annotated[PlaylistStorage, Depends(get_playlist_storage)],
) -> PlaylistFileResponse:
    catalog = PlaylistCatalog.load()
    preset = next((item for item in catalog.presets if item.slug == slug), None)
    if preset is None:
        raise AppError("preset_not_found", "Das Preset wurde nicht gefunden.", 404)
    allowed_overrides = {"name", "comment", "limit", "sort", "order"}
    if set(payload.overrides) - allowed_overrides:
        raise AppError("invalid_preset_override", "Das Preset-Override ist ungültig.", 422)
    definition = deepcopy(preset.definition) | payload.overrides
    validated = validate_playlist(definition, catalog)
    return PlaylistFileResponse.from_record(
        storage.create(payload.filename, validated, "preset")
    )


@router.post(
    "/this-is/preview",
)
def preview_this_is(payload: ThisIsRequest) -> dict:
    return build_this_is(
        payload.artist,
        payload.method,
        payload.limit,
        payload.name,
        payload.comment,
    ).model_dump(exclude_none=True)


@router.post(
    "/this-is",
    response_model=PlaylistFileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_this_is(
    payload: ThisIsRequest,
    storage: Annotated[PlaylistStorage, Depends(get_playlist_storage)],
) -> PlaylistFileResponse:
    definition = build_this_is(
        payload.artist,
        payload.method,
        payload.limit,
        payload.name,
        payload.comment,
    )
    return PlaylistFileResponse.from_record(
        storage.create(payload.filename, definition, "this_is")
    )


@router.get("", response_model=list[PlaylistFileResponse])
def list_playlists(
    storage: Annotated[PlaylistStorage, Depends(get_playlist_storage)],
) -> list[PlaylistFileResponse]:
    return [PlaylistFileResponse.from_record(record) for record in storage.list()]


@router.post("", response_model=PlaylistFileResponse, status_code=status.HTTP_201_CREATED)
def create_custom_playlist(
    payload: CustomPlaylistRequest,
    storage: Annotated[PlaylistStorage, Depends(get_playlist_storage)],
) -> PlaylistFileResponse:
    definition = validate_playlist(payload.definition, PlaylistCatalog.load())
    return PlaylistFileResponse.from_record(
        storage.create(payload.filename, definition, payload.source_mode)
    )


@router.get("/{name}", response_model=PlaylistFileResponse)
def read_playlist(
    name: str,
    storage: Annotated[PlaylistStorage, Depends(get_playlist_storage)],
) -> PlaylistFileResponse:
    return PlaylistFileResponse.from_record(storage.read(name))


@router.put("/{name}", response_model=PlaylistFileResponse)
def update_playlist(
    name: str,
    payload: PlaylistUpdateRequest,
    storage: Annotated[PlaylistStorage, Depends(get_playlist_storage)],
) -> PlaylistFileResponse:
    definition = validate_playlist(payload.definition, PlaylistCatalog.load())
    return PlaylistFileResponse.from_record(
        storage.update(name, definition, payload.expected_fingerprint, "existing")
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    name: str,
    payload: PlaylistDeleteRequest,
    storage: Annotated[PlaylistStorage, Depends(get_playlist_storage)],
) -> Response:
    storage.delete(name, payload.expected_fingerprint)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
