from dataclasses import replace
from pathlib import Path
from threading import Event

from essentia_studio.analysis.protocol import AnalysisBackend
from essentia_studio.domain.analysis import AnalysisOptions, StoredAnalysis
from essentia_studio.domain.tracks import TrackFingerprint
from essentia_studio.errors import AppError
from essentia_studio.repositories.results import ResultRepository
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.labels import format_mood_label, normalize_tags, split_genre_label
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
        cancellation: Event | None = None,
    ) -> StoredAnalysis:
        if cancellation is not None and cancellation.is_set():
            raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
        track = self._tracks.get_by_path(relative_path)
        path = resolve_track_path(self._music_root, relative_path)
        before = path.stat()
        result = self._backend.analyze(path, options, cancellation)
        if cancellation is not None and cancellation.is_set():
            raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
        after = path.stat()
        fingerprint = TrackFingerprint(before.st_size, before.st_mtime_ns)
        if fingerprint != TrackFingerprint(after.st_size, after.st_mtime_ns):
            raise AppError(
                "track_changed_during_analysis",
                "Der Titel wurde während der Analyse geändert und nicht übernommen.",
                409,
            )
        if cancellation is not None and cancellation.is_set():
            raise AppError("analysis_cancelled", "Die Analyse wurde abgebrochen.", 409)
        genres = normalize_tags(
            [
                genre
                for prediction in result.genres
                if prediction.accepted
                for genre in split_genre_label(prediction.label)
            ]
        )[: options.genre_count]
        moods = normalize_tags([format_mood_label(value.label) for value in result.moods])
        return self._results.save(
            replace(track, fingerprint=fingerprint),
            result,
            genres,
            moods,
            job_id,
        )
