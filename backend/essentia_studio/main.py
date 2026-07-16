from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from threading import Event

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from essentia_studio.api.router import router as api_router
from essentia_studio.api.routes.health import router as health_router
from essentia_studio.config import RuntimeConfig
from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.jobs import JobType
from essentia_studio.errors import AppError, app_error_handler
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.capabilities import CapabilityService
from essentia_studio.services.jobs import JobCoordinator
from essentia_studio.services.scanner import scan_music_root


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    engine = create_sqlite_engine(runtime_config.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        apply_migrations(engine)
        track_repository = TrackRepository(engine)
        job_repository = JobRepository(engine)

        def scan_handler(_value: str, cancelled: Event) -> dict[str, int]:
            if cancelled.is_set():
                return {"scanned": 0, "present": 0, "missing": 0}
            summary = track_repository.replace_scan(
                scan_music_root(runtime_config.music_root),
                datetime.now(timezone.utc),
            )
            return asdict(summary)

        job_coordinator = JobCoordinator(job_repository, {JobType.SCAN: scan_handler})
        app.state.config = runtime_config
        app.state.engine = engine
        app.state.settings_repository = SettingsRepository(engine)
        app.state.track_repository = track_repository
        app.state.job_repository = job_repository
        app.state.job_coordinator = job_coordinator
        app.state.capability_service = CapabilityService(runtime_config)
        job_coordinator.start()
        yield
        job_coordinator.stop()
        engine.dispose()

    app = FastAPI(title="Essentia Studio", version="0.0.0", lifespan=lifespan)
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health_router)
    app.include_router(api_router)

    if (runtime_config.frontend_dir / "index.html").is_file():
        app.mount(
            "/",
            StaticFiles(directory=runtime_config.frontend_dir, html=True),
            name="frontend",
        )

    return app
