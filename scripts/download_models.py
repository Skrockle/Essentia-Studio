"""Download and checksum-verify the pinned Essentia model inventory."""

import argparse
import hashlib
import json
import os
import tempfile
import time
import urllib.request
from pathlib import Path

DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_ATTEMPTS = 3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_models(manifest_path: Path, output: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    for model in manifest:
        destination = output / model["name"]
        if destination.is_file() and sha256(destination) == model["sha256"]:
            print(f"model ready: {destination.name} (cached)", flush=True)
            continue
        print(f"downloading model: {destination.name}", flush=True)
        _download_with_retries(model["url"], model["sha256"], destination)
        print(f"model ready: {destination.name}", flush=True)


def _download_with_retries(url: str, expected: str, destination: Path) -> None:
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            _download_verified(url, expected, destination)
            return
        except (OSError, TimeoutError) as error:
            if attempt == DOWNLOAD_ATTEMPTS:
                raise
            print(
                f"download failed for {destination.name}: {error}; "
                f"retrying ({attempt}/{DOWNLOAD_ATTEMPTS})",
                flush=True,
            )
            time.sleep(attempt)


def _download_verified(url: str, expected: str, destination: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    digest = hashlib.sha256()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Essentia-Studio"})
        with os.fdopen(descriptor, "wb") as output, urllib.request.urlopen(
            request,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        ) as response:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())
        if digest.hexdigest() != expected:
            raise ValueError(f"Checksum mismatch for {destination.name}")
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    download_models(arguments.manifest, arguments.output)


if __name__ == "__main__":
    main()
