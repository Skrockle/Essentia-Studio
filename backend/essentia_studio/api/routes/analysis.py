from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio.api.dependencies import (
    get_analysis_admission_service,
    get_job_coordinator,
    get_settings_service,
    get_track_repository,
)
from essentia_studio.domain.jobs import JobType
from essentia_studio.errors import AppError
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.schemas.analysis import AnalysisJobRequest
from essentia_studio.schemas.jobs import JobResponse
from essentia_studio.services.analysis_admission import AnalysisAdmissionService
from essentia_studio.services.jobs import JobCoordinator
from essentia_studio.services.settings import SettingsService

router = APIRouter(prefix="/analysis")


@router.post("/jobs", response_model=JobResponse, status_code=202)
def create_analysis_job(
    payload: AnalysisJobRequest,
    coordinator: Annotated[JobCoordinator, Depends(get_job_coordinator)],
    settings: Annotated[SettingsService, Depends(get_settings_service)],
    tracks: Annotated[TrackRepository, Depends(get_track_repository)],
    admission: Annotated[AnalysisAdmissionService, Depends(get_analysis_admission_service)],
) -> JobResponse:
    selected_tracks = _selected_tracks(payload, tracks)
    if not selected_tracks:
        raise AppError("empty_selection", "Die Auswahl enthält keine vorhandenen Titel.", 422)

    analysis_settings = settings.load().values.analysis
    options = payload.options(analysis_settings)
    admitted = admission.prepare(selected_tracks, options)
    if not admitted.items:
        _raise_when_nothing_is_admitted(admitted, len(selected_tracks))
    configuration = {
        "analysis": asdict(options),
        "worker_count": max(analysis_settings.workers, analysis_settings.cpu_workers),
        "selection": payload.model_dump(exclude_none=True),
        "heads_by_path": {
            item.relative_path: {
                "enable_genres": item.enable_genres,
                "enable_moods": item.enable_moods,
            }
            for item in admitted.items
        },
    }
    job = coordinator.submit(
        JobType.ANALYSIS,
        [item.relative_path for item in admitted.items],
        configuration,
    )
    return JobResponse.from_record(job)


def _selected_tracks(payload: AnalysisJobRequest, repository: TrackRepository):
    if payload.track_ids:
        return repository.get_by_ids(payload.track_ids)
    query = payload.query
    assert query is not None
    return repository.query_all(query.to_domain())


def _raise_when_nothing_is_admitted(admitted, candidate_count: int) -> None:
    if len(admitted.failures) == candidate_count:
        raise AppError(
            "managed_tags_unreadable",
            (
                f"Die Managed Tags von {len(admitted.failures)} ausgewählten Titeln "
                "konnten nicht gelesen werden."
            ),
            422,
        )
    raise AppError(
        "no_missing_managed_tags",
        "Die ausgewählten Titel enthalten bereits Genre- und Mood-Tags.",
        422,
    )
