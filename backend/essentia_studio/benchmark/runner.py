from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from threading import Event

from essentia_studio.benchmark.worker import run_isolated_worker
from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.benchmarks import ComputeMeasurement, ComputeMode
from essentia_studio.domain.tracks import LibraryTrack
from essentia_studio.errors import AppError

BenchmarkWorker = Callable[
    [Path, AnalysisOptions, Path, ComputeMode, Event, int],
    ComputeMeasurement,
]


def fake_benchmark_worker(
    _path: Path,
    _options: AnalysisOptions,
    _model_dir: Path,
    compute: ComputeMode,
    cancel: Event,
    batch_size: int = 1,
) -> ComputeMeasurement:
    if cancel.is_set():
        raise AppError("benchmark_cancelled", "Benchmark wurde abgebrochen.", 409)
    return ComputeMeasurement(
        compute=compute,
        initialization_seconds=0.01,
        warmup_seconds=0.02,
        measured_seconds=[0.01, 0.01],
        baseline_peak_bytes=128 * 1024 * 1024,
        worker_peak_bytes=256 * 1024 * 1024,
        model_ids=["fake-genre", "fake-mood"],
        batch_size=batch_size,
    )


def select_sample(
    tracks: Sequence[LibraryTrack],
    minimum_seconds: int = 60,
) -> LibraryTrack:
    eligible = [
        track
        for track in tracks
        if track.present
        and track.metadata.duration_seconds is not None
        and math.isfinite(track.metadata.duration_seconds)
        and track.metadata.duration_seconds >= minimum_seconds
    ]
    if not eligible:
        raise AppError(
            "benchmark_sample_missing",
            f"Kein lesbarer Titel mit mindestens {minimum_seconds} Sekunden gefunden.",
            409,
        )
    return min(
        eligible,
        key=lambda track: (track.metadata.duration_seconds or math.inf, track.relative_path),
    )


class BenchmarkRunner:
    def __init__(
        self,
        music_root: Path,
        model_dir: Path,
        *,
        worker: BenchmarkWorker = run_isolated_worker,
    ) -> None:
        self._music_root = music_root
        self._model_dir = model_dir
        self._worker = worker

    def run(
        self,
        sample: LibraryTrack,
        options: AnalysisOptions,
        compute_modes: Sequence[ComputeMode],
        cancel: Event,
        batch_sizes: Sequence[int] | None = None,
    ) -> list[ComputeMeasurement]:
        fixed_options = replace(options, max_audio_seconds=60)
        sample_path = self._music_root / sample.relative_path
        measurements: list[ComputeMeasurement] = []
        for compute in compute_modes:
            modes = batch_sizes if compute == "cuda" and batch_sizes else (1,)
            for batch_size in modes:
                if cancel.is_set():
                    return measurements
                measurements.append(
                    self._worker(
                        sample_path,
                        fixed_options,
                        self._model_dir,
                        compute,
                        cancel,
                        batch_size,
                    )
                )
        return measurements
