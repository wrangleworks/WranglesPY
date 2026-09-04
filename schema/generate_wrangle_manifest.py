"""Generate the deterministic recipe-wrangle runtime contract manifest.

The manifest deliberately keeps runtime facts separate from curated Registry
content.  It inventories the recipe namespace, public Python signature, embedded
JSON Schema docstring, and common-control capabilities without trying to decide
which documentation wording is best.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterator

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import wrangles  # noqa: E402


FORMAT = "wrangles-runtime-manifest"
FORMAT_VERSION = "0.1"
SCHEMA_URL = (
    "https://docs.wrangles.com/registry/schema/"
    "wrangles-runtime-manifest.schema.json"
)
SOURCE_REPOSITORY = "https://github.com/wrangleworks/WranglesPY"
DEFAULT_OUTPUT = Path(__file__).with_name("wrangle_runtime_manifest.json")
# These values are supplied by recipe.run rather than authored in recipe YAML.
# Keeping them separate prevents implementation plumbing from becoming public
# Registry syntax while preserving it for runtime reconciliation. ``variables``
# is also injected, but remains public when the callable's embedded schema
# deliberately documents it (for example, ``matrix`` and ``recipe``).
INTERNAL_PARAMETERS = {"df", "error", "functions"}
SKIPPED_NAMESPACE_NAMES = {"main", "pandas"}


class ManifestError(ValueError):
    """Raised when the runtime namespace cannot produce a trustworthy manifest."""


def _recipe_key(path: tuple[str, ...]) -> str:
    python_path = ".".join(path)
    replacements = {
        python_name: recipe_name
        for recipe_name, python_name in wrangles.config.reserved_word_replacements.items()
    }
    return replacements.get(python_path, python_path)


def _iter_callables(
    obj: Any,
    path: tuple[str, ...] = (),
) -> Iterator[tuple[str, Any]]:
    """Yield every public callable exposed through the recipe namespace."""
    if callable(obj):
        yield _recipe_key(path), obj

    for name in sorted(item for item in dir(obj) if not item.startswith("_")):
        if name in SKIPPED_NAMESPACE_NAMES:
            continue
        child = getattr(obj, name)
        if child is obj:
            continue
        yield from _iter_callables(child, (*path, name))


def _annotation_text(annotation: Any) -> str | None:
    if annotation is inspect.Parameter.empty:
        return None
    return inspect.formatannotation(annotation)


def _parameter_contract(parameter: inspect.Parameter) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "name": parameter.name,
        "kind": parameter.kind.name.lower(),
        "required": parameter.default is inspect.Parameter.empty,
    }
    annotation = _annotation_text(parameter.annotation)
    if annotation is not None:
        contract["annotation"] = annotation
    if parameter.default is not inspect.Parameter.empty:
        try:
            json.dumps(parameter.default)
        except TypeError as error:
            raise ManifestError(
                f"Parameter {parameter.name!r} has a non-JSON default: "
                f"{parameter.default!r}"
            ) from error
        contract["default"] = parameter.default
    return contract


def _parse_docstring_schema(runtime_key: str, function: Any) -> dict[str, Any] | None:
    docstring = getattr(function, "__doc__", None)
    if not docstring:
        return None

    stripped = docstring.strip()
    looks_like_schema = stripped.startswith("type:") or stripped.startswith("anyOf:")
    try:
        parsed = yaml.safe_load(docstring)
    except yaml.YAMLError as error:
        if looks_like_schema:
            raise ManifestError(
                f"{runtime_key} has an invalid JSON Schema docstring: {error}"
            ) from error
        return None

    if isinstance(parsed, dict) and ("type" in parsed or "anyOf" in parsed):
        return parsed
    return None


def _plain_docstring(function: Any, schema: dict[str, Any] | None) -> str | None:
    """Return useful code-owned prose only when no schema docstring exists."""
    if schema is not None:
        return None
    docstring = inspect.getdoc(function)
    return docstring or None


def _common_controls(runtime_key: str) -> tuple[dict[str, bool], str]:
    where_supported = runtime_key not in wrangles.config.where_not_implemented
    where_mode = "unsupported"
    if where_supported:
        where_mode = (
            "overwrite_output"
            if runtime_key in wrangles.config.where_overwrite_output
            else "filter"
        )
    return (
        {
            "if": True,
            "where": where_supported,
            "where_params": where_supported,
        },
        where_mode,
    )


def _wrangle_contract(runtime_key: str, function: Any) -> dict[str, Any]:
    signature = inspect.signature(function)
    docstring_schema = _parse_docstring_schema(runtime_key, function)
    schema_properties = (
        docstring_schema.get("properties", {})
        if isinstance(docstring_schema, dict)
        else {}
    )
    if isinstance(docstring_schema, dict) and isinstance(docstring_schema.get("anyOf"), list):
        for option in reversed(docstring_schema["anyOf"]):
            if isinstance(option, dict) and isinstance(option.get("properties"), dict):
                schema_properties = option["properties"]
                break
    public_parameters = []
    internal_parameters = []
    variadic = {"positional": None, "keyword": None}

    for parameter in signature.parameters.values():
        is_injected_variable = (
            parameter.name == "variables" and parameter.name not in schema_properties
        )
        if parameter.name in INTERNAL_PARAMETERS or is_injected_variable:
            internal_parameters.append(parameter.name)
        elif parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            variadic["positional"] = parameter.name
        elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
            variadic["keyword"] = parameter.name
        else:
            public_parameters.append(_parameter_contract(parameter))

    capabilities, where_mode = _common_controls(runtime_key)
    symbol = f"{function.__module__}.{function.__qualname__}"

    return {
        "runtime_key": runtime_key,
        "python_symbol": symbol,
        "signature": str(signature),
        "parameters": public_parameters,
        "internal_parameters": internal_parameters,
        "variadic": variadic,
        "capabilities": capabilities,
        "where_mode": where_mode,
        "docstring_schema_status": "available" if docstring_schema else "missing",
        "docstring_schema": docstring_schema,
        "plain_docstring": _plain_docstring(function, docstring_schema),
    }


def build_manifest(
    *,
    source_revision: str = "unversioned",
    root: Any | None = None,
) -> dict[str, Any]:
    """Build a deterministic manifest for the exposed recipe namespace."""
    if not source_revision.strip():
        raise ManifestError("source_revision must not be blank")

    recipe_root = root if root is not None else wrangles.recipe._recipe_wrangles
    entries = [
        _wrangle_contract(runtime_key, function)
        for runtime_key, function in _iter_callables(recipe_root)
    ]
    entries.sort(key=lambda entry: entry["runtime_key"])

    runtime_keys = [entry["runtime_key"] for entry in entries]
    duplicate_keys = sorted(
        {runtime_key for runtime_key in runtime_keys if runtime_keys.count(runtime_key) > 1}
    )
    if duplicate_keys:
        raise ManifestError(
            "Duplicate runtime keys in recipe namespace: " + ", ".join(duplicate_keys)
        )

    return {
        "$schema": SCHEMA_URL,
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "revision": source_revision,
        },
        "entry_count": len(entries),
        "wrangles": entries,
    }


def manifest_json(manifest: dict[str, Any]) -> str:
    """Serialize a manifest consistently across platforms."""
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the WranglesPY recipe-wrangle runtime manifest."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--source-revision",
        default=os.environ.get("GITHUB_SHA", "unversioned"),
        help="WranglesPY commit or release represented by the manifest.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(source_revision=args.source_revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(manifest_json(manifest), encoding="utf-8", newline="\n")
    print(f"Wrote {manifest['entry_count']} wrangles to {args.output}")


if __name__ == "__main__":
    main()
