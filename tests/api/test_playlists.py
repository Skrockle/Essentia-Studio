def test_catalog_preset_and_file_lifecycle(client) -> None:
    catalog = client.get("/api/playlists/catalog").json()
    assert len(catalog["presets"]) == 298
    assert len(catalog["this_is_methods"]) == 20

    built = client.post(
        "/api/playlists/from-preset/recently-played",
        json={"filename": "recent.nsp", "overrides": {"limit": 25}},
    )
    assert built.status_code == 201
    fingerprint = built.json()["fingerprint"]

    updated = client.put(
        "/api/playlists/recent.nsp",
        json={
            "expected_fingerprint": fingerprint,
            "definition": {
                "name": "Recent",
                "all": [{"inTheLast": {"lastplayed": 7}}],
            },
        },
    )
    assert updated.status_code == 200
    deleted = client.request(
        "DELETE",
        "/api/playlists/recent.nsp",
        json={"expected_fingerprint": updated.json()["fingerprint"]},
    )
    assert deleted.status_code == 204


def test_this_is_and_custom_nested_playlist(client) -> None:
    this_is = client.post(
        "/api/playlists/this-is",
        json={
            "filename": "this-is-bjork.nsp",
            "artist": "Björk",
            "method": "greatest_hits",
            "limit": 50,
        },
    )
    assert this_is.status_code == 201
    assert this_is.json()["definition"]["name"] == "This is Björk"

    custom = client.post(
        "/api/playlists",
        json={
            "filename": "custom.nsp",
            "definition": {
                "name": "Custom",
                "all": [
                    {
                        "any": [
                            {"contains": {"genre": "Ambient"}},
                            {"is": {"loved": True}},
                        ]
                    }
                ],
            },
        },
    )
    assert custom.status_code == 201
    assert len(client.get("/api/playlists").json()) == 2
