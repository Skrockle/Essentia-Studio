import unicodedata

from essentia_studio.errors import AppError

MAX_TAGS = 64
MAX_TAG_LENGTH = 120


def format_genre(raw_genre: str) -> str:
    parts = [part.strip() for part in raw_genre.split("---", maxsplit=1)]
    return "; ".join(part for part in parts if part)


def format_mood(raw_mood: str) -> str:
    label = raw_mood.rsplit("---", maxsplit=1)[-1]
    return label.strip().title()


def normalize_tags(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for value in values:
        label = unicodedata.normalize("NFKC", value).strip()
        if not label:
            continue
        if len(label) > MAX_TAG_LENGTH:
            raise AppError(
                "tag_too_long",
                "Genre- und Mood-Werte dürfen höchstens 120 Zeichen lang sein.",
                422,
            )
        identity = label.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append(label)
        if len(normalized) > MAX_TAGS:
            raise AppError(
                "too_many_tags",
                "Ein Titel darf höchstens 64 Genre- oder Mood-Werte enthalten.",
                422,
            )

    return normalized
