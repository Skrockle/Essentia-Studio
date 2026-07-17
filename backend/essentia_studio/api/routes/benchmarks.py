from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio.api.dependencies import get_benchmark_service
from essentia_studio.schemas.benchmarks import BenchmarkResponse
from essentia_studio.schemas.jobs import JobResponse
from essentia_studio.services.benchmarks import BenchmarkService

router = APIRouter(prefix="/benchmarks")


@router.post("", response_model=JobResponse, status_code=202)
def start_benchmark(
    service: Annotated[BenchmarkService, Depends(get_benchmark_service)],
) -> JobResponse:
    return JobResponse.from_record(service.submit())


@router.get("", response_model=list[BenchmarkResponse])
def list_benchmarks(
    service: Annotated[BenchmarkService, Depends(get_benchmark_service)],
) -> list[BenchmarkResponse]:
    return [BenchmarkResponse.from_record(run, current) for run, current in service.list()]
