def split_genre_label(raw_label: str) -> list[str]:
    return [segment.strip() for segment in raw_label.split("---") if segment.strip()]


def legacy_genre_label(raw_label: str) -> str:
    return "; ".join(split_genre_label(raw_label))


def deduplicate_labels(values: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for value in values:
        identity = value.casefold()
        if identity not in seen:
            seen.add(identity)
            deduplicated.append(value)
    return deduplicated


def rewrite_legacy_genres(draft_values: list[str], raw_labels: list[str]) -> list[str]:
    replacements = {
        legacy_genre_label(raw_label): split_genre_label(raw_label)
        for raw_label in raw_labels
        if len(split_genre_label(raw_label)) > 1
    }
    expanded = [
        value
        for draft_value in draft_values
        for value in replacements.get(draft_value, [draft_value])
    ]
    return deduplicate_labels(expanded)


def format_mood_label(raw_label: str) -> str:
    return raw_label.rsplit("---", maxsplit=1)[-1].strip().title()
