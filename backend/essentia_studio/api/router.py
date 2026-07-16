from fastapi import APIRouter

from essentia_studio.api.routes import analysis, jobs, library, results, settings, writes

router = APIRouter(prefix="/api")
router.include_router(settings.router)
router.include_router(jobs.router)
router.include_router(library.router)
router.include_router(analysis.router)
router.include_router(results.router)
router.include_router(writes.router)
