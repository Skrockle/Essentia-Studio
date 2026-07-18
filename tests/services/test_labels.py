import pytest

from essentia_studio.domain.tag_labels import (
    format_mood_label,
    legacy_genre_label,
    split_genre_label,
)
from essentia_studio.errors import AppError
from essentia_studio.services.labels import normalize_tags


def test_discogs_parent_and_child_become_separate_tags() -> None:
    assert split_genre_label("Funk / Soul---Contemporary R&B") == [
        "Funk / Soul",
        "Contemporary R&B",
    ]
    assert split_genre_label("Rock") == ["Rock"]
    assert split_genre_label("Electronic---") == ["Electronic"]
    assert legacy_genre_label("Electronic---House") == "Electronic; House"


def test_mood_uses_the_last_model_segment() -> None:
    assert format_mood_label("moodtheme---happy") == "Happy"


def test_tag_normalization_deduplicates_values() -> None:
    assert normalize_tags([" House ", "house", "Deep House"]) == ["House", "Deep House"]


def test_tag_normalization_rejects_oversized_values() -> None:
    with pytest.raises(AppError, match="120 Zeichen"):
        normalize_tags(["x" * 121])


def test_tag_normalization_limits_unique_values() -> None:
    with pytest.raises(AppError) as error:
        normalize_tags([f"Genre {index}" for index in range(65)])

    assert error.value.code == "too_many_tags"
