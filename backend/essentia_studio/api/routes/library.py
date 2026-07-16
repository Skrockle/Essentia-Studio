from typing import Annotated

from fastapi import APIRouter, Depends, Query

from essentia_studio.api.dependencies import get_job_coordinator, get_track_repository
from essentia_studio.domain.jobs import JobType
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.schemas.jobs import JobResponse
from essentia_studio.schemas.library import TrackPage, TrackResponse
from essentia_studio.services.jobs import JobCoordinator

router = APIRouter(prefix="/library")


@router.post("/scan", response_model=JobResponse, status_code=202)
def scan_library(
    coordinator: Annotated[JobCoordinator, Depends(get_job_coordinator)],
) -> JobResponse:
    job = coordinator.submit(JobType.SCAN, ["music-root"], {})
    return JobResponse.from_record(job)


@router.get("/tracks", response_model=TrackPage)
def list_tracks(
    repository: Annotated[TrackRepository, Depends(get_track_repository)],
    search: str | None = None,
    present: bool | None = True,
    extension: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> TrackPage:
    tracks, total = repository.query(search, present, extension, page, page_size)
    return TrackPage(
        items=[TrackResponse.from_record(track) for track in tracks],
        total=total,
        page=page,
        page_size=page_size,
    )
