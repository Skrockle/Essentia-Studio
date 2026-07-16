from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from essentia_studio.api.router import router as api_router
from essentia_studio.api.routes.health import router as health_router
from essentia_studio.config import RuntimeConfig
from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.errors import AppError, app_error_handler
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.services.capabilities import CapabilityService


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    engine = create_sqlite_engine(runtime_config.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        apply_migrations(engine)
        app.state.config = runtime_config
        app.state.engine = engine
        app.state.settings_repository = SettingsRepository(engine)
        app.state.capability_service = CapabilityService(runtime_config)
        yield
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
