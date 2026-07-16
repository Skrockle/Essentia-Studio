"""Extract the complete literal catalog from the pinned upstream NSP generator."""

import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "vendor"
    / "navidrome-smart-playlist-generator"
    / "navidrome_smart_playlist_creator.py"
)
OUTPUT = ROOT / "backend" / "essentia_studio" / "playlists" / "catalog.json"
SOURCE_COMMIT = "b706d70148011093acc69b1e1679029d48d1aea4"

METHOD_LABELS = {
    "random": "Random selection",
    "top_rated": "Top rated",
    "most_played": "Most played",
    "recently_played": "Recently played",
    "recently_added": "Recently added",
    "loved": "Loved tracks only",
    "deep_cuts": "Deep cuts",
    "greatest_hits": "Greatest hits",
    "chronological": "Chronological",
    "reverse_chrono": "Reverse chronological",
    "longest": "Longest tracks",
    "shortest": "Shortest tracks",
    "high_energy": "High energy",
    "chill": "Chill",
    "lossless_only": "Lossless only",
    "unplayed": "Unplayed",
    "rare_gems": "Rare gems",
    "album_openers": "Album openers",
    "album_closers": "Album closers",
    "singles": "Singles",
}


def assigned_literals(source: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for node in ast.walk(ast.parse(source)):
        target = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
        if name in {"fields", "operators", "sort_options", "PRESETS"} and value:
            values[name] = ast.literal_eval(value)
    return values


def build_catalog(source: str) -> dict[str, Any]:
    literals = assigned_literals(source)
    fields = [
        {"key": key, "label": label, "type": field_type, "category": category}
        for category, entries in literals["fields"].items()
        for key, label, field_type in entries
    ]
    operators = {
        field_type: [{"key": key, "label": label} for key, label in entries]
        for field_type, entries in literals["operators"].items()
    }
    sort_options = [
        {"key": key, "label": label} for key, label in literals["sort_options"]
    ]
    presets = [
        {"label": label, "slug": slug, "category": category, "definition": definition}
        for label, slug, category, definition in literals["PRESETS"]
    ]
    methods = [{"id": key, "label": label} for key, label in METHOD_LABELS.items()]
    return {
        "source_commit": SOURCE_COMMIT,
        "fields": fields,
        "operators": operators,
        "sort_options": sort_options,
        "presets": presets,
        "this_is_methods": methods,
    }


def main() -> None:
    payload = build_catalog(SOURCE.read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
