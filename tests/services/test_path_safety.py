import pytest

from essentia_studio.errors import AppError
from essentia_studio.services.path_safety import resolve_track_path


def test_resolve_track_path_rejects_parent_escape(tmp_path) -> None:
    root = tmp_path / "music"
    root.mkdir()

    with pytest.raises(AppError, match="Musikverzeichnis"):
        resolve_track_path(root, "../outside.flac")


def test_resolve_track_path_accepts_nested_relative_path(tmp_path) -> None:
    root = tmp_path / "music"
    track = root / "Artist" / "Album" / "song.flac"
    track.parent.mkdir(parents=True)
    track.touch()

    assert resolve_track_path(root, "Artist/Album/song.flac") == track.resolve()


def test_resolve_track_path_rejects_symlink_escape(tmp_path) -> None:
    root = tmp_path / "music"
    root.mkdir()
    outside = tmp_path / "outside.flac"
    outside.touch()
    (root / "linked.flac").symlink_to(outside)

    with pytest.raises(AppError, match="Musikverzeichnis"):
        resolve_track_path(root, "linked.flac")


def test_resolve_track_path_rejects_absolute_path(tmp_path) -> None:
    root = tmp_path / "music"
    root.mkdir()

    with pytest.raises(AppError, match="Musikverzeichnis"):
        resolve_track_path(root, "/etc/passwd")
