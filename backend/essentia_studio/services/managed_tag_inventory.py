import unicodedata
from collections.abc import Iterable
from pathlib import Path

from essentia_studio.domain.tracks import ManagedTagInventory
from essentia_studio.tags.protocol import ManagedTagSnapshot
from essentia_studio.tags.registry import TagAdapterRegistry


def normalize_inventory_values(values: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    identities: set[str] = set()
    for value in values:
        cleaned = unicodedata.normalize("NFKC", str(value)).strip()
        if cleaned and cleaned.casefold() not in identities:
            normalized.append(cleaned)
            identities.add(cleaned.casefold())
    return normalized


def inventory_from_snapshot(snapshot: ManagedTagSnapshot) -> ManagedTagInventory:
    return ManagedTagInventory(
        genres=normalize_inventory_values(snapshot.fields.get("genres", [])),
        moods=normalize_inventory_values(snapshot.fields.get("moods", [])),
        status="ok",
    )


def read_managed_tag_inventory(path: Path, registry: TagAdapterRegistry) -> ManagedTagInventory:
    try:
        return inventory_from_snapshot(registry.for_path(path).read(path))
    except Exception:
        return ManagedTagInventory(status="error", error_code="managed_tags_unreadable")
