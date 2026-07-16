import json
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CatalogItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str
    label: str


class PlaylistField(CatalogItem):
    type: Literal["string", "number", "boolean", "date", "playlist"]
    category: str


class PlaylistPreset(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    slug: str
    category: str
    definition: dict


class ThisIsMethod(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    label: str


class PlaylistCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_commit: str
    fields: tuple[PlaylistField, ...]
    operators: dict[str, tuple[CatalogItem, ...]]
    sort_options: tuple[CatalogItem, ...]
    presets: tuple[PlaylistPreset, ...]
    this_is_methods: tuple[ThisIsMethod, ...]

    @classmethod
    def load(cls) -> "PlaylistCatalog":
        resource = files("essentia_studio.playlists").joinpath("catalog.json")
        catalog = cls.model_validate_json(resource.read_text(encoding="utf-8"))
        cls._reject_duplicates(catalog)
        return catalog

    @staticmethod
    def _reject_duplicates(catalog: "PlaylistCatalog") -> None:
        checks = {
            "field keys": [field.key for field in catalog.fields],
            "preset slugs": [preset.slug for preset in catalog.presets],
            "method ids": [method.id for method in catalog.this_is_methods],
        }
        for label, values in checks.items():
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate playlist catalog {label}")

    def as_dict(self) -> dict:
        return json.loads(self.model_dump_json())
