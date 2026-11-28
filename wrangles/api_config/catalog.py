"""Export public caller choices from the same resolution layers as execution."""

import argparse
import json
import os
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile

from .. import ai_config
from .parameters import public_schema
from .resolver import _effective, _members, _default, choices, load_snapshot


def _public_choice(config, choice, cell, policy):
    resolved = _effective(config, choice, cell, policy, {}, {}, True)
    item = choice.selection()
    if choice.status:
        item["status"] = choice.status
    item["defaults"] = {key: resolved.defaults[key] for key in (
        "decimals", "default_concurrency", "request_timeout_seconds", "retries", "include_raw_response"
    ) if key in resolved.defaults}
    if "enabled" in resolved.defaults.get("cache", {}):
        item["defaults"]["cache"] = {"enabled": resolved.defaults["cache"]["enabled"]}
    api = resolved.api_config
    if resolved.schemas:
        public_defs = {"#/$defs/" + name for name in api.get("public_definitions", [])}
        schema = public_schema(resolved.schemas, api.get("public_parameters", []), public_defs)
        item["parameter_schema"] = schema
        values = {key: value for key, value in resolved.parameters.items()
                  if key in schema["properties"] and type(value) in (str, bool, int, float)}
        if values:
            item["defaults"]["parameters"] = values
    return item


def export_catalog(snapshot=None):
    """Build one distributable catalog. Omit private transport and schema metadata."""
    snap = snapshot if snapshot is not None else load_snapshot()
    config = snap._config
    callers = {}
    for name, settings in config["callers"].items():
        operations = {}
        callers[name] = {"operations": operations}
        for operation, definition in settings["operations"].items():
            if not definition["actions"]:
                continue
            actions = {}
            operations[operation] = {"actions": actions}
            for action in definition["actions"]:
                cell, policy = _members(config, operation, name, action)
                options = choices(config, operation, policy)
                entry = {"choices": [_public_choice(config, option, cell, policy) for option in options
                                     if option.status != "retired"]}
                if "default_selection" in cell:
                    entry["default_selection"] = _default(options, cell["default_selection"]).selection()
                actions[action] = entry
    return {"schema_version": 1, "package_version": version("wrangles"),
            "configuration": {"source": snap.source, "version": snap.version, "revision": snap.revision},
            "callers": callers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--config", type=Path, help="Export this complete replacement configuration")
    source.add_argument("--packaged", action="store_true", help="Use the packaged configuration, ignoring the environment")
    parser.add_argument("--output-dir", type=Path, help="Write a revision-specific artifact (default: stdout)")
    args = parser.parse_args()
    snap = load_snapshot(ai_config._PACKAGED_CONFIG if args.packaged else args.config)
    catalog = export_catalog(snap)
    contents = json.dumps(catalog, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output_dir is None:
        print(contents, end="")
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / f"api-catalog-v1-{catalog['package_version']}-{snap.source}-{snap.revision}.json"
    data = contents.encode("utf-8")
    temp = NamedTemporaryFile(dir=target.parent, delete=False)
    path = Path(temp.name)
    try:
        with temp:
            temp.write(data)
        try:
            # Publish the completed file atomically, including concurrent exports.
            os.link(path, target)
        except FileExistsError:
            if target.read_bytes() != data:
                parser.exit(1, "A different catalog already exists for this package and configuration revision.\n")
    finally:
        path.unlink(missing_ok=True)
    print(target)
