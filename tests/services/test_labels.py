import pytest

from essentia_studio.errors import AppError
from essentia_studio.services.labels import format_genre, format_mood, normalize_tags


def test_discogs_parent_child_format_and_deduplication() -> None:
    assert format_genre("Electronic---House") == "Electronic; House"
    assert normalize_tags([" House ", "house", "Deep House"]) == ["House", "Deep House"]


def test_mood_label_becomes_title_case() -> None:
    assert format_mood("moodtheme---happy") == "Happy"


def test_tag_normalization_rejects_oversized_values() -> None:
    with pytest.raises(AppError, match="120 Zeichen"):
        normalize_tags(["x" * 121])


def test_tag_normalization_limits_unique_values() -> None:
    with pytest.raises(AppError) as error:
        normalize_tags([f"Genre {index}" for index in range(65)])

    assert error.value.code == "too_many_tags"
