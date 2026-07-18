from collections.abc import Iterator
from pathlib import Path

from essentia_studio.domain.tracks import ScannedTrack, TrackFingerprint
from essentia_studio.services.metadata import MetadataService

SUPPORTED_EXTENSIONS = {
    ".aac",
    ".aif",
    ".aiff",
    ".ape",
    ".dsf",
    ".flac",
    ".m4a",
    ".m4b",
    ".mp+",
    ".mp3",
    ".mp4",
    ".mpc",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
    ".wv",
}


def scan_music_root(
    root: Path,
    metadata_service: MetadataService | None = None,
) -> Iterator[ScannedTrack]:
    resolved_root = root.resolve(strict=True)
    reader = metadata_service or MetadataService()
    scanned_tracks: list[ScannedTrack] = []

    for path in resolved_root.rglob("*"):
        extension = path.suffix.lower()
        if path.is_symlink() or not path.is_file() or extension not in SUPPORTED_EXTENSIONS:
            continue

        file_stat = path.stat()
        scanned_tracks.append(
            ScannedTrack(
                relative_path=(relative_path := path.relative_to(resolved_root).as_posix()),
                extension=extension,
                fingerprint=TrackFingerprint(
                    size=file_stat.st_size,
                    mtime_ns=file_stat.st_mtime_ns,
                ),
                metadata=reader.read(path, relative_path),
            )
        )

    yield from sorted(scanned_tracks, key=lambda track: track.relative_path)
