from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import pytest

from essentia_studio.benchmark.runner import BenchmarkRunner, select_sample
from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.benchmarks import ComputeMeasurement
from essentia_studio.domain.tracks import LibraryTrack, TrackFingerprint, TrackMetadata
from essentia_studio.errors import AppError


def _track(path: str, duration: float | None, present: bool = True) -> LibraryTrack:
    return LibraryTrack(
        id=1,
        relative_path=path,
        extension=".flac",
        fingerprint=TrackFingerprint(10, 20),
        last_seen=datetime.now(timezone.utc),
        present=present,
        metadata=TrackMetadata("Artist", path, None, duration, "embedded"),
    )


def _measurement(compute: str) -> ComputeMeasurement:
    return ComputeMeasurement(
        compute=compute,
        initialization_seconds=0.5,
        warmup_seconds=2.5,
        measured_seconds=[2.0, 1.8],
        baseline_peak_bytes=100,
        worker_peak_bytes=500,
        model_ids=["genre", "mood"],
    )


def test_selects_shortest_track_meeting_minimum() -> None:
    selected = select_sample(
        [_track("short.flac", 59), _track("long.flac", 125), _track("best.flac", 61)],
        minimum_seconds=60,
    )

    assert selected.relative_path == "best.flac"


def test_sample_selection_rejects_missing_or_unknown_duration() -> None:
    with pytest.raises(AppError, match="60 Sekunden"):
        select_sample(
            [_track("missing.flac", 120, present=False), _track("unknown.flac", None)],
            minimum_seconds=60,
        )


def test_runner_uses_fixed_sample_and_requested_compute_modes(tmp_path: Path) -> None:
    calls = []

    def worker(path, options, model_dir, compute, cancel):
        calls.append((path, options, model_dir, compute, cancel))
        return _measurement(compute)

    runner = BenchmarkRunner(tmp_path / "music", tmp_path / "models", worker=worker)
    sample = _track("Artist/song.flac", 180)
    cancel = Event()

    measurements = runner.run(
        sample,
        AnalysisOptions(max_audio_seconds=300),
        ["cpu", "cuda"],
        cancel,
    )

    assert [measurement.compute for measurement in measurements] == ["cpu", "cuda"]
    assert all(call[1].max_audio_seconds == 60 for call in calls)
    assert all(call[0] == tmp_path / "music" / "Artist/song.flac" for call in calls)


def test_cancellation_stops_before_next_compute_mode(tmp_path: Path) -> None:
    cancel = Event()
    calls = []

    def worker(_path, _options, _model_dir, compute, _cancel):
        calls.append(compute)
        cancel.set()
        return _measurement(compute)

    runner = BenchmarkRunner(tmp_path, tmp_path, worker=worker)
    measurements = runner.run(_track("song.flac", 60), AnalysisOptions(), ["cpu", "cuda"], cancel)

    assert [measurement.compute for measurement in measurements] == ["cpu"]
    assert calls == ["cpu"]
