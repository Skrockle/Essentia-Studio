def split_genre_label(raw_label: str) -> list[str]:
    return [segment.strip() for segment in raw_label.split("---") if segment.strip()]


def legacy_genre_label(raw_label: str) -> str:
    return "; ".join(split_genre_label(raw_label))


def format_mood_label(raw_label: str) -> str:
    return raw_label.rsplit("---", maxsplit=1)[-1].strip().title()
