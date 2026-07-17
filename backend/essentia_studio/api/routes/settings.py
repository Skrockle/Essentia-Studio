from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio.analysis.pool_manager import WorkerPoolManager
from essentia_studio.api.dependencies import (
    get_automation_service,
    get_capability_service,
    get_settings_service,
    get_worker_pool_manager,
)
from essentia_studio.errors import AppError
from essentia_studio.schemas.settings import AppSettingsUpdate, EffectiveSettings
from essentia_studio.services.automation import AutomationService
from essentia_studio.services.capabilities import CapabilityService
from essentia_studio.services.settings import SettingsService

router = APIRouter(prefix="/settings")


@router.get("", response_model=EffectiveSettings)
def get_settings(
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> EffectiveSettings:
    return service.load()


@router.put("", response_model=EffectiveSettings)
def put_settings(
    payload: AppSettingsUpdate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    capability_service: Annotated[CapabilityService, Depends(get_capability_service)],
    automation_service: Annotated[AutomationService, Depends(get_automation_service)],
    pool_manager: Annotated[WorkerPoolManager, Depends(get_worker_pool_manager)],
) -> EffectiveSettings:
    compute_preference = payload.analysis.compute if payload.analysis is not None else None
    available_compute = capability_service.inspect().available_compute

    if compute_preference not in {None, "auto"} and compute_preference not in available_compute:
        raise AppError(
            "compute_mode_unavailable",
            "CUDA ist in diesem Image nicht verfügbar.",
            409,
        )

    pool_fields = {"workers", "compute"}
    reconfigure_pool = bool(
        payload.analysis is not None
        and payload.analysis.model_fields_set.intersection(pool_fields)
    )
    if reconfigure_pool and pool_manager.is_busy():
        raise AppError(
            "analysis_pool_busy",
            "Die Worker können während eines Analysejobs nicht geändert werden.",
            409,
        )

    effective = service.update(payload)
    if reconfigure_pool:
        pool_manager.reconfigure(effective.values.analysis)
    automation_service.reconfigure()
    return effective
