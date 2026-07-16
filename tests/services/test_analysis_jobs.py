from datetime import datetime, timezone

from essentia_studio.db.engine import create_sqlite_engine
from essentia_studio.db.migrate import apply_migrations
from essentia_studio.domain.analysis import AnalysisOptions, AnalysisResult, Prediction
from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.analysis_jobs import AnalysisJobService


class FakeAnalysisBackend:
    def analyze(self, _path, _options) -> AnalysisResult:
        return AnalysisResult(
            genres=[Prediction("Electronic---House", 0.9)],
            moods=[Prediction("moodtheme---happy", 0.8)],
            model_ids=["fake-genre", "fake-mood"],
        )


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

    assert stored.draft.genres == ["Electronic; House"]
    assert stored.draft.moods == ["Happy"]
    assert track_path.read_bytes() == b"unchanged-audio"
    assert results.get_by_path("Artist/song.flac") == stored
