from copy import deepcopy
from typing import Any

from essentia_studio.errors import AppError
from essentia_studio.playlists.catalog import PlaylistCatalog
from essentia_studio.playlists.models import PlaylistDefinition
from essentia_studio.playlists.validation import validate_playlist

METHODS: dict[str, dict[str, Any]] = {
    "random": {"sort": "random"},
    "top_rated": {"sort": "rating", "order": "desc"},
    "most_played": {"sort": "playcount", "order": "desc"},
    "recently_played": {
        "conditions": [{"inTheLast": {"lastplayed": 90}}],
        "sort": "lastplayed",
        "order": "desc",
    },
    "recently_added": {"sort": "dateadded", "order": "desc"},
    "loved": {"conditions": [{"is": {"loved": True}}], "sort": "random"},
    "deep_cuts": {"conditions": [{"gt": {"track": 3}}], "sort": "random"},
    "greatest_hits": {
        "conditions": [
            {
                "any": [
                    {"is": {"loved": True}},
                    {"gt": {"rating": 3}},
                    {"gt": {"playcount": 9}},
                ]
            }
        ],
        "sort": "playcount",
        "order": "desc",
    },
    "chronological": {"sort": "+year,+discnumber,+track"},
    "reverse_chrono": {"sort": "-year,+discnumber,+track"},
    "longest": {"sort": "duration", "order": "desc"},
    "shortest": {"sort": "duration", "order": "asc"},
    "high_energy": {
        "conditions": [{"gt": {"bpm": 0}}],
        "sort": "bpm",
        "order": "desc",
    },
    "chill": {
        "conditions": [{"gt": {"bpm": 0}}],
        "sort": "bpm",
        "order": "asc",
    },
    "lossless_only": {
        "conditions": [{"is": {"filetype": "flac"}}],
        "sort": "+year,+discnumber,+track",
    },
    "unplayed": {"conditions": [{"is": {"playcount": 0}}], "sort": "random"},
    "rare_gems": {
        "conditions": [{"gt": {"rating": 3}}, {"lt": {"playcount": 5}}],
        "sort": "rating",
        "order": "desc",
    },
    "album_openers": {
        "conditions": [{"is": {"track": 1}}],
        "sort": "+year,+album",
    },
    "album_closers": {
        "conditions": [{"gt": {"track": 8}}, {"gt": {"duration": 180}}],
        "sort": "+year,+album",
    },
    "singles": {
        "conditions": [{"lt": {"track": 4}}, {"lt": {"duration": 270}}],
        "sort": "playcount",
        "order": "desc",
    },
}

METHOD_DESCRIPTIONS = {
    "random": "shuffled mix",
    "top_rated": "top rated",
    "most_played": "most played",
    "recently_played": "recently played",
    "recently_added": "recently added",
    "loved": "loved tracks",
    "deep_cuts": "deep cuts",
    "greatest_hits": "greatest hits",
    "chronological": "chronological",
    "reverse_chrono": "reverse chronological",
    "longest": "longest tracks",
    "shortest": "shortest tracks",
    "high_energy": "high energy",
    "chill": "chill",
    "lossless_only": "lossless only",
    "unplayed": "unplayed",
    "rare_gems": "rare gems",
    "album_openers": "album openers",
    "album_closers": "album closers",
    "singles": "singles",
}


def build_this_is(
    artist: str,
    method: str,
    limit: int = 50,
    name: str | None = None,
    comment: str | None = None,
) -> PlaylistDefinition:
    clean_artist = artist.strip()
    if not clean_artist or method not in METHODS:
        raise AppError(
            "invalid_this_is_request",
            "Künstler oder Methode ist ungültig.",
            422,
        )
    template = deepcopy(METHODS[method])
    conditions = [{"is": {"albumartist": clean_artist}}]
    conditions.extend(template.pop("conditions", []))
    raw = template | {
        "all": conditions,
        "limit": limit,
        "name": name.strip() if name and name.strip() else f"This is {clean_artist}",
        "comment": (
            comment.strip()
            if comment and comment.strip()
            else f'A "This is {clean_artist}" playlist — {METHOD_DESCRIPTIONS[method]}'
        ),
    }
    return validate_playlist(raw, PlaylistCatalog.load())
