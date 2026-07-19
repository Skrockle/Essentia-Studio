from __future__ import annotations

import multiprocessing
import os
import sys
import time
from multiprocessing.connection import Connection
from pathlib import Path
from threading import Event

from essentia_studio.analysis.essentia_backend import EssentiaBackend
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult
from essentia_studio.domain.benchmarks import ComputeMeasurement, ComputeMode
from essentia_studio.errors import AppError


def run_isolated_worker(
    path: Path,
    options: AnalysisOptions,
    model_dir: Path,
    compute: ComputeMode,
    cancel: Event,
    batch_size: int = 1,
) -> ComputeMeasurement:
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker_entry,
        args=(send, str(path), options, str(model_dir), compute, batch_size),
        name=f"essentia-benchmark-{compute}",
    )
    process.start()
    send.close()
    try:
        while process.is_alive():
            if receive.poll(0.1):
                break
            if cancel.is_set():
                process.terminate()
                process.join(timeout=5)
                raise AppError("benchmark_cancelled", "Benchmark wurde abgebrochen.", 409)
        process.join(timeout=5)
        if not receive.poll():
            raise AppError(
                "benchmark_worker_failed",
                f"Der {compute.upper()}-Benchmark-Prozess wurde unerwartet beendet.",
                500,
            )
        payload = receive.recv()
    finally:
        receive.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)

    if isinstance(payload, ComputeMeasurement):
        return payload
    raise AppError(
        "benchmark_worker_failed",
        str(payload.get("error", "Benchmark-Prozess fehlgeschlagen.")),
        500,
    )


def _worker_entry(
    connection: Connection,
    path: str,
    options: AnalysisOptions,
    model_dir: str,
    compute: ComputeMode,
    batch_size: int,
) -> None:
    try:
        connection.send(_measure(Path(path), options, Path(model_dir), compute, batch_size))
    except BaseException as error:
        connection.send({"error": str(error)})
    finally:
        connection.close()


def _measure(
    path: Path,
    options: AnalysisOptions,
    model_dir: Path,
    compute: ComputeMode,
    batch_size: int,
) -> ComputeMeasurement:
    os.environ["CUDA_VISIBLE_DEVICES"] = "" if compute == "cpu" else os.environ.get(
        "CUDA_VISIBLE_DEVICES",
        "0",
    )
    baseline = _peak_rss_bytes()
    backend = EssentiaBackend(model_dir, "cuda" if compute == "cuda" else "cpu")

    started = time.perf_counter()
    backend.initialize()
    initialization_seconds = time.perf_counter() - started

    started = time.perf_counter()
    prepared = backend.prepare(path, options)
    warmup_result = _analyze_batch(backend, prepared, options, batch_size)[-1]
    warmup_seconds = time.perf_counter() - started

    measured_seconds: list[float] = []
    result = warmup_result
    for _ in range(2):
        started = time.perf_counter()
        result = _analyze_batch(backend, prepared, options, batch_size)[-1]
        measured_seconds.append(time.perf_counter() - started)

    peak = _peak_rss_bytes()
    return ComputeMeasurement(
        compute=compute,
        initialization_seconds=initialization_seconds,
        warmup_seconds=warmup_seconds,
        measured_seconds=measured_seconds,
        baseline_peak_bytes=baseline,
        worker_peak_bytes=max(peak - baseline, 1),
        model_ids=result.model_ids,
        batch_size=batch_size,
    )


def _analyze_batch(
    backend: EssentiaBackend,
    prepared: object,
    options: AnalysisOptions,
    batch_size: int,
) -> list[AnalysisResult]:
    return backend.analyze_prepared_batch([prepared] * batch_size, options)


def _peak_rss_bytes() -> int:
    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak if sys.platform == "darwin" else peak * 1024)
    except (ImportError, ValueError):
        return 0
