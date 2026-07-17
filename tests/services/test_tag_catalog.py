import json

import pytest

from essentia_studio.errors import AppError
from essentia_studio.services.tag_catalog import TagCatalogService

GENRE_CATALOG = "genre_discogs400-discogs-effnet-1.json"
MOOD_CATALOG = "mtg_jamendo_moodtheme-discogs-effnet-1.json"


def write_catalog(model_dir, catalog_name: str, classes: list[str]) -> None:
    (model_dir / catalog_name).write_text(
        json.dumps({"classes": classes}), encoding="utf-8"
    )


def write_required_catalogs(model_dir) -> None:
    write_catalog(
        model_dir,
        GENRE_CATALOG,
        [
            "Rock",
            "Funk / Soul---Contemporary R&B",
            "Funk / Soul---Contemporary r&b",
            "Rock",
        ],
    )
    write_catalog(
        model_dir,
        MOOD_CATALOG,
        ["moodtheme---sad", "moodtheme---happy", "moodtheme---Happy"],
    )


def test_load_expands_sorts_and_deduplicates_bundled_model_labels(tmp_path) -> None:
    write_required_catalogs(tmp_path)

    options = TagCatalogService(tmp_path).load()

    assert options.genres == ["Contemporary R&B", "Funk / Soul", "Rock"]
    assert options.moods == ["Happy", "Sad"]


def test_load_nfkc_normalizes_labels_before_deduplication(tmp_path) -> None:
    write_catalog(tmp_path, GENRE_CATALOG, ["Ａｍｂｉｅｎｔ", "Ambient"])
    write_catalog(tmp_path, MOOD_CATALOG, ["moodtheme---ｈａｐｐｙ", "moodtheme---happy"])

    options = TagCatalogService(tmp_path).load()

    assert options.genres == ["Ambient"]
    assert options.moods == ["Happy"]


def test_load_reports_missing_catalog_without_exposing_its_path(tmp_path) -> None:
    write_catalog(tmp_path, MOOD_CATALOG, ["moodtheme---happy"])

    with pytest.raises(AppError) as raised:
        TagCatalogService(tmp_path).load()

    assert raised.value.code == "tag_catalog_unavailable"
    assert raised.value.status_code == 503
    assert raised.value.message == (
        "Der Tag-Katalog „genre_discogs400-discogs-effnet-1.json“ ist nicht verfügbar."
    )
    assert str(tmp_path) not in raised.value.message


def test_load_reports_invalid_json_without_exposing_its_path(tmp_path) -> None:
    (tmp_path / GENRE_CATALOG).write_text("not valid json", encoding="utf-8")
    write_catalog(tmp_path, MOOD_CATALOG, ["moodtheme---happy"])

    with pytest.raises(AppError) as raised:
        TagCatalogService(tmp_path).load()

    assert raised.value.code == "tag_catalog_unavailable"
    assert raised.value.message == (
        "Der Tag-Katalog „genre_discogs400-discogs-effnet-1.json“ ist nicht verfügbar."
    )
    assert str(tmp_path) not in raised.value.message


def test_load_reports_invalid_utf8_without_exposing_its_path(tmp_path) -> None:
    (tmp_path / GENRE_CATALOG).write_bytes(b'{"classes": ["\xff"]}')
    write_catalog(tmp_path, MOOD_CATALOG, ["moodtheme---happy"])

    with pytest.raises(AppError) as raised:
        TagCatalogService(tmp_path).load()

    assert raised.value.code == "tag_catalog_unavailable"
    assert raised.value.status_code == 503
    assert raised.value.message == (
        "Der Tag-Katalog „genre_discogs400-discogs-effnet-1.json“ ist nicht verfügbar."
    )
    assert str(tmp_path) not in raised.value.message


@pytest.mark.parametrize("classes", [None, ["Rock", 3], "Rock"])
def test_load_reports_an_invalid_catalog_structure(tmp_path, classes) -> None:
    (tmp_path / GENRE_CATALOG).write_text(json.dumps({"classes": classes}), encoding="utf-8")
    write_catalog(tmp_path, MOOD_CATALOG, ["moodtheme---happy"])

    with pytest.raises(AppError) as raised:
        TagCatalogService(tmp_path).load()

    assert raised.value.code == "tag_catalog_unavailable"
    assert raised.value.message == (
        "Der Tag-Katalog „genre_discogs400-discogs-effnet-1.json“ ist nicht verfügbar."
    )
