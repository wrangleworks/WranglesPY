"""Generate the deterministic recipe-wrangle runtime contract manifest.

The manifest deliberately keeps runtime facts separate from curated Registry
content.  It inventories the recipe namespace, public Python signature, embedded
JSON Schema docstring, and common-control capabilities without trying to decide
which documentation wording is best.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import math
import re
import subprocess
import types
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterator

import yaml
import jsonschema


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

# Runtime imports are lazy: release validation does not require installing WranglesPY.


FORMAT = "wrangles-runtime-manifest"
FORMAT_VERSION = "0.1"
SCHEMA_URL = (
    "https://docs.wrangles.com/registry/schema/"
    "wrangles-runtime-manifest.schema.json"
)
SOURCE_REPOSITORY = "https://github.com/wrangleworks/WranglesPY"
ROOT = REPOSITORY_ROOT
SCHEMA_PATH = Path(__file__).with_name("wrangles-runtime-manifest.schema.json")
REPOSITORY = SOURCE_REPOSITORY
FILENAME = "wrangles-runtime-manifest.json"
KEY = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*")
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
REVISION = re.compile(r"[0-9a-f]{40}")
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


def _recipe_key(path: tuple[str, ...], config: Any) -> str:
    python_path = ".".join(path)
    replacements = {python_name: recipe_name for recipe_name, python_name in config.reserved_word_replacements.items()}
    if len(replacements) != len(config.reserved_word_replacements):
        raise ManifestError("Ambiguous reserved recipe names")
    key = replacements.get(python_path, python_path)
    if not KEY.fullmatch(key):
        raise ManifestError(f"Invalid runtime key: {key}")
    return key


def _iter_callables(obj: Any, path: tuple[str, ...] = (), *, config: Any = None,
                    ancestors: frozenset[int] = frozenset()) -> Iterator[tuple[str, Any]]:
    """Yield public recipe functions, including callable namespaces and aliases."""
    if config is None:
        from wrangles import config
    if id(obj) in ancestors:
        raise ManifestError(f"Cyclic runtime namespace: {'.'.join(path)}")
    if not isinstance(obj, types.ModuleType) and not inspect.isfunction(obj):
        raise ManifestError(f"Unsupported public runtime export: {'.'.join(path)}")
    if inspect.isfunction(obj):
        yield _recipe_key(path, config), obj
    for name in sorted(item for item in dir(obj) if not item.startswith("_")):
        if not path and name in SKIPPED_NAMESPACE_NAMES:
            continue
        yield from _iter_callables(getattr(obj, name), (*path, name), config=config,
                                   ancestors=ancestors | {id(obj)})


def _annotation_text(annotation: Any) -> str | None:
    if annotation is inspect.Parameter.empty:
        return None
    value = inspect.formatannotation(annotation)
    if re.search(r"\bat 0x[0-9a-fA-F]+", value) or "\\" in value:
        raise ManifestError("Nonportable runtime annotation")
    return value


def _parameter_contract(parameter: inspect.Parameter) -> dict[str, Any]:
    contract = {"name": parameter.name, "kind": parameter.kind.name.lower(),
                "required": parameter.default is inspect.Parameter.empty}
    annotation = _annotation_text(parameter.annotation)
    if annotation is not None:
        contract["annotation"] = annotation
    # A named object sentinel means omission; its stable name is in the signature.
    if parameter.default is not inspect.Parameter.empty and type(parameter.default) is not object:
        contract["default"] = json_value(parameter.default)
    return contract


def _parse_docstring_schema(runtime_key: str, function: Any) -> dict[str, Any] | None:
    docstring = inspect.getdoc(function)
    if not docstring:
        return None

    stripped = docstring.strip()
    schema_keys = ("type", "anyOf", "oneOf", "allOf", "$ref")
    looks_like_schema = stripped.startswith(tuple(f"{key}:" for key in schema_keys))
    try:
        parsed = yaml.safe_load(docstring)
    except yaml.YAMLError as error:
        if looks_like_schema:
            raise ManifestError(
                f"{runtime_key} has an invalid JSON Schema docstring: {error}"
            ) from error
        return None

    if isinstance(parsed, dict) and any(key in parsed for key in schema_keys):
        return parsed
    return None


def _plain_docstring(function: Any, schema: dict[str, Any] | None) -> str | None:
    """Return useful code-owned prose only when no schema docstring exists."""
    if schema is not None:
        return None
    docstring = inspect.getdoc(function)
    return docstring or None


def _common_controls(runtime_key: str, config: Any) -> tuple[dict[str, bool], str]:
    implementation_key = config.reserved_word_replacements.get(runtime_key, runtime_key)
    where_supported = implementation_key not in config.where_not_implemented
    where_mode = "unsupported"
    if where_supported:
        where_mode = (
            "overwrite_output"
            if implementation_key in config.where_overwrite_output
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


def _wrangle_contract(runtime_key: str, function: Any, config: Any) -> dict[str, Any]:
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

    capabilities, where_mode = _common_controls(runtime_key, config)
    symbol = f"{function.__module__}.{function.__qualname__}"

    entry = {
        "runtime_key": runtime_key,
        "python_symbol": symbol,
        "signature": _signature_text(function, signature),
        "parameters": public_parameters,
        "internal_parameters": internal_parameters,
        "variadic": variadic,
        "capabilities": capabilities,
        "where_mode": where_mode,
        "docstring_schema_status": "available" if docstring_schema else "missing",
        "docstring_schema": docstring_schema,
        "plain_docstring": _plain_docstring(function, docstring_schema),
    }
    if hasattr(function, "__catalog_id__"):
        entry["catalog_id"] = function.__catalog_id__
    return entry


def build_manifest(*, source_revision: str, root: Any | None = None,
                   source_version: str | None = None, config: Any = None) -> dict[str, Any]:
    """Export runtime facts using the original Registry contract and parameter rules."""
    if root is None:
        from wrangles import recipe
        root = recipe._recipe_wrangles
    if config is None:
        from wrangles import config
    entries = []
    for runtime_key, function in _iter_callables(root, config=config):
        try:
            entries.append(_wrangle_contract(runtime_key, function, config))
        except (ValueError, TypeError) as error:
            raise ManifestError(f"Cannot export {runtime_key}: {error}") from error
    if not entries:
        raise ManifestError("Runtime discovery produced no operations")
    entries.sort(key=lambda entry: entry["runtime_key"])
    manifest = {"$schema": SCHEMA_URL, "format": FORMAT, "format_version": FORMAT_VERSION,
                "source": {"repository": SOURCE_REPOSITORY, "revision": source_revision,
                           "version": source_version or read_version(REPOSITORY_ROOT)},
                "entry_count": len(entries), "wrangles": entries}
    validate_manifest(manifest)
    return manifest


def manifest_json(manifest: dict[str, Any]) -> str:
    """Serialize the validated contract consistently across platforms."""
    validate_manifest(manifest)
    return json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def json_value(value):
    """Reject lossy/nonportable defaults instead of serializing their repr."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [json_value(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: json_value(value[key]) for key in sorted(value)}
    raise ValueError(f"Non-JSON runtime metadata/default: {type(value).__name__}")


