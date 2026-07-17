from fastapi import APIRouter

from essentia_studio.api.routes import (
    analysis,
    automation,
    benchmarks,
    jobs,
    library,
    playlists,
    results,
    settings,
    tag_options,
    writes,
)

router = APIRouter(prefix="/api")
router.include_router(settings.router)
router.include_router(automation.router)
router.include_router(benchmarks.router)
router.include_router(jobs.router)
router.include_router(library.router)
router.include_router(analysis.router)
router.include_router(results.router)
router.include_router(writes.router)
router.include_router(playlists.router)
router.include_router(tag_options.router)
