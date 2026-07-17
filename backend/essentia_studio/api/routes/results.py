from typing import Annotated

from fastapi import APIRouter, Depends, Query

from essentia_studio.api.dependencies import get_result_repository, get_track_state_service
from essentia_studio.errors import AppError
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.schemas.results import (
    AffectedResponse,
    BulkDraftUpdate,
    DraftUpdate,
    ResultPage,
    ResultQuery,
    ResultResponse,
    SelectionUpdate,
)
from essentia_studio.services.labels import normalize_tags
from essentia_studio.services.track_state import TrackStateService

router = APIRouter(prefix="/results")


@router.get("", response_model=ResultPage)
def list_results(
    repository: Annotated[ResultRepository, Depends(get_result_repository)],
    state_service: Annotated[TrackStateService, Depends(get_track_state_service)],
    job_id: str | None = None,
    search: str | None = None,
    genre: str | None = None,
    mood: str | None = None,
    status: str | None = None,
    selected: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ResultPage:
    filters = ResultQuery(
        job_id=job_id,
        search=search,
        genre=genre,
        mood=mood,
        status=status,
        selected=selected,
    ).model_dump(exclude_none=True)
    results, total, selected_count = repository.query(filters, page, page_size)
    states = state_service.states([result.track_id for result in results])
    return ResultPage(
        items=[
            ResultResponse.from_record(result, states[result.track_id]) for result in results
        ],
        total=total,
        page=page,
        page_size=page_size,
        selected_count=selected_count,
    )


@router.patch("/{result_id}/draft", response_model=ResultResponse)
def update_draft(
    result_id: str,
    payload: DraftUpdate,
    repository: Annotated[ResultRepository, Depends(get_result_repository)],
) -> ResultResponse:
    genres = normalize_tags(payload.genres) if payload.genres is not None else None
    moods = normalize_tags(payload.moods) if payload.moods is not None else None
    return ResultResponse.from_record(repository.replace_draft(result_id, genres, moods))


@router.post("/selection", response_model=AffectedResponse)
def update_selection(
    payload: SelectionUpdate,
    repository: Annotated[ResultRepository, Depends(get_result_repository)],
) -> AffectedResponse:
    affected = repository.update_selection(payload.selection.model_dump(), payload.selected)
    return AffectedResponse(affected=affected)


@router.post("/bulk-draft", response_model=AffectedResponse)
def bulk_update_drafts(
    payload: BulkDraftUpdate,
    repository: Annotated[ResultRepository, Depends(get_result_repository)],
) -> AffectedResponse:
    normalized = normalize_tags([payload.value])
    if not normalized:
        raise AppError("empty_tag", "Genre oder Mood darf nicht leer sein.", 422)
    value = normalized[0]
    affected = repository.bulk_update(
        payload.selection.model_dump(),
        payload.operation,
        value,
    )
    return AffectedResponse(affected=affected)
