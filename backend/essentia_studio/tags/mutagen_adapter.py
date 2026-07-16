from pathlib import Path
from typing import Any

import mutagen
from mutagen.id3 import COMM, TCON

from essentia_studio.tags.protocol import DesiredTags, ManagedTagSnapshot

VORBIS_EXTENSIONS = {".flac", ".ogg", ".oga", ".opus"}
ID3_EXTENSIONS = {".mp3", ".aiff", ".aif", ".wav", ".dsf"}
MP4_EXTENSIONS = {".m4a", ".m4b", ".mp4", ".aac"}
ASF_EXTENSIONS = {".wma", ".asf"}
APE_EXTENSIONS = {".ape", ".wv", ".mpc"}


class MutagenTagAdapter:
    """Read and modify only the fields managed by Essentia Studio."""

    def read(self, path: Path) -> ManagedTagSnapshot:
        audio = self._open(path)
        family = self._family(path)
        return ManagedTagSnapshot(family, self._read_fields(audio, family))

    def write(self, path: Path, desired: DesiredTags, overwrite: bool) -> None:
        audio = self._open(path)
        family = self._family(path)
        current = self._read_fields(audio, family)
        genres = self._merged(current["genres"], desired.genres, overwrite)
        moods = self._merged(current["moods"], desired.moods, overwrite)
        values = {
            "genres": genres,
            "moods": moods,
            "genre_confidence": [desired.genre_confidence]
            if desired.genre_confidence
            else current["genre_confidence"],
            "mood_confidence": [desired.mood_confidence]
            if desired.mood_confidence
            else current["mood_confidence"],
        }
        self._replace_fields(audio, family, values)
        audio.save()

    def restore(self, path: Path, snapshot: ManagedTagSnapshot) -> None:
        audio = self._open(path)
        if self._family(path) != snapshot.format:
            raise ValueError("Tag snapshot does not match the audio format")
        self._replace_fields(audio, snapshot.format, snapshot.fields)
        audio.save()

    @staticmethod
    def _open(path: Path):
        audio = mutagen.File(path, easy=False)
        if audio is None:
            raise ValueError(f"Unsupported audio format: {path.suffix}")
        if audio.tags is None:
            audio.add_tags()
        return audio

    @staticmethod
    def _family(path: Path) -> str:
        extension = path.suffix.casefold()
        if extension in VORBIS_EXTENSIONS:
            return "vorbis"
        if extension in ID3_EXTENSIONS:
            return "id3"
        if extension in MP4_EXTENSIONS:
            return "mp4"
        if extension in ASF_EXTENSIONS:
            return "asf"
        if extension in APE_EXTENSIONS:
            return "apev2"
        raise ValueError(f"Unsupported audio format: {extension}")

    def _read_fields(self, audio, family: str) -> dict[str, list[str]]:
        tags = audio.tags
        if family == "id3":
            return {
                "genres": [str(value) for frame in tags.getall("TCON") for value in frame.text],
                "moods": self._id3_comments(tags, "Essentia Mood"),
                "genre_confidence": self._id3_comments(tags, "Essentia Genre"),
                "mood_confidence": self._id3_comments(tags, "Essentia Mood Confidence"),
            }
        mapping = self._mapping(family)
        return {
            logical: self._string_values(tags.get(raw_key, []), family)
            for logical, raw_key in mapping.items()
        }

    def _replace_fields(
        self,
        audio,
        family: str,
        fields: dict[str, Any],
    ) -> None:
        normalized = {name: list(values or []) for name, values in fields.items()}
        if family == "id3":
            self._replace_id3(audio.tags, normalized)
            return
        for logical, raw_key in self._mapping(family).items():
            values = normalized.get(logical, [])
            if raw_key in audio.tags:
                del audio.tags[raw_key]
            if values:
                audio.tags[raw_key] = self._encode_values(values, family, raw_key)

    @staticmethod
    def _mapping(family: str) -> dict[str, str]:
        return {
            "vorbis": {
                "genres": "GENRE",
                "moods": "MOOD",
                "genre_confidence": "ESSENTIA_GENRE",
                "mood_confidence": "ESSENTIA_MOOD",
            },
            "mp4": {
                "genres": "\xa9gen",
                "moods": "----:com.apple.iTunes:MOOD",
                "genre_confidence": "----:com.apple.iTunes:ESSENTIA_GENRE",
                "mood_confidence": "----:com.apple.iTunes:ESSENTIA_MOOD",
            },
            "asf": {
                "genres": "WM/Genre",
                "moods": "WM/Mood",
                "genre_confidence": "Essentia/Genre",
                "mood_confidence": "Essentia/Mood",
            },
            "apev2": {
                "genres": "Genre",
                "moods": "Mood",
                "genre_confidence": "Essentia Genre",
                "mood_confidence": "Essentia Mood",
            },
        }[family]

    @staticmethod
    def _id3_comments(tags, description: str) -> list[str]:
        return [
            str(value)
            for frame in tags.getall("COMM")
            if frame.desc == description and frame.lang == "eng"
            for value in frame.text
        ]

    @staticmethod
    def _replace_id3(tags, fields: dict[str, list[str]]) -> None:
        tags.delall("TCON")
        if fields.get("genres"):
            tags.add(TCON(encoding=3, text=fields["genres"]))
        comments = {
            "moods": "Essentia Mood",
            "genre_confidence": "Essentia Genre",
            "mood_confidence": "Essentia Mood Confidence",
        }
        for logical, description in comments.items():
            for frame in list(tags.getall("COMM")):
                if frame.desc == description and frame.lang == "eng":
                    tags.delall(frame.HashKey)
            if fields.get(logical):
                tags.add(
                    COMM(
                        encoding=3,
                        lang="eng",
                        desc=description,
                        text=fields[logical],
                    )
                )

    @staticmethod
    def _string_values(value: Any, family: str) -> list[str]:
        if value is None:
            return []
        values = value if isinstance(value, (list, tuple)) else [value]
        decoded: list[str] = []
        for item in values:
            raw = getattr(item, "value", item)
            if isinstance(raw, bytes):
                decoded.append(raw.decode("utf-8"))
            else:
                decoded.append(str(raw))
        return decoded

    @staticmethod
    def _encode_values(values: list[str], family: str, raw_key: str):
        if family == "mp4" and raw_key.startswith("----:"):
            return [value.encode("utf-8") for value in values]
        return values

    @staticmethod
    def _merged(existing: list[str], desired: list[str], overwrite: bool) -> list[str]:
        if overwrite:
            return desired
        merged = list(existing)
        seen = {value.casefold() for value in merged}
        for value in desired:
            if value.casefold() not in seen:
                merged.append(value)
                seen.add(value.casefold())
        return merged
