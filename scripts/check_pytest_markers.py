"""
Validate pytest marker configuration against marker usage in tests.

This keeps the local/offline and integration pytest configs aligned and makes
new live-test markers explicit instead of letting them drift silently.
"""
from __future__ import annotations

import ast
import configparser
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTEST_CONFIGS = [
    REPO_ROOT / "setup.cfg",
    REPO_ROOT / "pytest-local.ini",
    REPO_ROOT / "pytest-integration.ini",
]
REQUIRED_LOCAL_EXPRESSION_PARTS = ("not integration", "not slow")
REQUIRED_INTEGRATION_EXPRESSION = "integration"
BUILTIN_MARKERS = {
    "anyio",
    "filterwarnings",
    "parametrize",
    "skip",
    "skipif",
    "tryfirst",
    "trylast",
    "usefixtures",
    "xfail",
}


def _pytest_section_name(path: Path) -> str:
    return "tool:pytest" if path.name == "setup.cfg" else "pytest"


def _read_pytest_config(path: Path) -> configparser.SectionProxy:
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    section = _pytest_section_name(path)
    if not parser.has_section(section):
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} is missing [{section}]")
    return parser[section]


def marker_definitions(path: Path) -> dict[str, str]:
    section = _read_pytest_config(path)
    if "markers" not in section:
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} is missing pytest markers")

    markers = {}
    for raw_line in section["markers"].splitlines():
        line = raw_line.strip()
        if not line:
            continue
        name, _, description = line.partition(":")
        name = name.strip()
        description = description.strip()
        if not name or not description:
            raise AssertionError(
                f"{path.relative_to(REPO_ROOT)} has an invalid marker line: {raw_line!r}"
            )
        markers[name] = description
    return markers


def marker_calls(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        parent = node.value
        if (
            isinstance(parent, ast.Attribute)
            and parent.attr == "mark"
            and isinstance(parent.value, ast.Name)
            and parent.value.id == "pytest"
        ):
            names.add(node.attr)

    # Some legacy skipif decorators use the compact string form:
    # @pytest.mark.skipif("OPENAI_API_KEY" not in os.environ, ...)
    for match in re.finditer(r"pytest\.mark\.([A-Za-z_][A-Za-z0-9_]*)", source):
        names.add(match.group(1))
    return names


def used_markers() -> dict[str, list[Path]]:
    usages: dict[str, list[Path]] = {}
    for path in sorted((REPO_ROOT / "tests").rglob("test*.py")):
        for marker in marker_calls(path):
            usages.setdefault(marker, []).append(path)
    return usages


def _addopts(path: Path) -> str:
    section = _read_pytest_config(path)
    return " ".join(section.get("addopts", "").split())


def validate() -> list[str]:
    errors = []
    definitions_by_config = {path: marker_definitions(path) for path in PYTEST_CONFIGS}

    baseline = definitions_by_config[PYTEST_CONFIGS[0]]
    for path, definitions in definitions_by_config.items():
        if definitions != baseline:
            errors.append(
                f"{path.relative_to(REPO_ROOT)} marker definitions differ from "
                f"{PYTEST_CONFIGS[0].relative_to(REPO_ROOT)}"
            )

    declared = set(baseline) | BUILTIN_MARKERS
    for marker, paths in used_markers().items():
        if marker in declared:
            continue
        formatted_paths = ", ".join(str(path.relative_to(REPO_ROOT)) for path in paths)
        errors.append(f"pytest marker '{marker}' is used but not registered: {formatted_paths}")

    local_addopts = _addopts(REPO_ROOT / "pytest-local.ini")
    for expression in REQUIRED_LOCAL_EXPRESSION_PARTS:
        if expression not in local_addopts:
            errors.append(f"pytest-local.ini addopts must exclude '{expression}'")

    integration_addopts = _addopts(REPO_ROOT / "pytest-integration.ini")
    if REQUIRED_INTEGRATION_EXPRESSION not in integration_addopts:
        errors.append("pytest-integration.ini addopts must select integration tests")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("pytest marker configuration is consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
