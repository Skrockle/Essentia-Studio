from essentia_studio.playlists.catalog import PlaylistCatalog


def test_catalog_contains_complete_upstream_inventory() -> None:
    catalog = PlaylistCatalog.load()

    assert len(catalog.fields) >= 100
    assert {item.type for item in catalog.fields} == {
        "string",
        "number",
        "boolean",
        "date",
        "playlist",
    }
    assert len(catalog.presets) == 298
    assert len(catalog.this_is_methods) == 20
    assert {method.id for method in catalog.this_is_methods} == {
        "random",
        "top_rated",
        "most_played",
        "recently_played",
        "recently_added",
        "loved",
        "deep_cuts",
        "greatest_hits",
        "chronological",
        "reverse_chrono",
        "longest",
        "shortest",
        "high_energy",
        "chill",
        "lossless_only",
        "unplayed",
        "rare_gems",
        "album_openers",
        "album_closers",
        "singles",
    }