class _NamedDefault:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


def _signature_text(function, signature):
    parameters = []
    for parameter in signature.parameters.values():
        _annotation_text(parameter.annotation)
        if parameter.default is not inspect.Parameter.empty:
            if type(parameter.default) is object:
                names = [name for name, value in function.__globals__.items()
                         if value is parameter.default and name.isidentifier()]
                if len(names) != 1:
                    raise ManifestError(f"Default sentinel for {parameter.name} needs one stable module name")
                default = _NamedDefault(function.__module__ + "." + names[0])
            else:
                default = json_value(parameter.default)
            parameter = parameter.replace(default=default)
        parameters.append(parameter)
    _annotation_text(signature.return_annotation)
    return str(signature.replace(parameters=parameters))


def read_version(root):
    tree = ast.parse((Path(root) / "setup.py").read_text(encoding="utf-8"))
    versions = [keyword.value.value for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setup"
                for keyword in node.keywords if keyword.arg == "version"
                and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str)]
    if len(versions) != 1 or not VERSION.fullmatch(versions[0]):
        raise ManifestError("setup.py must declare one literal stable version")
    return versions[0]


def validate_manifest(manifest):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema).validate(manifest)
    except jsonschema.ValidationError as error:
        raise ValueError(f"Invalid runtime manifest at {list(error.absolute_path)}: {error.message}") from error
    json_value(manifest)
    if manifest["$schema"] != SCHEMA_URL:
        raise ValueError("Unexpected runtime schema URL")
    if manifest["source"]["repository"] != REPOSITORY:
        raise ValueError("Unexpected runtime repository")
    if not VERSION.fullmatch(manifest["source"]["version"]) or not REVISION.fullmatch(manifest["source"]["revision"]):
        raise ValueError("Manifest requires an exact stable version and full Git revision")
    if not manifest["wrangles"] or manifest["entry_count"] != len(manifest["wrangles"]):
        raise ValueError("Invalid runtime entry_count")
    keys, identities = set(), set()
    for entry in manifest["wrangles"]:
        key = entry["runtime_key"]
        if key in keys:
            raise ValueError(f"Duplicate runtime key: {key}")
        keys.add(key)
        identity = entry.get("catalog_id")
        if identity is not None:
            if int(identity) > 9223372036854775807 or identity in identities:
                raise ValueError("Invalid or duplicate catalog identity")
            identities.add(identity)
        names = [parameter["name"] for parameter in entry["parameters"]] + entry["internal_parameters"]
        names += [value for value in entry["variadic"].values() if value is not None]
        if len(set(names)) != len(names):
            raise ValueError(f"Duplicate parameter for {key}")
        for parameter in entry["parameters"]:
            if parameter["required"] and "default" in parameter:
                raise ValueError(f"Inconsistent required/default parameter for {key}")
        supported = entry["where_mode"] != "unsupported"
        if entry["capabilities"] != {"if": True, "where": supported, "where_params": supported}:
            raise ValueError(f"Inconsistent runtime capabilities for {key}")
        if (entry["docstring_schema_status"] == "available") != (entry["docstring_schema"] is not None):
            raise ValueError(f"Inconsistent docstring schema for {key}")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8").strip()


