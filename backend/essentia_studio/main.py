from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from threading import Event

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from essentia_studio import __version__
from essentia_studio.analysis.fake_backend import FakeAnalysisBackend
from essentia_studio.analysis.pool_manager import BackendFactory, WorkerPoolManager
from essentia_studio.analysis.process_backend import ProcessAnalysisBackend
from essentia_studio.analysis.protocol import AnalysisBackend
from essentia_studio.analysis.tensorflow_devices import (
    detect_tensorflow_devices,
    select_compute,
)
from essentia_studio.api.router import router as api_router
from essentia_studio.api.routes.health import router as health_router
from essentia_studio.benchmark.runner import BenchmarkRunner, fake_benchmark_worker
from essentia_studio.config import RuntimeConfig
from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.jobs import JobType
from essentia_studio.errors import AppError, app_error_handler
from essentia_studio.playlists.storage import PlaylistStorage
from essentia_studio.repositories.benchmarks import BenchmarkRepository
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.repositories.playlists import PlaylistRepository
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.settings import SettingsRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.repositories.writes import WriteRepository
from essentia_studio.schemas.settings import AnalysisSettings
from essentia_studio.services.analysis_jobs import AnalysisJobService
from essentia_studio.services.automation import AutomationService
from essentia_studio.services.automation_status import AutomationStatusStore
from essentia_studio.services.benchmarks import BenchmarkService
from essentia_studio.services.capabilities import CapabilityService
from essentia_studio.services.jobs import JobCoordinator
from essentia_studio.services.metadata import MetadataService
from essentia_studio.services.scanner import scan_music_root
from essentia_studio.services.settings import SettingsService
from essentia_studio.services.tag_catalog import TagCatalogService
from essentia_studio.services.tag_operations import TagOperationService
from essentia_studio.services.track_state import TrackStateService
from essentia_studio.tags.registry import TagAdapterRegistry


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    engine = create_sqlite_engine(runtime_config.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        apply_migrations(engine)
        settings_repository = SettingsRepository(engine)
        tag_catalog_service = TagCatalogService(runtime_config.model_dir)
        settings_service = SettingsService(runtime_config.settings_path)
        application_settings = settings_service.migrate_legacy(settings_repository.get()).values
        track_repository = TrackRepository(engine)
        track_state_service = TrackStateService(engine)
        job_repository = JobRepository(engine)
        benchmark_repository = BenchmarkRepository(engine)
        result_repository = ResultRepository(engine)
        result_repository.reconcile_hierarchical_genres()
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
            application_settings.analysis.overwrite_existing,
        )
        gpu_devices: tuple[str, ...] = ()
        if runtime_config.analysis_backend != "fake":
            device_report = detect_tensorflow_devices()
            gpu_devices = device_report.gpu_devices
        pool_manager = WorkerPoolManager(
            _analysis_backend_factory(runtime_config, gpu_devices),
            application_settings.analysis,
        )
        analysis_backend: AnalysisBackend = pool_manager
        analysis_service = AnalysisJobService(
            analysis_backend,
            result_repository,
            track_repository,
            runtime_config.music_root,
        )

        def refresh_library():
            return track_repository.replace_scan(
                scan_music_root(runtime_config.music_root, metadata_service),
                datetime.now(timezone.utc),
            )

        def scan_handler(_job_id: str, _value: str, cancelled: Event) -> dict[str, int]:
            if cancelled.is_set():
                return {"scanned": 0, "present": 0, "missing": 0}
            summary = refresh_library()
            return asdict(summary)

        def analysis_handler(job_id: str, relative_path: str, cancelled: Event) -> dict[str, str]:
            job = job_repository.get(job_id)
            options = AnalysisOptions(**job.configuration["analysis"])
            stored = analysis_service.process(relative_path, options, job_id, cancelled)
            return {"result_id": stored.id, "relative_path": relative_path}

        def write_handler(_job_id: str, result_id: str, _cancelled: Event) -> dict[str, str]:
            operation = tag_operation_service.write_one(result_id, "manual")
            if operation.status != "verified":
                raise AppError(
                    operation.error_code or "write_not_verified",
                    operation.error_message or "Die Tags konnten nicht verifiziert werden.",
                    409,
                )
            return {
                "operation_id": operation.id,
                "relative_path": operation.relative_path,
                "status": operation.status,
            }

        job_coordinator = JobCoordinator(
            job_repository,
            {
                JobType.SCAN: scan_handler,
                JobType.ANALYSIS: analysis_handler,
                JobType.WRITE: write_handler,
            },
        )
        job_coordinator.register_cancellation_handler(JobType.ANALYSIS, pool_manager.cancel)
        benchmark_runner = _benchmark_runner(runtime_config)
        benchmark_service = BenchmarkService(
            settings=settings_service,
            tracks=track_repository,
            jobs=job_repository,
            coordinator=job_coordinator,
            repository=benchmark_repository,
            runner=benchmark_runner,
            image_variant=runtime_config.image_variant,
            available_compute=analysis_backend.available_compute(),
            model_inventory=analysis_backend.model_inventory(),
            pool_manager=pool_manager,
            gpu_devices=gpu_devices,
        )

        def benchmark_handler(
            job_id: str,
            relative_path: str,
            cancelled: Event,
        ) -> dict[str, str]:
            job = job_repository.get(job_id)
            run = benchmark_service.execute(
                job.configuration["run_id"],
                relative_path,
                AnalysisOptions(**job.configuration["analysis"]),
                job.configuration["compute_modes"],
                job.configuration.get("batch_sizes", [1]),
                cancelled,
            )
            return {"run_id": run.id, "relative_path": relative_path}

        job_coordinator.register_handler(JobType.BENCHMARK, benchmark_handler)
        automation_status_store = AutomationStatusStore(settings_service)
        automation_service = AutomationService(
            settings=settings_service,
            tracks=track_repository,
            states=track_state_service,
            coordinator=job_coordinator,
            results=result_repository,
            tag_operations=tag_operation_service,
            refresh_library=refresh_library,
            music_root=runtime_config.music_root,
            playlist_dir=runtime_config.playlist_dir,
            status_store=automation_status_store,
        )
        app.state.config = runtime_config
        app.state.engine = engine
        app.state.settings_service = settings_service
        app.state.tag_catalog_service = tag_catalog_service
        app.state.automation_status_store = automation_status_store
        app.state.automation_service = automation_service
        app.state.benchmark_service = benchmark_service
        app.state.benchmark_repository = benchmark_repository
        app.state.track_repository = track_repository
        app.state.track_state_service = track_state_service
        app.state.job_repository = job_repository
        app.state.result_repository = result_repository
        app.state.playlist_repository = playlist_repository
        app.state.playlist_storage = playlist_storage
        app.state.write_repository = write_repository
        app.state.tag_registry = tag_registry
        app.state.tag_operation_service = tag_operation_service
        app.state.job_coordinator = job_coordinator
        app.state.analysis_backend = analysis_backend
        app.state.worker_pool_manager = pool_manager
        app.state.capability_service = CapabilityService(runtime_config, analysis_backend)
        job_coordinator.start()
        automation_service.start()
        yield
        automation_service.stop()
        job_coordinator.stop()
        pool_manager.close()
        engine.dispose()

    app = FastAPI(title="Essentia Studio", version=__version__, lifespan=lifespan)
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health_router)
    app.include_router(api_router)

    _mount_frontend(app, runtime_config)

    return app


