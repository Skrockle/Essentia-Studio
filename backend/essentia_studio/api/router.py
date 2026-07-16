from fastapi import APIRouter

from essentia_studio.api.routes import settings

router = APIRouter(prefix="/api")
router.include_router(settings.router)
