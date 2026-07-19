import hashlib
import json
import zipfile
from pathlib import Path

from scripts.download_models import download_models


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_download_models_installs_checksum_verified_archive(tmp_path: Path) -> None:
    models = {
        "embedding.pb": b"embedding-model",
        "genres.json": b'{"classes": ["Ambient"]}',
    }
    archive = tmp_path / "models.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, content in models.items():
            bundle.writestr(name, content)

    manifest = tmp_path / "models.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "name": name,
                    "url": "https://invalid.example/model",
                    "sha256": _digest(content),
                }
                for name, content in models.items()
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"

    download_models(
        manifest,
        output,
        archive_url=archive.as_uri(),
        archive_sha256=_digest(archive.read_bytes()),
    )

    assert {path.name: path.read_bytes() for path in output.iterdir()} == models


def test_production_images_use_the_verified_model_archive() -> None:
    archive_url = "https://oc-file.gozdzik.online/api/public/dl/_OlwyHdn/"
    archive_sha256 = "25878d4d36533b2ef6ac888f4479baa2477eac48bae0bdbea79a1bad79c41916"

    for dockerfile in ["Dockerfile", "Dockerfile.cuda"]:
        text = Path(dockerfile).read_text(encoding="utf-8")
        assert archive_url in text
        assert archive_sha256 in text
        assert "--archive-url" in text
        assert "--archive-sha256" in text


def test_cuda_onnx_image_downloads_its_native_manifest_without_archive() -> None:
    text = Path("Dockerfile.cuda-onnx").read_text(encoding="utf-8")

    assert "ESSENTIA_MODEL_ARCHIVE" not in text
    assert "--manifest /app/onnx-download.json" in text
    assert "cp /app/onnx-models.json /app/models/onnx-models.json" in text
    assert "--archive-url" not in text
    assert "--archive-sha256" not in text
