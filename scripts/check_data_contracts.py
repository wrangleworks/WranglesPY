"""Check classification of schema-exposed recipe operations and text casts.

Descriptors on the implementation callable own adapted policies. The inventory
contains only explicit exemptions for boundaries awaiting that migration.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import inspect
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import yaml


# User-editable defaults, anchored to this checkout rather than the caller.
REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO_ROOT / "tests/fixtures/data-contracts/inventory.json"
RECIPE_SOURCE = REPO_ROOT / "wrangles/recipe_wrangles"
EXEMPT_FAMILIES = frozenset({"legacy", "typed", "orchestration"})
ENGINES = frozenset({"python", "pandas", "numpy", "sql", "external", "hybrid"})


@dataclass(frozen=True)
class Operation:
    name: str
    function: object
    owner: str

    @property
    def contract(self):
        return getattr(self.function, "__data_contract__", None)


def discover_operations(namespace=None, *, reserved_replacements=None):
    """Mirror schema traversal, retaining alias paths and callable children."""
    if namespace is None:
        sys.path.insert(0, str(REPO_ROOT))
        import wrangles

        namespace = wrangles.recipe._recipe_wrangles
        reserved_replacements = {value: key for key, value in
                                 wrangles.config.reserved_word_replacements.items()}
    reserved_replacements = reserved_replacements or {}
    module_prefix = namespace.__name__ if isinstance(namespace, ModuleType) else None
    found = {}

    def walk(obj, path, ancestors):
        if id(obj) in ancestors:
            return
        if callable(obj) and path:
            try:
                schema = yaml.safe_load(obj.__doc__)
            except (yaml.YAMLError, TypeError):
                schema = None
            if isinstance(schema, dict) and ("type" in schema or "anyOf" in schema):
                name = reserved_replacements.get(path, path)
                found[name] = Operation(name, obj, getattr(obj, "__module__", "unknown"))

        # Imported third-party modules/classes are not operation namespaces.
        # Functions can also carry dotted children (standardize, lookup).
        if isinstance(obj, ModuleType):
            if module_prefix and not obj.__name__.startswith(module_prefix):
                return
        elif not (inspect.isfunction(obj) or isinstance(obj, SimpleNamespace)):
            return
        ancestors = ancestors | {id(obj)}
        for name in sorted(dir(obj)):
            if name.startswith("_") or name in {"main", "pandas"}:
                continue
            child = getattr(obj, name)
            if child is not obj:
                walk(child, f"{path}.{name}" if path else name, ancestors)

    walk(namespace, "", frozenset())
    return dict(sorted(found.items()))


def _reason_valid(entry):
    return isinstance(entry, dict) and isinstance(entry.get("reason"), str) and bool(entry["reason"].strip())


def validate_operations(operations, inventory):
    """Return actionable failures without executing any recipe operation."""
    from wrangles._data_contracts import (
        DataContract, FAMILIES, MISSING_POLICIES, NON_TEXT_POLICIES, OUTPUT_KINDS,
    )

    errors = []
    if inventory.get("schema_version") != 1:
        errors.append("Inventory schema_version must be 1")
    exemptions = inventory.get("exemptions", {})
    if not isinstance(exemptions, dict):
        return errors + ["Inventory exemptions must be an object keyed by operation"]
    for name, operation in operations.items():
        descriptor = operation.contract
        if descriptor is not None:
            if name in exemptions:
                errors.append(f"{name}: remove duplicate exemption; its callable descriptor owns the policy")
            if not isinstance(descriptor, DataContract):
                errors.append(f"{name}: __data_contract__ must be a DataContract on the callable")
                continue
            for field, choices in (("family", FAMILIES), ("missing", MISSING_POLICIES),
                                   ("non_text", NON_TEXT_POLICIES), ("output", OUTPUT_KINDS)):
                if getattr(descriptor, field) not in choices:
                    errors.append(f"{name}: unsupported descriptor {field}={getattr(descriptor, field)!r}")
            continue
        exemption = exemptions.get(name)
        if exemption is None:
            errors.append(f"{name}: unclassified operation owned by {operation.owner}; add a descriptor or reviewed exemption")
        elif not _reason_valid(exemption):
            errors.append(f"{name}: exemption needs a non-empty reason")
        elif set(exemption) - {"family", "owner", "reason"}:
            errors.append(f"{name}: exemption may contain only family, owner, and reason; policies belong on the callable")
        elif exemption.get("family") not in EXEMPT_FAMILIES:
            errors.append(f"{name}: exemption family must be legacy, typed, or orchestration; needs_review is not classified")
        elif exemption.get("owner") != operation.owner:
            errors.append(f"{name}: exemption owner must be {operation.owner}")
    for name in sorted(set(exemptions) - set(operations)):
        errors.append(f"{name}: stale exemption; operation is no longer schema-exposed")
    return errors


def validate_implementations(operations, inventory):
    """Classify the underlying transform independently of its frame adapter."""
    implementations = inventory.get("implementations", {})
    if not isinstance(implementations, dict):
        return ["Inventory implementations must be an object keyed by operation"]
    errors = []
    for name in operations:
        entry = implementations.get(name)
        if not isinstance(entry, dict):
            errors.append(f"{name}: missing core implementation classification")
            continue
        unexpected = set(entry) - {"engine", "core", "notes"}
        if unexpected:
            errors.append(f"{name}: implementation record has unsupported fields {sorted(unexpected)}; contract policies belong on the callable")
        if entry.get("engine") not in ENGINES:
            errors.append(f"{name}: core engine must be one of {', '.join(sorted(ENGINES))}; needs_review is not classified")
        if not isinstance(entry.get("core"), str) or not entry["core"].strip() or entry["core"] == "needs_review":
            errors.append(f"{name}: core implementation needs a reviewed function or backend reference")
        if not isinstance(entry.get("notes"), str) or not entry["notes"].strip():
            errors.append(f"{name}: core implementation needs notes distinguishing the transform from its DataFrame adapter")
    for name in sorted(set(implementations) - set(operations)):
        errors.append(f"{name}: stale core implementation record; operation is no longer schema-exposed")
    return errors


@dataclass(frozen=True)
class TextCast:
    path: str
    line: int
    function: str


def scan_text_casts(source, *, module, path):
    """Find implicit stringification, including dtype=str and astype('str')."""
    found = []

    def is_str(node):
        return (isinstance(node, ast.Name) and node.id == "str"
                or isinstance(node, ast.Constant) and node.value == "str"
                or isinstance(node, ast.Attribute) and node.attr == "str"
                and isinstance(node.value, ast.Name) and node.value.id == "builtins")

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.scope = []

        def visit_FunctionDef(self, node):
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "astype":
                dtype = node.args[0] if node.args else next(
                    (keyword.value for keyword in node.keywords if keyword.arg == "dtype"), None)
                if dtype is not None and is_str(dtype):
                    owner = ".".join([module, *self.scope]) if self.scope else f"{module}.<module>"
                    found.append(TextCast(str(path), node.lineno, owner))
            self.generic_visit(node)

    Visitor().visit(ast.parse(source, filename=str(path)))
    return found


def find_text_casts(source_root=RECIPE_SOURCE):
    source_root = Path(source_root)
    found = []
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).with_suffix("")
        module = ".".join(["wrangles", "recipe_wrangles", *relative.parts])
        found.extend(scan_text_casts(path.read_text(encoding="utf-8-sig"), module=module, path=path))
    return found


def validate_text_casts(casts, exemptions):
    if not isinstance(exemptions, dict):
        return ["astype_str_exemptions must be an object keyed by qualified function"]
    errors = []
    owners = {cast.function for cast in casts}
    for cast in casts:
        exemption = exemptions.get(cast.function)
        if exemption is None:
            errors.append(f"{cast.path}:{cast.line}: bare astype(str) in {cast.function}; use an explicit adapter")
        elif not _reason_valid(exemption) or cast.function.endswith(".<module>"):
            errors.append(f"{cast.function}: text-cast exemption requires a function-specific reason")
    for name in sorted(set(exemptions) - owners):
        errors.append(f"{name}: stale text-cast exemption; no matching astype(str) call")
    return errors


def scaffold_inventory(operations, inventory):
    """Add new gaps for review; never guess a policy or remove existing notes."""
    result = {**inventory, "schema_version": 1,
              "exemptions": dict(inventory.get("exemptions", {})),
              "implementations": dict(inventory.get("implementations", {})),
              "astype_str_exemptions": dict(inventory.get("astype_str_exemptions", {}))}
    for name, operation in operations.items():
        if operation.contract is None and name not in result["exemptions"]:
            result["exemptions"][name] = {
                "family": "needs_review", "owner": operation.owner,
                "reason": "Review this boundary and select an explicit exemption family or attach a descriptor.",
            }
        if name not in result["implementations"]:
            result["implementations"][name] = {
                "engine": "needs_review", "core": "needs_review",
                "notes": "Identify the core transform/backend, separately from its pandas DataFrame adapter.",
            }
    result["exemptions"] = dict(sorted(result["exemptions"].items()))
    result["implementations"] = dict(sorted(result["implementations"].items()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--write-inventory", action="store_true",
                        help="Scaffold new operations as needs_review; checks still fail until reviewed")
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8")) if args.inventory.exists() else {}
    operations = discover_operations()
    if args.write_inventory:
        inventory = scaffold_inventory(operations, inventory)
        args.inventory.parent.mkdir(parents=True, exist_ok=True)
        args.inventory.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    errors = validate_operations(operations, inventory)
    errors.extend(validate_implementations(operations, inventory))
    casts = find_text_casts()
    errors.extend(validate_text_casts(casts, inventory.get("astype_str_exemptions", {})))
    print(f"Data contracts: {len(operations)} schema operations, "
          f"{sum(operation.contract is not None for operation in operations.values())} descriptors, "
          f"{len(inventory.get('exemptions', {}))} exemptions, "
          f"{len(inventory.get('implementations', {}))} core implementation records, {len(casts)} bare text casts")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