def _benchmark_runner(config: RuntimeConfig) -> BenchmarkRunner:
    if config.analysis_backend == "fake":
        return BenchmarkRunner(
            config.music_root,
            config.model_dir,
            worker=fake_benchmark_worker,
        )
    return BenchmarkRunner(config.music_root, config.model_dir)


def _analysis_backend_factory(
    config: RuntimeConfig,
    gpu_devices: tuple[str, ...],
) -> BackendFactory:
    def create(settings: AnalysisSettings) -> AnalysisBackend:
        if config.analysis_backend == "fake":
            return FakeAnalysisBackend()
        compute = select_compute(
            settings.compute,
            image_variant=config.image_variant,
            gpu_devices=gpu_devices,
        )
        available_compute = ["cpu"]
        if config.image_variant == "cuda" and gpu_devices:
            available_compute.append("cuda")
        return ProcessAnalysisBackend(
            config.model_dir,
            compute,
            settings.workers,
            config.image_variant,
            available_compute,
            cpu_workers=settings.cpu_workers if settings.cpu_workers != 1 else settings.workers,
            gpu_batch_size=settings.gpu_batch_size,
            gpu_queue_size=settings.gpu_queue_size,
            inference_runtime=config.inference_runtime,
        )

    return create


def _mount_frontend(app: FastAPI, config: RuntimeConfig) -> None:
    if (config.frontend_dir / "index.html").is_file():
        app.mount(
            "/",
            StaticFiles(directory=config.frontend_dir, html=True),
            name="frontend",
        )
