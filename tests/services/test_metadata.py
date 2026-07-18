from pathlib import Path

from essentia_studio.domain.tracks import TrackMetadata
from essentia_studio.services.metadata import MetadataService, metadata_from_path


def test_filename_metadata_uses_artist_track_number_and_title() -> None:
    metadata = metadata_from_path(
        Path("Bastille/Doom Days/Bastille - 01 - Quarter Past Midnight.flac")
    )

    assert metadata == TrackMetadata(
        artist="Bastille",
        title="Quarter Past Midnight",
        album="Doom Days",
        duration_seconds=None,
        source="filename",
    )


def test_directory_metadata_uses_artist_album_and_clean_filename() -> None:
    metadata = metadata_from_path(Path("Underworld/Second Toughest/08 - Stagger.flac"))

    assert metadata == TrackMetadata(
        artist="Underworld",
        title="Stagger",
        album="Second Toughest",
        duration_seconds=None,
        source="directory",
    )


def test_loose_file_uses_safe_fallback() -> None:
    metadata = metadata_from_path(Path("loose-file.wav"))

    assert metadata == TrackMetadata(
        artist="Unbekannter Interpret",
        title="loose-file",
        album=None,
        duration_seconds=None,
        source="fallback",
    )


def test_single_parent_directory_is_used_as_artist() -> None:
    metadata = metadata_from_path(Path("Artist/song.flac"))

    assert metadata.artist == "Artist"
    assert metadata.title == "song"
    assert metadata.album is None
    assert metadata.source == "directory"


class FakeInfo:
    length = 185.25


class FakeAudio:
    info = FakeInfo()

    def __init__(self) -> None:
        self.tags = {
            "artist": ["Correct Artist", "Guest Artist"],
            "title": ["Correct Title"],
            "album": ["Correct Album"],
        }


def test_embedded_tags_override_path_and_include_duration(tmp_path: Path) -> None:
    path = tmp_path / "Wrong" / "Wrong Album" / "wrong.mp3"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"audio")
    service = MetadataService(audio_loader=lambda _path: FakeAudio())

    metadata = service.read(path, "Wrong/Wrong Album/wrong.mp3")

    assert metadata == TrackMetadata(
        artist="Correct Artist; Guest Artist",
        title="Correct Title",
        album="Correct Album",
        duration_seconds=185.25,
        source="embedded",
    )


def test_malformed_audio_uses_path_metadata() -> None:
    def broken_loader(_path: Path):
        raise ValueError("broken tags")

    metadata = MetadataService(audio_loader=broken_loader).read(
        Path("/music/Artist/Album/03 - Song.flac"),
        "Artist/Album/03 - Song.flac",
    )

    assert metadata.artist == "Artist"
    assert metadata.title == "Song"
    assert metadata.source == "directory"
