import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeValidation:
    code: str
    message: str


def validate_runtime(
    model_dir: Path,
    music_root: Path,
    data_dir: Path,
    manifest_path: Path | None = None,
) -> RuntimeValidation:
    manifest_file = manifest_path or Path("/app/models.json")
    if not manifest_file.is_file():
        return RuntimeValidation("manifest_missing", "Model manifest is missing")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    missing = [item["name"] for item in manifest if not (model_dir / item["name"]).is_file()]
    if missing:
        return RuntimeValidation("models_missing", f"Missing models: {', '.join(missing)}")
    invalid = [
        item["name"]
        for item in manifest
        if item.get("sha256") and _sha256(model_dir / item["name"]) != item["sha256"]
    ]
    if invalid:
        return RuntimeValidation(
            "models_invalid",
            f"Model checksum mismatch: {', '.join(invalid)}",
        )
    if not music_root.is_dir() or not os.access(music_root, os.R_OK):
        return RuntimeValidation("music_mount_unavailable", "Music mount is not readable")
    if not data_dir.is_dir() or not os.access(data_dir, os.W_OK):
        return RuntimeValidation("data_mount_unavailable", "Data mount is not writable")
    return RuntimeValidation("ready", "Runtime is ready")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(command: list[str] | None = None) -> int:
    model_dir = Path(os.environ.get("ESSENTIA_MODEL_DIR", "/app/models"))
    music_root = Path(os.environ.get("ESSENTIA_MUSIC_ROOT", "/music"))
    data_dir = Path(os.environ.get("ESSENTIA_DATA_DIR", "/data"))
    manifest = Path(
        os.environ.get(
            "ESSENTIA_MODEL_MANIFEST",
            "/app/models.json",
        )
    )
    result = validate_runtime(model_dir, music_root, data_dir, manifest)
    print(json.dumps(asdict(result)), flush=True)
    if result.code != "ready":
        return 1
    arguments = command if command is not None else sys.argv[1:]
    if not arguments:
        return 0
    os.execvp(arguments[0], arguments)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
