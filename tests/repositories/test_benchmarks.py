from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.benchmarks import ComputeMeasurement, snapshot_hash
from essentia_studio.repositories.benchmarks import BenchmarkRepository


def _repository(tmp_path):
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    return BenchmarkRepository(engine)


def test_snapshot_hash_is_stable_for_equivalent_mappings() -> None:
    assert snapshot_hash({"cpu": 2, "models": ["a"], "ram": 4}) == snapshot_hash(
        {"ram": 4, "models": ["a"], "cpu": 2}
    )


def test_only_matching_completed_environment_snapshot_is_current(tmp_path) -> None:
    repository = _repository(tmp_path)
    old = repository.create(
        snapshot={"memory": 4_000, "cpus": 2},
        sample_track_id=None,
        sample_relative_path="Artist/song.flac",
    )
    repository.finish(old.id, recommended_workers=2)

    assert repository.current_for(snapshot_hash({"memory": 8_000, "cpus": 4})) is None
    assert repository.current_for(old.snapshot_hash).id == old.id


def test_persists_measurements_and_failed_runs(tmp_path) -> None:
    repository = _repository(tmp_path)
    run = repository.create(
        snapshot={"image_variant": "cpu"},
        sample_track_id=None,
        sample_relative_path="song.flac",
    )
    repository.record_measurement(
        run.id,
        ComputeMeasurement(
            compute="cpu",
            initialization_seconds=1.2,
            warmup_seconds=2.1,
            measured_seconds=[2.0, 1.8],
            baseline_peak_bytes=300,
            worker_peak_bytes=800,
            model_ids=["genre", "mood"],
        ),
    )
    finished = repository.finish(run.id, recommended_workers=3)

    assert finished.recommended_workers == 3
    assert finished.measurements[0].measured_seconds == [2.0, 1.8]
    assert repository.list()[0].id == run.id

    failed = repository.create(
        snapshot={"image_variant": "cpu", "version": 2},
        sample_track_id=None,
        sample_relative_path="broken.flac",
    )
    assert repository.fail(failed.id, "Decoder fehlgeschlagen").status == "failed"
