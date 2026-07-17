from collections.abc import Sequence

from essentia_studio.domain.analysis import Prediction
from essentia_studio.domain.tag_labels import split_genre_label


def select_genre_predictions(
    labels: Sequence[str],
    scores: Sequence[float],
    threshold: float,
    visible_tag_limit: int,
) -> list[Prediction]:
    ranked_candidates = sorted(
        zip(labels, scores, strict=True),
        key=lambda candidate: candidate[1],
        reverse=True,
    )
    if not ranked_candidates:
        return []

    accepted: list[Prediction] = []
    visible_tag_ids: set[str] = set()
    for label, score in ranked_candidates:
        if score < threshold:
            continue
        new_tag_ids = {
            tag.casefold()
            for tag in split_genre_label(label)
            if tag.casefold() not in visible_tag_ids
        }
        if not new_tag_ids:
            continue
        accepted.append(Prediction(label, float(score)))
        visible_tag_ids.update(new_tag_ids)
        if len(visible_tag_ids) >= visible_tag_limit:
            return accepted

    if accepted:
        return accepted

    label, score = ranked_candidates[0]
    return [Prediction(label, float(score), accepted=False)]
