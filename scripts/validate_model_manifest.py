"""Validate every model file in an image against its runtime manifest."""

import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(manifest_path: Path, model_dir: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    invalid = []
    for model in manifest:
        model_path = model_dir / model["name"]
        if not model_path.is_file() or sha256(model_path) != model["sha256"]:
            invalid.append(model["name"])
    if invalid:
        raise SystemExit(f"Model manifest validation failed: {', '.join(invalid)}")


if __name__ == "__main__":
    validate(Path(sys.argv[1]), Path(sys.argv[2]))
