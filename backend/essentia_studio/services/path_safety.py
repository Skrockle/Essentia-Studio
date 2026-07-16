from pathlib import Path, PurePosixPath

from essentia_studio.errors import AppError


def resolve_track_path(root: Path, relative: str) -> Path:
    logical_path = PurePosixPath(relative)
    if logical_path.is_absolute() or ".." in logical_path.parts or not logical_path.parts:
        raise _invalid_track_path()

    resolved_root = root.resolve(strict=True)
    candidate = resolved_root.joinpath(*logical_path.parts).resolve(strict=True)
    if not candidate.is_relative_to(resolved_root):
        raise _invalid_track_path()
    return candidate


def _invalid_track_path() -> AppError:
    return AppError(
        "invalid_track_path",
        "Der Pfad liegt außerhalb des Musikverzeichnisses.",
        400,
    )
