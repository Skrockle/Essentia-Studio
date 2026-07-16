import pytest

from essentia_studio.errors import AppError
from essentia_studio.playlists.validation import validate_playlist


def test_nested_all_any_rule_is_preserved(catalog) -> None:
    raw = {
        "name": "Great electronic tracks",
        "all": [
            {"contains": {"genre": "Electronic"}},
            {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
        ],
        "sort": "-rating,+artist",
        "limit": 100,
    }

    assert validate_playlist(raw, catalog).model_dump(exclude_none=True) == raw


def test_operator_must_match_field_type(catalog) -> None:
    with pytest.raises(AppError) as error:
        validate_playlist(
            {"name": "Bad", "all": [{"before": {"rating": 3}}]},
            catalog,
        )

    assert error.value.code == "invalid_playlist_operator"


def test_nested_rules_are_bounded(catalog) -> None:
    rule = {"is": {"loved": True}}
    for _ in range(13):
        rule = {"all": [rule]}

    with pytest.raises(AppError) as error:
        validate_playlist({"name": "Too deep", "all": [rule]}, catalog)

    assert error.value.code == "invalid_playlist_group"
