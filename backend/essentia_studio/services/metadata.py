from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import mutagen

from essentia_studio.domain.tracks import TrackMetadata

UNKNOWN_ARTIST = "Unbekannter Interpret"
TRACK_PREFIX = re.compile(r"^\s*\d{1,3}(?:[._-]\d+)?\s*[-_. ]+\s*")
TRACK_TOKEN = re.compile(r"^\d{1,3}(?:[._-]\d+)?$")

AudioLoader = Callable[[Path], Any]


def metadata_from_path(relative_path: Path) -> TrackMetadata:
    path = Path(relative_path)
    stem = path.stem.strip()
    parts = [part.strip() for part in stem.split(" - ") if part.strip()]
    album = path.parent.name if len(path.parts) >= 3 else None

    if len(parts) >= 3 and TRACK_TOKEN.fullmatch(parts[1]):
        return TrackMetadata(parts[0], " - ".join(parts[2:]), album, None, "filename")
    if len(parts) >= 2 and not TRACK_TOKEN.fullmatch(parts[0]):
        return TrackMetadata(parts[0], " - ".join(parts[1:]), album, None, "filename")

    clean_title = TRACK_PREFIX.sub("", stem).strip() or stem
    if len(path.parts) >= 3:
        return TrackMetadata(path.parts[-3], clean_title, album, None, "directory")
    return TrackMetadata(UNKNOWN_ARTIST, clean_title, None, None, "fallback")


class MetadataService:
    def __init__(self, audio_loader: AudioLoader | None = None) -> None:
        self._audio_loader = audio_loader or self._load_audio

    def read(self, path: Path, relative_path: str) -> TrackMetadata:
        fallback = metadata_from_path(Path(relative_path))
        try:
            audio = self._audio_loader(path)
        except Exception:
            return fallback
        if audio is None:
            return fallback

        tags = getattr(audio, "tags", None) or {}
        artist_values = self._values(tags, "artist")
        title_values = self._values(tags, "title")
        album_values = self._values(tags, "album")
        duration = self._duration(audio)
        has_embedded_identity = bool(artist_values or title_values or album_values)
        return TrackMetadata(
            artist="; ".join(artist_values) if artist_values else fallback.artist,
            title=title_values[0] if title_values else fallback.title,
            album=album_values[0] if album_values else fallback.album,
            duration_seconds=duration,
            source="embedded" if has_embedded_identity else fallback.source,
        )

    @staticmethod
    def _load_audio(path: Path):
        return mutagen.File(path, easy=True)

    @staticmethod
    def _values(tags: Mapping[str, Any], name: str) -> list[str]:
        raw = tags.get(name, [])
        values: Sequence[Any] = raw if isinstance(raw, (list, tuple)) else [raw]
        return [str(value).strip() for value in values if str(value).strip()]

    @staticmethod
    def _duration(audio: Any) -> float | None:
        value = getattr(getattr(audio, "info", None), "length", None)
        try:
            duration = float(value)
        except (TypeError, ValueError):
            return None
        return duration if duration > 0 and math.isfinite(duration) else None
