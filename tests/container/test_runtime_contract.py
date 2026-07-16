import json
from pathlib import Path

from docker.entrypoint import validate_runtime


def test_model_manifest_has_sha256_for_every_file() -> None:
    manifest = json.loads(
        Path("backend/essentia_studio/analysis/models.json").read_text()
    )

    assert len(manifest) == 5
    assert all(len(item["sha256"]) == 64 for item in manifest)
    assert all(item["url"].startswith("https://") for item in manifest)


def test_entrypoint_rejects_missing_models(tmp_path) -> None:
    manifest = tmp_path / "models.json"
    manifest.write_text(
        json.dumps([{"name": "missing.pb"}]),
        encoding="utf-8",
    )

    result = validate_runtime(tmp_path, tmp_path, tmp_path, manifest)

    assert result.code == "models_missing"


def test_entrypoint_rejects_model_with_wrong_checksum(tmp_path) -> None:
    model = tmp_path / "model.pb"
    model.write_bytes(b"corrupted")
    manifest = tmp_path / "models.json"
    manifest.write_text(
        json.dumps([{"name": model.name, "sha256": "0" * 64}]),
        encoding="utf-8",
    )

    result = validate_runtime(tmp_path, tmp_path, tmp_path, manifest)

    assert result.code == "models_invalid"


def test_production_images_keep_application_files_read_only() -> None:
    for dockerfile in ["Dockerfile", "Dockerfile.cuda"]:
        text = Path(dockerfile).read_text(encoding="utf-8")
        assert "chmod -R a+rX,a-w /app" in text
        assert "chown -R app:app /app" not in text
