from datetime import datetime, timezone

from sqlalchemy import text

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.analysis import AnalysisResult, Prediction
from essentia_studio.domain.tag_labels import rewrite_legacy_genres
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint, TrackMetadata
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.tracks import TrackRepository


def test_rewrite_replaces_only_exact_model_derived_values() -> None:
    assert rewrite_legacy_genres(
        ["Funk / Soul; Contemporary R&B", "Manual; Value"],
        ["Funk / Soul---Contemporary R&B"],
    ) == ["Funk / Soul", "Contemporary R&B", "Manual; Value"]


def test_rewrite_deduplicates_hierarchical_values_case_insensitively() -> None:
    assert rewrite_legacy_genres(
        ["Electronic; House", "house", "Manual"],
        ["Electronic---House"],
    ) == ["Electronic", "House", "Manual"]


def test_reconcile_hierarchical_genres_is_idempotent_and_preserves_draft_state(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    tracks = TrackRepository(engine)
    results = ResultRepository(engine)
    scanned_track = ScannedTrack(
        "Artist/song.flac",
        ".flac",
        TrackFingerprint(size=10, mtime_ns=100),
        TrackMetadata("Artist", "Song", "Album", 180.0, "embedded"),
    )
    tracks.replace_scan([scanned_track], datetime(2026, 7, 17, tzinfo=timezone.utc))
    stored = results.save(
        tracks.get_by_path(scanned_track.relative_path),
        AnalysisResult(genres=[Prediction("Electronic---House", 0.9)]),
        ["Electronic; House"],
        [],
    )
    results.replace_draft(stored.id, ["Electronic; House", "Manual; Value"], None)
    results.update_selection({"mode": "ids", "ids": [stored.id]}, True)

    with engine.connect() as connection:
        selected_dirty_and_status = connection.execute(
            text(
                "SELECT selected, dirty, status FROM tag_drafts "
                "WHERE result_id = :result_id"
            ),
            {"result_id": stored.id},
        ).one()

    first_count = results.reconcile_hierarchical_genres()
    second_count = results.reconcile_hierarchical_genres()
    reconciled = results.get(stored.id)

    with engine.connect() as connection:
        final_selected_dirty_and_status = connection.execute(
            text(
                "SELECT selected, dirty, status FROM tag_drafts "
                "WHERE result_id = :result_id"
            ),
            {"result_id": stored.id},
        ).one()

    assert first_count == 1
    assert second_count == 0
    assert reconciled.draft.genres == ["Electronic", "House", "Manual; Value"]
    assert final_selected_dirty_and_status == selected_dirty_and_status
