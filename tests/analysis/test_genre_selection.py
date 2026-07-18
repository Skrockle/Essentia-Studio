from essentia_studio.analysis.genre_selection import select_genre_predictions
from essentia_studio.domain.analysis import Prediction


def test_selection_stops_after_predictions_fill_visible_tag_limit() -> None:
    selected = select_genre_predictions(
        labels=[
            "Rock---Alternative Rock",
            "Electronic---House",
            "Hip Hop---Cloud Rap",
        ],
        scores=[0.9, 0.8, 0.7],
        threshold=0.25,
        visible_tag_limit=3,
    )

    assert selected == [
        Prediction("Rock---Alternative Rock", 0.9),
        Prediction("Electronic---House", 0.8),
    ]


def test_selection_counts_only_distinct_visible_tags() -> None:
    selected = select_genre_predictions(
        labels=[
            "Rock---Alternative Rock",
            "Rock---Indie Rock",
            "Electronic---House",
        ],
        scores=[0.9, 0.8, 0.7],
        threshold=0.25,
        visible_tag_limit=3,
    )

    assert selected == [
        Prediction("Rock---Alternative Rock", 0.9),
        Prediction("Rock---Indie Rock", 0.8),
    ]


def test_selection_marks_best_below_threshold_as_rejected() -> None:
    selected = select_genre_predictions(
        labels=["Rock---Alternative Rock", "Electronic---House"],
        scores=[0.11, 0.08],
        threshold=0.25,
        visible_tag_limit=3,
    )

    assert selected == [
        Prediction("Rock---Alternative Rock", 0.11, accepted=False),
    ]


def test_selection_does_not_mix_rejected_candidates_into_accepted_results() -> None:
    selected = select_genre_predictions(
        labels=["Rock---Alternative Rock", "Electronic---House"],
        scores=[0.8, 0.1],
        threshold=0.25,
        visible_tag_limit=3,
    )

    assert selected == [Prediction("Rock---Alternative Rock", 0.8)]


def test_selection_handles_empty_model_output() -> None:
    assert select_genre_predictions([], [], threshold=0.25, visible_tag_limit=3) == []
