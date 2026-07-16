import pytest

from essentia_studio.playlists.this_is import METHODS, build_this_is


def test_greatest_hits_matches_upstream_rule() -> None:
    playlist = build_this_is("Björk", "greatest_hits", 50)

    assert playlist.model_dump(exclude_none=True)["all"] == [
        {"is": {"albumartist": "Björk"}},
        {
            "any": [
                {"is": {"loved": True}},
                {"gt": {"rating": 3}},
                {"gt": {"playcount": 9}},
            ]
        },
    ]


@pytest.mark.parametrize("method", METHODS)
def test_every_upstream_method_builds_a_valid_playlist(method: str) -> None:
    playlist = build_this_is("Björk", method)

    assert playlist.name == "This is Björk"
    assert playlist.limit == 50
