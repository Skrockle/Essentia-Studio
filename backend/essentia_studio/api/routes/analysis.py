from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio.api.dependencies import (
    get_job_coordinator,
    get_settings_repository,
    get_track_repository,
)
from essentia_studio.domain.jobs import JobType
from essentia_studio.errors import AppError
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.schemas.analysis import AnalysisJobRequest
from essentia_studio.schemas.jobs import JobResponse
from essentia_studio.services.jobs import JobCoordinator

router = APIRouter(prefix="/analysis")


@router.post("/jobs", response_model=JobResponse, status_code=202)
def create_analysis_job(
    payload: AnalysisJobRequest,
    coordinator: Annotated[JobCoordinator, Depends(get_job_coordinator)],
    settings: Annotated[SettingsRepository, Depends(get_settings_repository)],
    tracks: Annotated[TrackRepository, Depends(get_track_repository)],
) -> JobResponse:
    selected_tracks = _selected_tracks(payload, tracks)
    if not selected_tracks:
        raise AppError("empty_selection", "Die Auswahl enthält keine vorhandenen Titel.", 422)

    options = payload.options(settings.get())
    configuration = {
        "analysis": asdict(options),
        "selection": payload.model_dump(exclude_none=True),
    }
    job = coordinator.submit(
        JobType.ANALYSIS,
        [track.relative_path for track in selected_tracks],
        configuration,
    )
    return JobResponse.from_record(job)


def _selected_tracks(payload: AnalysisJobRequest, repository: TrackRepository):
    if payload.track_ids:
        return repository.get_by_ids(payload.track_ids)
    query = payload.query
    assert query is not None
    return repository.query(
        query.search,
        query.present,
        query.extension,
        page=1,
        page_size=1_000_000,
    )[0]
