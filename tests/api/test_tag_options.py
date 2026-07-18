import json

from fastapi.testclient import TestClient

from essentia_studio.config import RuntimeConfig
from essentia_studio.main import create_app

GENRE_CATALOG = "genre_discogs400-discogs-effnet-1.json"
MOOD_CATALOG = "mtg_jamendo_moodtheme-discogs-effnet-1.json"


def create_test_config(tmp_path, model_dir) -> RuntimeConfig:
    music_root = tmp_path / "music"
    data_dir = tmp_path / "data"
    music_root.mkdir()
    data_dir.mkdir()
    return RuntimeConfig.from_env(
        {
            "ESSENTIA_MUSIC_ROOT": str(music_root),
            "ESSENTIA_DATA_DIR": str(data_dir),
            "ESSENTIA_MODEL_DIR": str(model_dir),
            "ESSENTIA_FRONTEND_DIR": str(tmp_path / "missing-dist"),
            "ESSENTIA_ANALYSIS_BACKEND": "fake",
        }
    )


def write_catalog(model_dir, catalog_name: str, classes: list[str]) -> None:
    (model_dir / catalog_name).write_text(
        json.dumps({"classes": classes}), encoding="utf-8"
    )


def test_tag_options_returns_normalized_model_labels(tmp_path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    write_catalog(model_dir, GENRE_CATALOG, ["Funk / Soul---Contemporary R&B"])
    write_catalog(model_dir, MOOD_CATALOG, ["moodtheme---happy"])

    with TestClient(create_app(create_test_config(tmp_path, model_dir))) as client:
        response = client.get("/api/tag-options")

    assert response.status_code == 200
    assert response.json() == {
        "genres": ["Contemporary R&B", "Funk / Soul"],
        "moods": ["Happy"],
    }


def test_tag_options_uses_the_standard_error_envelope_for_missing_metadata(tmp_path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    write_catalog(model_dir, MOOD_CATALOG, ["moodtheme---happy"])

    with TestClient(create_app(create_test_config(tmp_path, model_dir))) as client:
        response = client.get("/api/tag-options")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "tag_catalog_unavailable",
            "message": (
                "Der Tag-Katalog „genre_discogs400-discogs-effnet-1.json“ ist nicht verfügbar."
            ),
            "details": {},
        }
    }


def test_tag_options_uses_the_standard_error_envelope_for_invalid_utf8(tmp_path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / GENRE_CATALOG).write_bytes(b'{"classes": ["\xff"]}')
    write_catalog(model_dir, MOOD_CATALOG, ["moodtheme---happy"])

    with TestClient(create_app(create_test_config(tmp_path, model_dir))) as client:
        response = client.get("/api/tag-options")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "tag_catalog_unavailable",
            "message": (
                "Der Tag-Katalog „genre_discogs400-discogs-effnet-1.json“ "
                "ist nicht verfügbar."
            ),
            "details": {},
        }
    }
