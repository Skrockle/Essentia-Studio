from typing import Annotated

from fastapi import APIRouter, Depends, Request

from essentia_studio.api.dependencies import (
    get_result_repository,
    get_tag_operation_service,
    get_write_repository,
)
from essentia_studio.domain.tracks import TrackFingerprint
from essentia_studio.errors import AppError
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.writes import WriteRepository
from essentia_studio.schemas.writes import (
    WriteBatchResponse,
    WriteOperationResponse,
    WritePreviewItem,
    WritePreviewResponse,
    WriteSelectionRequest,
)
from essentia_studio.services.path_safety import resolve_track_path
from essentia_studio.services.tag_operations import TagOperationService

router = APIRouter(prefix="/writes")


@router.post("/preview", response_model=WritePreviewResponse)
def preview_writes(
    payload: WriteSelectionRequest,
    request: Request,
    results: Annotated[ResultRepository, Depends(get_result_repository)],
) -> WritePreviewResponse:
    result_ids = results.resolve_selection(payload.selection.model_dump())
    items: list[WritePreviewItem] = []
    conflict_count = 0
    for result_id in result_ids:
        result = results.get(result_id)
        path = resolve_track_path(request.app.state.config.music_root, result.relative_path)
        stat = path.stat()
        conflict = TrackFingerprint(stat.st_size, stat.st_mtime_ns) != result.fingerprint
        conflict_count += int(conflict)
        if len(items) < 20:
            try:
                snapshot = request.app.state.tag_registry.for_path(path).read(path)
            except (OSError, ValueError) as error:
                raise AppError(
                    "invalid_audio_file",
                    "Die Datei ist beschädigt oder kein gültiges Audioformat "
                    "und kann nicht gelesen werden.",
                    422,
                    {"relative_path": result.relative_path, "reason": str(error)},
                ) from error
            items.append(
                WritePreviewItem(
                    result_id=result.id,
                    relative_path=result.relative_path,
                    before_genres=snapshot.fields.get("genres", []),
                    after_genres=result.draft.genres,
                    before_moods=snapshot.fields.get("moods", []),
                    after_moods=result.draft.moods,
                    conflict=conflict,
                )
            )
    return WritePreviewResponse(
        total=len(result_ids),
        writable=len(result_ids) - conflict_count,
        conflicts=conflict_count,
        items=items,
    )


@router.post("", response_model=WriteBatchResponse)
def write_selected(
    payload: WriteSelectionRequest,
    results: Annotated[ResultRepository, Depends(get_result_repository)],
    service: Annotated[TagOperationService, Depends(get_tag_operation_service)],
) -> WriteBatchResponse:
    result_ids = results.resolve_selection(payload.selection.model_dump())
    return WriteBatchResponse(
        operations=[
            WriteOperationResponse.from_record(operation)
            for operation in service.write_many(result_ids)
        ]
    )


@router.get("", response_model=list[WriteOperationResponse])
def list_writes(
    repository: Annotated[WriteRepository, Depends(get_write_repository)],
) -> list[WriteOperationResponse]:
    return [WriteOperationResponse.from_record(value) for value in repository.list()]


@router.post("/{operation_id}/undo", response_model=WriteOperationResponse)
def undo_write(
    operation_id: str,
    service: Annotated[TagOperationService, Depends(get_tag_operation_service)],
) -> WriteOperationResponse:
    return WriteOperationResponse.from_record(service.undo(operation_id))
