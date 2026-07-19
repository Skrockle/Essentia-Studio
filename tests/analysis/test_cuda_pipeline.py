from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock

import pytest

from essentia_studio.analysis.cuda_pipeline import CudaInferencePipeline, CudaPipelineSettings
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult


def test_pipeline_settings_allow_only_supported_micro_batches() -> None:
    for batch_size in (1, 2, 4, 8):
        settings = CudaPipelineSettings(cpu_workers=2, batch_size=batch_size, queue_size=8)
        assert settings.batch_size == batch_size

    with pytest.raises(ValueError, match="Batchgröße"):
        CudaPipelineSettings(cpu_workers=2, batch_size=3, queue_size=8)


def test_pipeline_batches_requests_and_initializes_inference_once(tmp_path: Path) -> None:
    prepared: list[str] = []
    batches: list[list[str]] = []
    initialized = 0

    def prepare(path: Path, _options: AnalysisOptions) -> str:
        prepared.append(path.name)
        return path.name

    def infer(batch: list[str], _options: AnalysisOptions) -> list[AnalysisResult]:
        nonlocal initialized
        initialized += 1
        batches.append(batch)
        return [AnalysisResult(model_ids=[name]) for name in batch]

    pipeline = CudaInferencePipeline(
        CudaPipelineSettings(cpu_workers=2, batch_size=2, queue_size=4),
        prepare=prepare,
        infer=infer,
    )
    try:
        with ThreadPoolExecutor(max_workers=3) as callers:
            futures = [
                callers.submit(
                    pipeline.analyze,
                    tmp_path / f"song-{index}.flac",
                    AnalysisOptions(),
                )
                for index in range(3)
            ]
            results = [future.result() for future in futures]
    finally:
        pipeline.close()

    assert set(prepared) == {"song-0.flac", "song-1.flac", "song-2.flac"}
    assert [result.model_ids for result in results] == [
        ["song-0.flac"],
        ["song-1.flac"],
        ["song-2.flac"],
    ]
    assert sorted(map(len, batches)) == [1, 2]
    assert initialized == 2


def test_pipeline_cancellation_does_not_submit_cancelled_request(tmp_path: Path) -> None:
    submitted: list[list[str]] = []

    def prepare(path: Path, _options: AnalysisOptions) -> str:
        return path.name

    def infer(batch: list[str], _options: AnalysisOptions) -> list[AnalysisResult]:
        submitted.append(batch)
        return [AnalysisResult(model_ids=[name]) for name in batch]

    pipeline = CudaInferencePipeline(
        CudaPipelineSettings(cpu_workers=1, batch_size=1, queue_size=1),
        prepare=prepare,
        infer=infer,
    )
    try:
        cancellation = Event()
        cancellation.set()
        with pytest.raises(Exception, match="abgebrochen"):
            pipeline.analyze(tmp_path / "cancelled.flac", AnalysisOptions(), cancellation)
        assert submitted == []
    finally:
        pipeline.close()


def test_cpu_preparation_capacity_is_independent_from_queue_size(tmp_path: Path) -> None:
    started: list[str] = []
    started_lock = Lock()
    both_started = Event()
    release_preparation = Event()

    def prepare(path: Path, _options: AnalysisOptions) -> str:
        with started_lock:
            started.append(path.name)
            if len(started) == 2:
                both_started.set()
        release_preparation.wait(timeout=2)
        return path.name

    def infer(batch: list[str], _options: AnalysisOptions) -> list[AnalysisResult]:
        return [AnalysisResult(model_ids=[name]) for name in batch]

    pipeline = CudaInferencePipeline(
        CudaPipelineSettings(cpu_workers=2, batch_size=1, queue_size=1),
        prepare=prepare,
        infer=infer,
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as callers:
            futures = [
                callers.submit(
                    pipeline.analyze,
                    tmp_path / f"song-{index}.flac",
                    AnalysisOptions(),
                )
                for index in range(2)
            ]
            assert both_started.wait(timeout=1)
            release_preparation.set()
            assert [future.result(timeout=2).model_ids for future in futures] == [
                ["song-0.flac"],
                ["song-1.flac"],
            ]
    finally:
        release_preparation.set()
        pipeline.close()
