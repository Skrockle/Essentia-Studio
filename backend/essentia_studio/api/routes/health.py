from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio import __version__
from essentia_studio.api.dependencies import get_capability_service
from essentia_studio.schemas.common import Capabilities, HealthResponse
from essentia_studio.services.capabilities import CapabilityService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=__version__)


@router.get("/api/capabilities", response_model=Capabilities)
def capabilities(
    service: Annotated[CapabilityService, Depends(get_capability_service)],
) -> Capabilities:
    return service.inspect()
