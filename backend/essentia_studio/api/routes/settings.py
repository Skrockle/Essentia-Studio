from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio.api.dependencies import (
    get_capability_service,
    get_settings_repository,
)
from essentia_studio.errors import AppError
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.schemas.settings import AppSettings, AppSettingsUpdate
from essentia_studio.services.capabilities import CapabilityService

router = APIRouter(prefix="/settings")


@router.get("", response_model=AppSettings)
def get_settings(
    repository: Annotated[SettingsRepository, Depends(get_settings_repository)],
) -> AppSettings:
    return repository.get()


@router.put("", response_model=AppSettings)
def put_settings(
    payload: AppSettingsUpdate,
    repository: Annotated[SettingsRepository, Depends(get_settings_repository)],
    capability_service: Annotated[CapabilityService, Depends(get_capability_service)],
) -> AppSettings:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    compute_preference = updates.get("compute_preference")
    available_compute = capability_service.inspect().available_compute

    if compute_preference not in {None, "auto"} and compute_preference not in available_compute:
        raise AppError(
            "compute_mode_unavailable",
            "CUDA ist in diesem Image nicht verfügbar.",
            409,
        )

    current = repository.get()
    return repository.replace(current.model_copy(update=updates))
