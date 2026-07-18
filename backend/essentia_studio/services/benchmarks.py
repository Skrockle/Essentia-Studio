from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
from threading import Event, Lock

from essentia_studio.analysis.pool_manager import WorkerPoolManager
from essentia_studio.benchmark.resources import (
    ResourceLimits,
    detect_resource_limits,
    recommend_workers,
)
from essentia_studio.benchmark.runner import BenchmarkRunner, select_sample
from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.benchmarks import BenchmarkRun, ComputeMode, snapshot_hash
from essentia_studio.domain.jobs import JobRecord, JobType
from essentia_studio.errors import AppError
from essentia_studio.repositories.benchmarks import BenchmarkRepository
from essentia_studio.repositories.jobs import JobRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.jobs import JobCoordinator
from essentia_studio.services.settings import SettingsService


class BenchmarkService:
    def __init__(
        self,
        *,
        settings: SettingsService,
        tracks: TrackRepository,
        jobs: JobRepository,
        coordinator: JobCoordinator,
        repository: BenchmarkRepository,
        runner: BenchmarkRunner,
        image_variant: str,
        available_compute: Sequence[str],
        model_inventory: list[dict[str, str]],
        pool_manager: WorkerPoolManager,
        gpu_devices: Sequence[str] = (),
        resource_probe: Callable[[], ResourceLimits] = detect_resource_limits,
    ) -> None:
        self._settings = settings
        self._tracks = tracks
        self._jobs = jobs
        self._coordinator = coordinator
        self._repository = repository
        self._runner = runner
        self._image_variant = image_variant
        self._available_compute = [
            mode for mode in available_compute if mode in {"cpu", "cuda"}
        ]
        self._model_inventory = model_inventory
        self._gpu_devices = list(gpu_devices)
        self._resource_probe = resource_probe
        self._pool_manager = pool_manager
        self._submit_lock = Lock()

    def submit(self) -> JobRecord:
        with self._submit_lock:
            if self._jobs.has_active():
                raise AppError(
                    "benchmark_system_busy",
                    "Der Benchmark kann erst starten, wenn alle Jobs beendet sind.",
                    409,
                )
            settings = self._settings.load().values
            tracks, _total = self._tracks.query(present=True, page=1, page_size=1_000_000)
            sample = select_sample(tracks, settings.benchmark.minimum_track_seconds)
            snapshot = self.environment_snapshot()
            run = self._repository.create(
                snapshot=snapshot,
                sample_track_id=sample.id,
                sample_relative_path=sample.relative_path,
                sample_seconds=60,
            )
            options = self._analysis_options()
            return self._coordinator.submit(
                JobType.BENCHMARK,
                [sample.relative_path],
                {
                    "run_id": run.id,
                    "analysis": asdict(options),
                    "compute_modes": self._available_compute or ["cpu"],
                },
            )

    def execute(
        self,
        run_id: str,
        relative_path: str,
        options: AnalysisOptions,
        compute_modes: Sequence[ComputeMode],
        cancel: Event,
    ) -> BenchmarkRun:
        try:
            sample = self._tracks.get_by_path(relative_path)
            measurements = self._runner.run(sample, options, compute_modes, cancel)
            if cancel.is_set():
                return self._repository.cancel(run_id)
            for measurement in measurements:
                self._repository.record_measurement(run_id, measurement)
            cpu = next(
                (measurement for measurement in measurements if measurement.compute == "cpu"),
                None,
            )
            if cpu is None:
                raise AppError(
                    "benchmark_cpu_missing",
                    "Die CPU-Referenzmessung ist fehlgeschlagen.",
                    500,
                )
            limits = self._resource_probe()
            benchmark_settings = self._settings.load().values.benchmark
            workers = recommend_workers(
                limits.memory_bytes,
                cpu.baseline_peak_bytes,
                cpu.worker_peak_bytes,
                limits.cpu_count,
                benchmark_settings.safety_margin_percent / 100,
            )
            return self._repository.finish(run_id, workers)
        except Exception as error:
            self._repository.fail(run_id, str(error))
            raise

    def list(self) -> list[tuple[BenchmarkRun, bool]]:
        current_hash = snapshot_hash(self.environment_snapshot())
        return [
            (run, run.status == "completed" and run.snapshot_hash == current_hash)
            for run in self._repository.list()
        ]

    def apply(self, run_id: str):
        if self._jobs.has_active() or self._pool_manager.is_busy():
            raise AppError(
                "benchmark_system_busy",
                "Die Empfehlung kann erst nach Abschluss aller Analysejobs übernommen werden.",
                409,
            )
        run = self._repository.get(run_id)
        if run.status != "completed" or not run.recommended_workers:
            raise AppError(
                "benchmark_not_applicable",
                "Dieser Benchmark enthält keine anwendbare Worker-Empfehlung.",
                409,
            )
        if run.snapshot_hash != snapshot_hash(self.environment_snapshot()):
            raise AppError(
                "benchmark_stale",
                "Die Ressourcen oder Analyseoptionen haben sich seit dem Benchmark geändert.",
                409,
            )
        effective = self._settings.update(
            {"analysis": {"workers": run.recommended_workers}}
        )
        self._pool_manager.reconfigure(effective.values.analysis)
        return effective

    def environment_snapshot(self) -> dict[str, object]:
        limits = self._resource_probe()
        settings = self._settings.load().values
        models = sorted(
            (
                {key: value for key, value in model.items() if key in {"name", "sha256", "status"}}
                for model in self._model_inventory
            ),
            key=lambda model: model.get("name", ""),
        )
        return {
            "memory_bytes": limits.memory_bytes,
            "cpu_count": limits.cpu_count,
            "gpu_devices": self._gpu_devices,
            "image_variant": self._image_variant,
            "available_compute": self._available_compute,
            "models": models,
            "analysis": asdict(self._analysis_options()),
            "minimum_track_seconds": settings.benchmark.minimum_track_seconds,
            "safety_margin_percent": settings.benchmark.safety_margin_percent,
        }

    def _analysis_options(self) -> AnalysisOptions:
        analysis = self._settings.load().values.analysis
        return AnalysisOptions(
            genre_threshold=analysis.genre_threshold,
            mood_threshold=analysis.mood_threshold,
            genre_count=analysis.genre_count,
            max_audio_seconds=60,
        )
