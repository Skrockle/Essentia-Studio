import asyncio
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from essentia_studio.api.dependencies import get_job_coordinator, get_job_repository
from essentia_studio.domain.jobs import TERMINAL_STATUSES
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.schemas.jobs import JobEventResponse, JobItemResponse, JobResponse
from essentia_studio.services.jobs import JobCoordinator

router = APIRouter(prefix="/jobs")


@router.get("", response_model=list[JobResponse])
def list_jobs(
    repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> list[JobResponse]:
    return [JobResponse.from_record(job) for job in repository.list()]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> JobResponse:
    return JobResponse.from_record(repository.get(job_id))


@router.get("/{job_id}/items", response_model=list[JobItemResponse])
def list_job_items(
    job_id: str,
    repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> list[JobItemResponse]:
    repository.get(job_id)
    return [JobItemResponse.from_record(item) for item in repository.list_items(job_id)]


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: str,
    coordinator: Annotated[JobCoordinator, Depends(get_job_coordinator)],
) -> JobResponse:
    return JobResponse.from_record(coordinator.cancel(job_id))


@router.post("/{job_id}/resume", response_model=JobResponse, status_code=202)
def resume_job(
    job_id: str,
    coordinator: Annotated[JobCoordinator, Depends(get_job_coordinator)],
) -> JobResponse:
    return JobResponse.from_record(coordinator.resume(job_id))


@router.get("/{job_id}/events", response_class=EventSourceResponse)
async def stream_job_events(
    job_id: str,
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    after: int = 0,
) -> AsyncIterable[ServerSentEvent]:
    sequence = after
    while True:
        events = repository.events_after(job_id, sequence)
        for event in events:
            sequence = event.sequence
            yield ServerSentEvent(
                data=JobEventResponse.from_record(event),
                event=event.kind,
                id=str(event.sequence),
            )
        if repository.get(job_id).status in TERMINAL_STATUSES and not events:
            return
        await asyncio.sleep(0.05)
