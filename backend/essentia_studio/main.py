from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from threading import Event

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from essentia_studio import __version__
from essentia_studio.analysis.fake_backend import FakeAnalysisBackend
from essentia_studio.analysis.process_backend import ProcessAnalysisBackend
from essentia_studio.analysis.protocol import AnalysisBackend
from essentia_studio.analysis.tensorflow_devices import (
    detect_tensorflow_devices,
    select_compute,
)
from essentia_studio.api.router import router as api_router
from essentia_studio.api.routes.health import router as health_router
from essentia_studio.config import RuntimeConfig
from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.jobs import JobType
from essentia_studio.errors import AppError, app_error_handler
from essentia_studio.playlists.storage import PlaylistStorage
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.repositories.playlists import PlaylistRepository
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.repositories.writes import WriteRepository
from essentia_studio.services.analysis_jobs import AnalysisJobService
from essentia_studio.services.capabilities import CapabilityService
from essentia_studio.services.jobs import JobCoordinator
from essentia_studio.services.metadata import MetadataService
from essentia_studio.services.scanner import scan_music_root
from essentia_studio.services.tag_operations import TagOperationService
from essentia_studio.tags.registry import TagAdapterRegistry


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    engine = create_sqlite_engine(runtime_config.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        apply_migrations(engine)
        settings_repository = SettingsRepository(engine)
        application_settings = settings_repository.get()
        track_repository = TrackRepository(engine)
        job_repository = JobRepository(engine)
        result_repository = ResultRepository(engine)
        playlist_repository = PlaylistRepository(engine)
        playlist_storage = PlaylistStorage(runtime_config.playlist_dir, playlist_repository)
        write_repository = WriteRepository(engine)
        tag_registry = TagAdapterRegistry()
        metadata_service = MetadataService()
        tag_operation_service = TagOperationService(
            result_repository,
            write_repository,
            tag_registry,
            runtime_config.music_root,
            application_settings.overwrite_existing,
        )
        analysis_backend: AnalysisBackend
        if runtime_config.analysis_backend == "fake":
            analysis_backend = FakeAnalysisBackend()
        else:
            device_report = detect_tensorflow_devices()
            compute = select_compute(
                application_settings.compute_preference,
                image_variant=runtime_config.image_variant,
                gpu_devices=device_report.gpu_devices,
            )
            available_compute = ["cpu"]
            if runtime_config.image_variant == "cuda" and device_report.gpu_devices:
                available_compute.append("cuda")
            analysis_backend = ProcessAnalysisBackend(
                runtime_config.model_dir,
                compute,
                application_settings.worker_count,
                runtime_config.image_variant,
                available_compute,
            )
        analysis_service = AnalysisJobService(
            analysis_backend,
            result_repository,
            track_repository,
            runtime_config.music_root,
        )

        def scan_handler(_job_id: str, _value: str, cancelled: Event) -> dict[str, int]:
            if cancelled.is_set():
                return {"scanned": 0, "present": 0, "missing": 0}
            summary = track_repository.replace_scan(
                scan_music_root(runtime_config.music_root, metadata_service),
                datetime.now(timezone.utc),
            )
            return asdict(summary)

        def analysis_handler(job_id: str, relative_path: str, _cancelled: Event) -> dict[str, str]:
            job = job_repository.get(job_id)
            options = AnalysisOptions(**job.configuration["analysis"])
            stored = analysis_service.process(relative_path, options, job_id)
            return {"result_id": stored.id, "relative_path": relative_path}

        job_coordinator = JobCoordinator(
            job_repository,
            {
                JobType.SCAN: scan_handler,
                JobType.ANALYSIS: analysis_handler,
            },
        )
        app.state.config = runtime_config
        app.state.engine = engine
        app.state.settings_repository = settings_repository
        app.state.track_repository = track_repository
        app.state.job_repository = job_repository
        app.state.result_repository = result_repository
        app.state.playlist_repository = playlist_repository
        app.state.playlist_storage = playlist_storage
        app.state.write_repository = write_repository
        app.state.tag_registry = tag_registry
        app.state.tag_operation_service = tag_operation_service
        app.state.job_coordinator = job_coordinator
        app.state.analysis_backend = analysis_backend
        app.state.capability_service = CapabilityService(runtime_config, analysis_backend)
        job_coordinator.start()
        yield
        job_coordinator.stop()
        if isinstance(analysis_backend, ProcessAnalysisBackend):
            analysis_backend.close()
        engine.dispose()

    app = FastAPI(title="Essentia Studio", version=__version__, lifespan=lifespan)
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
