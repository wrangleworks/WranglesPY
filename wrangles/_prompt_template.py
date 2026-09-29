"""Literal row-column substitution for text prompts, without provider dependencies."""

import json
import math
import re


_IDENTIFIER = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*\Z")
_PLACEHOLDER = re.compile(r"\{\{\s*(.*?)\s*\}\}", re.DOTALL)


def _json_value(value):
    """Validate finite JSON without including private input values in errors."""
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict) and all(isinstance(key, str) for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError

    try:
        check(value)
        # Also rejects circular containers before sending any requests.
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError(
            "Prompt template values must contain finite JSON-compatible values "
            "and string object keys."
        ) from None


def render(template, row_items):
    """Render once from (column, value) pairs, preserving duplicate-name checks."""
    if not isinstance(template, str) or not _PLACEHOLDER.search(template):
        return template

    aliases = {}
    for name, value in row_items:
        if isinstance(name, str):
            alias = re.sub(r"[^a-zA-Z0-9_]", "_", name)
            aliases.setdefault(alias, []).append(value)

    def substitute(match):
        name = match.group(1).strip()
        if not _IDENTIFIER.fullmatch(name):
            raise ValueError(
                "Prompt template references must be ASCII identifiers; "
                "use underscores for spaces or punctuation."
            )
        matches = aliases.get(name, [])
        if not matches:
            raise ValueError(f"Prompt template reference {name!r} does not match a source column.")
        if len(matches) > 1:
            raise ValueError(
                f"Prompt template reference {name!r} is ambiguous because source "
                "columns share the same normalized name."
            )
        value = matches[0]
        _json_value(value)
        return value if isinstance(value, str) else json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )

    return _PLACEHOLDER.sub(substitute, template)
