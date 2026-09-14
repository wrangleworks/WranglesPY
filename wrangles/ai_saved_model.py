"""Prepare Extract-AI content using XL's authoring contract, without compiling it.

Validation inspects known columns but preserves the original cell values and all
extra columns. Runtime compilation remains a separate, stricter operation.
"""

import copy as _copy
import re as _re

import yaml as _yaml

from .ai_definition import (
    _JSON_TYPES,
    _TYPE_ALIASES,
    _load_json_like as _load_cell,
    _split_top_level,
    _validate_json_tree,
)


KNOWN_HEADINGS = (
    "Find", "Description", "Type", "Default", "Examples", "Enum", "Notes",
    "Properties", "Items", "Required", "Additional Properties", "Nullable",
    "Example - Input", "Example - Output",
)
_TYPES = ("string", "number", "integer", "boolean", "array", "object")
_SCHEMA_TYPES = _JSON_TYPES | _TYPE_ALIASES.keys()


def _load_json_like(value):
    return _load_cell(value, json_first=False)


def _header(value):
    return _re.sub(r"[^a-z0-9]", "", str(value).lower())


def _blank(value):
    # XL also treats an empty array (or one blank array element) as a blank cell.
    if isinstance(value, list):
        return not value or (len(value) == 1 and _blank(value[0]))
    return value is None or isinstance(value, str) and not value.strip()


def _parts(text):
    return _split_top_level(text, "|") or _split_top_level(text, ",")


def _parse_list(value):
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        raise ValueError("must be a list")
    text = value.strip()
    if text.startswith(("[", "- ")):
        parsed = _load_json_like(text)
        if not isinstance(parsed, list):
            raise ValueError("must be a list")
        return parsed
    return _parts(text) or [text]


def _parse_properties(value):
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        raise ValueError("must be an object or list")
    text = value.strip()
    if text.startswith(("{", "[", "- ")):
        parsed = _load_json_like(text)
        if not isinstance(parsed, (dict, list)):
            raise ValueError("must be an object or list")
        return parsed
    parts = _parts(text)
    if parts and all(":" in part for part in parts):
        return {
            name.strip(): schema.strip()
            for name, schema in (part.split(":", 1) for part in parts)
        }
    if ":" in text:
        parsed = _load_json_like(text)
        if not isinstance(parsed, dict):
            raise ValueError("must be an object")
        return parsed
    return _parse_list(value)


def _properties(value):
    parsed = _parse_properties(value)
    if isinstance(parsed, list):
        return
    for schema in parsed.values():
        if isinstance(schema, str):
            if schema.strip().lower() not in _SCHEMA_TYPES:
                raise ValueError(f"contains unsupported type {schema}")
        elif not isinstance(schema, (dict, list)):
            raise ValueError("property definitions must be types or schema objects")


def _items(value):
    if isinstance(value, str) and value.strip().lower() in _SCHEMA_TYPES:
        return
    _parse_properties(value)


def _structured(value):
    if isinstance(value, str) and value.strip().startswith(("{", "[", "- ")):
        _load_json_like(value)


def _examples(value):
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            _load_json_like(value)
        except (ValueError, _yaml.YAMLError):
            parts = _split_top_level(value.strip(), ",")
            if not parts:
                raise
            for part in parts:
                _load_json_like(part)
    else:
        _structured(value)


def _boolean(value):
    return isinstance(value, bool) or (
        isinstance(value, str) and value.strip().lower() in {"true", "false"}
    )


def merge_settings(existing: dict | None = None, overrides: dict | None = None) -> dict:
    """Copy content-level settings, replacing only explicitly supplied keys."""
    result = {}
    for settings in (existing, overrides):
        if settings is None:
            continue
        if not isinstance(settings, dict):
            raise ValueError("Extract-AI Settings must be an object.")
        try:
            _validate_json_tree(settings)
        except ValueError as exc:
            raise ValueError(f"Extract-AI Settings: {exc}.") from exc
        result.update(_copy.deepcopy(settings))
    if "variant" in result and result["variant"] != "extract-ai":
        raise ValueError("Extract-AI Settings.variant must be 'extract-ai'.")
    return result


def prepare_content(content: dict) -> dict:
    """Validate and copy a full saved definition without service calls.

    Blank rows and optional cells are retained. No defaults are materialized,
    schema cells rewritten, or unknown columns discarded. This is save-time
    validation, not a guarantee that the definition can execute or compile.
    """
    if not isinstance(content, dict):
        raise ValueError("Extract-AI content must be an object.")
    columns, rows = content.get("Columns"), content.get("Data")
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise ValueError("Extract-AI content must contain Columns and Data arrays.")
    _validate_json_tree(columns)
    normalized = [_header(column) for column in columns]
    if "find" not in normalized:
        raise ValueError("The Find column is required.")
    indexes = {
        _header(heading): normalized.index(_header(heading))
        for heading in KNOWN_HEADINGS if _header(heading) in normalized
    }

    for number, row in enumerate(rows, start=2):
        if not isinstance(row, list) or len(row) > len(columns):
            raise ValueError(f"Data on row {number}: must be an array with no more values than columns.")
        for column, value in zip(columns, row):
            try:
                _validate_json_tree(value)
            except ValueError as exc:
                raise ValueError(f"{column} on row {number}: {exc}.") from exc
        if all(_blank(value) for value in row):
            continue

        def value_at(heading):
            index = indexes.get(_header(heading))
            return row[index] if index is not None and index < len(row) else None

        def fail(column, message):
            raise ValueError(f"{column} on row {number}: {message}.")

        def check(column, action, only_type=None):
            value = value_at(column)
            if _blank(value):
                return
            if only_type and kind and kind != only_type:
                fail(column, f"applies only to type {only_type}")
            try:
                action(value)
            except (TypeError, ValueError, _yaml.YAMLError) as exc:
                fail(column, str(exc).rstrip("."))

        if _blank(value_at("Find")):
            raise ValueError(f"Find is required on row {number}.")
        raw_type = value_at("Type")
        kind = "" if _blank(raw_type) else str(raw_type).strip().lower()
        if kind and kind not in _TYPES:
            fail("Type", f"must be {', '.join(_TYPES)}")
        if kind == "object" and "properties" in indexes and _blank(value_at("Properties")):
            fail("Properties", "is required for type object")
        check("Properties", _properties, "object")
        check("Items", _items, "array")
        check("Required", _parse_list, "object")
        check(
            "Additional Properties",
            lambda value: None if _boolean(value) else _items(value),
            "object",
        )
        if not _blank(value_at("Nullable")) and not _boolean(value_at("Nullable")):
            fail("Nullable", "must be TRUE or FALSE")
        if not _blank(value_at("Example - Input")) and _blank(value_at("Example - Output")):
            fail("Example - Input", "requires Example - Output")
        for heading in ("Default", "Examples", "Enum", "Example - Output"):
            check(heading, _examples if heading == "Examples" else _structured)

    result = _copy.deepcopy(content)
    result["Settings"] = merge_settings(overrides=content.get("Settings"))
    return result
