from typing import Any

from pydantic import ValidationError

from essentia_studio.errors import AppError
from essentia_studio.playlists.catalog import PlaylistCatalog, PlaylistField
from essentia_studio.playlists.models import PlaylistDefinition

UPSTREAM_COMPATIBLE_OPERATORS = {("date", "notContains")}


def validate_playlist(raw: dict, catalog: PlaylistCatalog) -> PlaylistDefinition:
    if not isinstance(raw, dict):
        raise _error("invalid_playlist", "Die Playlist ist ungültig.")
    cleaned = dict(raw)
    counter = [0]
    for group_name in ("all", "any"):
        if group_name in cleaned:
            cleaned[group_name] = _validate_group(
                cleaned[group_name], depth=1, counter=counter, catalog=catalog
            )
    _validate_sort(cleaned.get("sort"), catalog)
    for key in ("name", "comment"):
        if key in cleaned and cleaned[key] is not None:
            cleaned[key] = _bounded_string(
                cleaned[key],
                allow_empty=key == "comment",
                trim=True,
            )
    try:
        return PlaylistDefinition.model_validate(cleaned)
    except ValidationError as error:
        raise _error("invalid_playlist", "Die Playlist ist ungültig.") from error


def _validate_group(
    items: object,
    *,
    depth: int,
    counter: list[int],
    catalog: PlaylistCatalog,
) -> list[dict]:
    if depth > 12 or not isinstance(items, list) or not items:
        raise _error("invalid_playlist_group", "Die Regelgruppe ist ungültig.")
    validated: list[dict] = []
    for item in items:
        counter[0] += 1
        if counter[0] > 500 or not isinstance(item, dict) or len(item) != 1:
            raise _error("invalid_playlist_rule", "Die Playlist enthält ungültige Regeln.")
        operator, operand = next(iter(item.items()))
        if operator in {"all", "any"}:
            nested = _validate_group(
                operand,
                depth=depth + 1,
                counter=counter,
                catalog=catalog,
            )
            validated.append({operator: nested})
        else:
            validated.append(_validate_condition(operator, operand, catalog))
    return validated


def _validate_condition(operator: str, operand: object, catalog: PlaylistCatalog) -> dict:
    if not isinstance(operand, dict) or len(operand) != 1:
        raise _error("invalid_playlist_rule", "Die Bedingung ist ungültig.")
    field_key, value = next(iter(operand.items()))
    field = next((item for item in catalog.fields if item.key == field_key), None)
    if field is None:
        raise _error("invalid_playlist_field", "Das Playlist-Feld ist unbekannt.")
    allowed = {item.key for item in catalog.operators[field.type]}
    if operator not in allowed and (field.type, operator) not in UPSTREAM_COMPATIBLE_OPERATORS:
        raise _error(
            "invalid_playlist_operator",
            "Der Operator passt nicht zum gewählten Feld.",
        )
    return {operator: {field_key: _validate_value(operator, value, field)}}


def _validate_value(operator: str, value: Any, field: PlaylistField) -> Any:
    if operator == "inTheRange":
        return _validate_range(value, field)
    if operator in {"inTheLast", "notInTheLast"}:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise _error("invalid_playlist_value", "Die Anzahl der Tage ist ungültig.")
        return value
    if field.type == "boolean":
        if not isinstance(value, bool):
            raise _error("invalid_playlist_value", "Der Wert muss wahr oder falsch sein.")
        return value
    if field.type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _error("invalid_playlist_value", "Der Wert muss eine Zahl sein.")
        return value
    return _bounded_string(
        value,
        allow_empty=field.type != "playlist",
        trim=field.type == "playlist",
    )


def _validate_range(value: Any, field: PlaylistField) -> list[Any]:
    if not isinstance(value, list) or len(value) != 2:
        raise _error("invalid_playlist_value", "Der Bereich benötigt zwei Werte.")
    values = [_validate_value("is", item, field) for item in value]
    if values[0] > values[1]:
        raise _error("invalid_playlist_value", "Der Bereich ist nicht aufsteigend.")
    return values


def _bounded_string(value: Any, *, allow_empty: bool, trim: bool) -> str:
    if not isinstance(value, str) or len(value) > 500:
        raise _error("invalid_playlist_value", "Der Textwert ist ungültig.")
    cleaned = value.strip() if trim else value
    if not cleaned and not allow_empty:
        raise _error("invalid_playlist_value", "Der Textwert ist ungültig.")
    return cleaned


def _validate_sort(value: Any, catalog: PlaylistCatalog) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise _error("invalid_playlist_sort", "Die Sortierung ist ungültig.")
    allowed = {field.key for field in catalog.fields} | {
        item.key for item in catalog.sort_options
    }
    segments = [segment.strip().lstrip("+-") for segment in value.split(",")]
    if any(not segment or segment not in allowed for segment in segments):
        raise _error("invalid_playlist_sort", "Die Sortierung ist ungültig.")


def _error(code: str, message: str) -> AppError:
    return AppError(code, message, 422)
