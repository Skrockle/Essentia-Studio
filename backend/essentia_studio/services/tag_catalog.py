import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from essentia_studio.domain.tag_labels import (
    deduplicate_labels,
    format_mood_label,
    split_genre_label,
)
from essentia_studio.errors import AppError
from essentia_studio.schemas.tag_options import TagOptions

GENRE_CATALOG_NAME = "genre_discogs400-discogs-effnet-1.json"
MOOD_CATALOG_NAME = "mtg_jamendo_moodtheme-discogs-effnet-1.json"


class TagCatalogService:
    def __init__(self, model_dir: Path) -> None:
        self._model_dir = model_dir

    def load(self) -> TagOptions:
        genres = self._load_classes(GENRE_CATALOG_NAME)
        moods = self._load_classes(MOOD_CATALOG_NAME)
        return TagOptions(
            genres=_sorted_unique(
                genre for raw_label in genres for genre in split_genre_label(raw_label)
            ),
            moods=_sorted_unique(format_mood_label(raw_label) for raw_label in moods),
        )

    def _load_classes(self, catalog_name: str) -> list[str]:
        try:
            with (self._model_dir / catalog_name).open(encoding="utf-8") as catalog_file:
                catalog = json.load(catalog_file)
        except (OSError, json.JSONDecodeError) as error:
            raise _catalog_unavailable(catalog_name) from error
        if not _has_classes(catalog):
            raise _catalog_unavailable(catalog_name)
        return catalog["classes"]


def _has_classes(catalog: Any) -> bool:
    return (
        isinstance(catalog, dict)
        and isinstance(catalog.get("classes"), list)
        and all(isinstance(label, str) for label in catalog["classes"])
    )


def _sorted_unique(labels: Iterable[str]) -> list[str]:
    return sorted(deduplicate_labels(list(labels)), key=str.casefold)


def _catalog_unavailable(catalog_name: str) -> AppError:
    return AppError(
        "tag_catalog_unavailable",
        f"Der Tag-Katalog „{catalog_name}“ ist nicht verfügbar.",
        503,
    )
