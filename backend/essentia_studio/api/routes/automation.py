from typing import Annotated

from fastapi import APIRouter, Depends

from essentia_studio.api.dependencies import get_automation_status_store
from essentia_studio.schemas.automation import AutomationStatus
from essentia_studio.services.automation_status import AutomationStatusStore

router = APIRouter(prefix="/automation")


@router.get("/status", response_model=AutomationStatus)
def get_status(
    store: Annotated[AutomationStatusStore, Depends(get_automation_status_store)],
) -> AutomationStatus:
    return store.snapshot()
