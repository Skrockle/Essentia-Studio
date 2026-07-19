import json
from importlib.resources import files
from pathlib import Path


def test_model_manifest_contains_verifiable_sha256_values() -> None:
    manifest = json.loads(
        files("essentia_studio.analysis").joinpath("models.json").read_text(encoding="utf-8")
    )

    assert len(manifest) == 5
    assert all(len(model["sha256"]) == 64 for model in manifest)
    assert all(set(model["sha256"]) <= set("0123456789abcdef") for model in manifest)


def test_onnx_manifest_contains_only_native_models_and_metadata() -> None:
    manifest_path = Path("backend/essentia_studio/analysis/onnx-models.json")
    download_path = Path("backend/essentia_studio/analysis/onnx-download.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    downloads = json.loads(download_path.read_text(encoding="utf-8"))

    assert {model["name"] for model in manifest} == {
        "discogs-effnet-bsdynamic-1.onnx",
        "genre_discogs400-discogs-effnet-1.json",
        "mtg_jamendo_moodtheme-discogs-effnet-1.onnx",
        "mtg_jamendo_moodtheme-discogs-effnet-1.json",
    }
    assert downloads == manifest
    assert all(len(model["sha256"]) == 64 for model in manifest)
    assert not any(model["name"].endswith(".pb") for model in manifest)
