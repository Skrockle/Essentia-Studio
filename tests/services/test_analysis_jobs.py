from datetime import datetime, timezone

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult, Prediction
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.analysis_jobs import AnalysisJobService


class FakeAnalysisBackend:
    def __init__(self, result: AnalysisResult | None = None) -> None:
        self._result = result or AnalysisResult(
            genres=[Prediction("Electronic---House", 0.9)],
            moods=[Prediction("moodtheme---happy", 0.8)],
            model_ids=["fake-genre", "fake-mood"],
        )

    def analyze(self, _path, _options) -> AnalysisResult:
        return self._result


def test_analysis_persists_draft_without_changing_audio(tmp_path) -> None:
    music_root = tmp_path / "music"
    track_path = music_root / "Artist" / "song.flac"
    track_path.parent.mkdir(parents=True)
    track_path.write_bytes(b"unchanged-audio")
    stat = track_path.stat()
    fingerprint = TrackFingerprint(stat.st_size, stat.st_mtime_ns)

    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    tracks = TrackRepository(engine)
    tracks.replace_scan(
        [ScannedTrack("Artist/song.flac", ".flac", fingerprint)],
        datetime.now(timezone.utc),
    )
    results = ResultRepository(engine)
    service = AnalysisJobService(FakeAnalysisBackend(), results, tracks, music_root)

    stored = service.process("Artist/song.flac", AnalysisOptions())

    assert stored.draft.genres == ["Electronic", "House"]
    assert stored.draft.moods == ["Happy"]
    assert track_path.read_bytes() == b"unchanged-audio"
    assert results.get_by_path("Artist/song.flac") == stored


def test_analysis_limits_visible_genres_and_excludes_rejected_candidate(tmp_path) -> None:
    music_root = tmp_path / "music"
    track_path = music_root / "Artist" / "song.flac"
    track_path.parent.mkdir(parents=True)
    track_path.write_bytes(b"unchanged-audio")
    stat = track_path.stat()

    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    tracks = TrackRepository(engine)
    tracks.replace_scan(
        [
            ScannedTrack(
                "Artist/song.flac",
                ".flac",
                TrackFingerprint(stat.st_size, stat.st_mtime_ns),
            )
        ],
        datetime.now(timezone.utc),
    )
    result = AnalysisResult(
        genres=[
            Prediction("Rock---Alternative Rock", 0.9),
            Prediction("Electronic---House", 0.8),
            Prediction("Hip Hop---Cloud Rap", 0.1, accepted=False),
        ],
        moods=[],
        model_ids=["fake-genre"],
    )
    service = AnalysisJobService(
        FakeAnalysisBackend(result),
        ResultRepository(engine),
        tracks,
        music_root,
    )

    stored = service.process("Artist/song.flac", AnalysisOptions(genre_count=3))

    assert stored.draft.genres == ["Rock", "Alternative Rock", "Electronic"]
    assert stored.result.genres[-1].accepted is False


def test_analysis_keeps_rejected_candidate_out_of_empty_draft(tmp_path) -> None:
    music_root = tmp_path / "music"
    track_path = music_root / "Artist" / "song.flac"
    track_path.parent.mkdir(parents=True)
    track_path.write_bytes(b"unchanged-audio")
    stat = track_path.stat()

    engine = create_sqlite_engine(tmp_path / "app.db")
    apply_migrations(engine)
    tracks = TrackRepository(engine)
    tracks.replace_scan(
        [
            ScannedTrack(
                "Artist/song.flac",
                ".flac",
                TrackFingerprint(stat.st_size, stat.st_mtime_ns),
            )
        ],
        datetime.now(timezone.utc),
    )
    result = AnalysisResult(
        genres=[Prediction("Rock---Alternative Rock", 0.11, accepted=False)],
        moods=[],
        model_ids=["fake-genre"],
    )
    service = AnalysisJobService(
        FakeAnalysisBackend(result),
        ResultRepository(engine),
        tracks,
        music_root,
    )

    stored = service.process("Artist/song.flac", AnalysisOptions(genre_count=3))

    assert stored.draft.genres == []
    assert stored.result.genres == result.genres
