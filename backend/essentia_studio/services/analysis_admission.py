from dataclasses import dataclass
from pathlib import Path

from essentia_studio.domain.analysis import AnalysisOptions
from essentia_studio.domain.tracks import LibraryTrack
from essentia_studio.repositories.tracks import TrackRepository
from essentia_studio.services.managed_tag_inventory import inventory_from_snapshot
from essentia_studio.services.path_safety import resolve_track_path
from essentia_studio.tags.registry import TagAdapterRegistry


@dataclass(frozen=True, slots=True)
class AnalysisWorkItem:
    relative_path: str
    enable_genres: bool
    enable_moods: bool


@dataclass(frozen=True, slots=True)
class AdmissionFailure:
    code: str
    relative_path: str


@dataclass(frozen=True, slots=True)
class AnalysisAdmission:
    items: list[AnalysisWorkItem]
    skipped_complete: list[str]
    failures: list[AdmissionFailure]


class AnalysisAdmissionService:
    def __init__(
        self,
        tracks: TrackRepository,
        tag_registry: TagAdapterRegistry,
        music_root: Path,
    ) -> None:
        self._tracks = tracks
        self._tag_registry = tag_registry
        self._music_root = music_root

    def prepare(
        self,
        tracks: list[LibraryTrack],
        requested: AnalysisOptions,
    ) -> AnalysisAdmission:
        items: list[AnalysisWorkItem] = []
        skipped_complete: list[str] = []
        failures: list[AdmissionFailure] = []
        for track in tracks:
            work_item = self._prepare_track(track, requested)
            if isinstance(work_item, AdmissionFailure):
                failures.append(work_item)
            elif work_item is None:
                skipped_complete.append(track.relative_path)
            else:
                items.append(work_item)
        return AnalysisAdmission(items, skipped_complete, failures)

    def _prepare_track(
        self,
        track: LibraryTrack,
        requested: AnalysisOptions,
    ) -> AnalysisWorkItem | AdmissionFailure | None:
        try:
            path = resolve_track_path(self._music_root, track.relative_path)
            snapshot = self._tag_registry.for_path(path).read(path)
            inventory = inventory_from_snapshot(snapshot)
            self._tracks.update_managed_tags(track.id, inventory)
        except Exception:
            return AdmissionFailure("managed_tags_unreadable", track.relative_path)

        enable_genres = requested.enable_genres and not inventory.genres
        enable_moods = requested.enable_moods and not inventory.moods
        if not enable_genres and not enable_moods:
            return None
        return AnalysisWorkItem(track.relative_path, enable_genres, enable_moods)
