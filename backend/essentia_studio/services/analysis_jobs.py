from dataclasses import replace
from pathlib import Path

from essentia_studio.analysis.protocol import AnalysisBackend
from essentia_studio.domain.analysis import AnalysisOptions, StoredAnalysis
from essentia_studio.domain.tracks import TrackFingerprint
from essentia_studio.errors import AppError
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.labels import format_genre, format_mood, normalize_tags
from essentia_studio.services.path_safety import resolve_track_path


class AnalysisJobService:
    def __init__(
        self,
        backend: AnalysisBackend,
        results: ResultRepository,
        tracks: TrackRepository,
        music_root: Path,
    ) -> None:
        self._backend = backend
        self._results = results
        self._tracks = tracks
        self._music_root = music_root

    def process(
        self,
        relative_path: str,
        options: AnalysisOptions,
        job_id: str | None = None,
    ) -> StoredAnalysis:
        track = self._tracks.get_by_path(relative_path)
        path = resolve_track_path(self._music_root, relative_path)
        before = path.stat()
        result = self._backend.analyze(path, options)
        after = path.stat()
        fingerprint = TrackFingerprint(before.st_size, before.st_mtime_ns)
        if fingerprint != TrackFingerprint(after.st_size, after.st_mtime_ns):
            raise AppError(
                "track_changed_during_analysis",
                "Der Titel wurde während der Analyse geändert und nicht übernommen.",
                409,
            )
        genres = normalize_tags([format_genre(value.label) for value in result.genres])
        moods = normalize_tags([format_mood(value.label) for value in result.moods])
        return self._results.save(
            replace(track, fingerprint=fingerprint),
            result,
            genres,
            moods,
            job_id,
        )
