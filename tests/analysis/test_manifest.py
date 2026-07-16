import json
from importlib.resources import files


def test_model_manifest_contains_verifiable_sha256_values() -> None:
    manifest = json.loads(
        files("essentia_studio.analysis").joinpath("models.json").read_text(encoding="utf-8")
    )

    assert len(manifest) == 5
    assert all(len(model["sha256"]) == 64 for model in manifest)
    assert all(set(model["sha256"]) <= set("0123456789abcdef") for model in manifest)