def read_provenance(root, tag=None, expected_revision=None, allow_dirty=False):
    root = Path(root)
    version = read_version(root)
    revision = git(root, "rev-parse", "--verify", "HEAD")
    if not REVISION.fullmatch(revision) or (expected_revision is not None and expected_revision != revision):
        raise ValueError("Checkout revision does not match the expected commit")
    if tag is not None:
        if allow_dirty or tag != "v" + version:
            raise ValueError("Release tag must match package version; dirty release exports are forbidden")
        if git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}") != revision:
            raise ValueError("Release tag does not point to the exported commit")
    paths = ["wrangles", "setup.py", "requirements.txt", "requirements-full.txt", "constraints",
             "schema/generate_wrangle_manifest.py", "schema/wrangles-runtime-manifest.schema.json"]
    if not allow_dirty and git(root, "status", "--porcelain", "--untracked-files=normal", "--", *paths):
        raise ValueError("Runtime/export inputs are dirty; commit them or use --allow-dirty for a local preview only")
    return version, revision


def export_checkout(root=ROOT, tag=None, expected_revision=None, allow_dirty=False):
    root = Path(root).resolve()
    if not (root / "wrangles/__init__.py").is_file():
        raise ValueError("Selected checkout has no WranglesPY source tree")
    version, revision = read_provenance(root, tag, expected_revision, allow_dirty)
    sys.path.insert(0, str(root))
    import wrangles
    from wrangles import config, recipe
    if Path(wrangles.__file__).resolve() != root / "wrangles/__init__.py":
        raise ValueError("Imported WranglesPY does not belong to the selected checkout")
    return build_manifest(root=recipe._recipe_wrangles, config=config, source_version=version, source_revision=revision)


def write_artifacts(manifest, output):
    validate_manifest(manifest)
    content = manifest_json(manifest).encode("utf-8")
    checksum = hashlib.sha256(content).hexdigest()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / FILENAME).write_bytes(content)
    (output / (FILENAME + ".sha256")).write_bytes(f"{checksum}  {FILENAME}\n".encode("ascii"))
    return checksum


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output", type=Path, help=f"JSON file (default: {DEFAULT_OUTPUT})")
    output.add_argument("--artifact-dir", type=Path, help="Write the release manifest and SHA-256 sidecar")
    parser.add_argument("--source-revision", "--revision", dest="source_revision",
                        default=os.environ.get("GITHUB_SHA"), help="Expected full checkout SHA")
    parser.add_argument("--tag", help="Stable vN.N.N tag; must resolve to this checkout")
    parser.add_argument("--allow-dirty", action="store_true", help="Local preview only; forbidden with --tag")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    manifest = export_checkout(tag=args.tag, expected_revision=args.source_revision, allow_dirty=args.allow_dirty)
    if args.artifact_dir is not None:
        checksum = write_artifacts(manifest, args.artifact_dir)
        output = args.artifact_dir / FILENAME
    else:
        output = args.output or DEFAULT_OUTPUT
        content = manifest_json(manifest).encode("utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        checksum = hashlib.sha256(content).hexdigest()
    print(json.dumps({"source": manifest["source"], "entry_count": manifest["entry_count"],
                      "sha256": checksum, "manifest": str(output)}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, ImportError, OSError, subprocess.SubprocessError) as error:
        print(f"Runtime manifest export failed: {error}", file=sys.stderr)
        sys.exit(1)
