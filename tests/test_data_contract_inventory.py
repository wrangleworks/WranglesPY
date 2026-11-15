"""The public operation inventory exposes migration gaps without declaring policies."""
import json
from types import SimpleNamespace

import pytest

from scripts import check_data_contracts as inventory_check
from wrangles._data_contracts import DataContract, data_contract


SCHEMA_DOC = """
type: object
description: Synthetic operation for inventory guard regressions.
properties: {}
"""


def operation(values):
    return values


operation.__doc__ = SCHEMA_DOC


def manifest(exemptions=None, casts=None, implementations=None):
    return {"schema_version": 1, "exemptions": exemptions or {}, "astype_str_exemptions": casts or {},
            "implementations": implementations or {}}


def exemption(function, *, family="legacy", reason="Retains the existing external provider boundary until its owning adapter migration."):
    return {"family": family, "owner": function.__module__, "reason": reason}


def test_every_schema_operation_and_bare_text_cast_is_classified():
    recorded = json.loads(inventory_check.INVENTORY_PATH.read_text(encoding="utf-8"))
    operations = inventory_check.discover_operations()
    assert operations, "An empty discovery result must not make the guard pass"
    failures = inventory_check.validate_operations(operations, recorded)
    failures.extend(inventory_check.validate_implementations(operations, recorded))
    failures.extend(inventory_check.validate_text_casts(
        inventory_check.find_text_casts(), recorded.get("astype_str_exemptions", {})))
    assert not failures, "\n".join(failures)


def test_discovery_includes_aliases_and_callable_children_and_avoids_cycles():
    def parent(values):
        return values

    parent.__doc__ = SCHEMA_DOC
    parent.child = operation
    parent.self_reference = parent
    root = SimpleNamespace(primary=parent, alias=parent,
                           main=SimpleNamespace(duplicate=operation),
                           pandas=SimpleNamespace(duplicate=operation), _hidden=operation)
    found = inventory_check.discover_operations(root)
    assert set(found) == {"alias", "alias.child", "primary", "primary.child"}
    assert found["alias"].function is found["primary"].function is parent
    assert found["alias.child"].function is operation


def test_discovery_uses_the_schema_reserved_word_mapping():
    found = inventory_check.discover_operations(SimpleNamespace(Try=operation),
                                                reserved_replacements={"Try": "try"})
    assert set(found) == {"try"}


def test_discovery_excludes_docstrings_without_parameter_schema():
    def helper():
        """An ordinary helper, not a public recipe schema."""
    assert inventory_check.discover_operations(SimpleNamespace(helper=helper)) == {}


def test_new_unclassified_operation_fails_even_when_existing_operation_is_exempt():
    recorded = manifest({"known": exemption(operation)})
    found = inventory_check.discover_operations(SimpleNamespace(known=operation, surprise=operation))
    failures = inventory_check.validate_operations(found, recorded)
    assert len(failures) == 1
    assert "surprise: unclassified operation" in failures[0]


def test_descriptor_is_read_from_the_actual_behavior_owner_and_its_alias():
    @data_contract("text_consumer", missing="none", non_text="stringify", output="text")
    def boundary(values):
        return [str(value) for value in values]

    boundary.__doc__ = SCHEMA_DOC
    found = inventory_check.discover_operations(SimpleNamespace(boundary=boundary, alias=boundary))
    assert found["boundary"].function is boundary
    assert found["alias"].contract is boundary.__data_contract__
    assert found["boundary"].contract == DataContract("text_consumer", "none", "stringify", "text", "")
    assert boundary([1, False]) == ["1", "False"]
    assert inventory_check.validate_operations(found, manifest()) == []
    failures = inventory_check.validate_operations(found, manifest({"boundary": exemption(boundary)}))
    assert any("remove duplicate exemption" in failure for failure in failures)


@pytest.mark.parametrize("entry", [
    {"family": "needs_review", "owner": __name__, "reason": "Awaiting deliberate review."},
    {"family": "legacy", "owner": "wrong.module", "reason": "Existing boundary."},
    {"family": "typed", "owner": __name__, "reason": ""},
    {"family": "legacy", "owner": __name__, "reason": "Existing boundary.", "missing": "empty"},
])
def test_incomplete_or_misattributed_exemptions_fail(entry):
    found = inventory_check.discover_operations(SimpleNamespace(boundary=operation))
    assert inventory_check.validate_operations(found, manifest({"boundary": entry}))


def test_removed_operation_leaves_a_failing_stale_exemption():
    failures = inventory_check.validate_operations({}, manifest({"retired": exemption(operation)}))
    assert failures == ["retired: stale exemption; operation is no longer schema-exposed"]


def test_scaffolding_adds_new_operations_as_needs_review_without_guessing_policy():
    found = inventory_check.discover_operations(SimpleNamespace(known=operation, new=operation))
    original = manifest({"known": exemption(operation, family="typed", reason="Numeric consumer preserves its typed inputs.")})
    updated = inventory_check.scaffold_inventory(found, original)
    assert updated["exemptions"]["known"] == original["exemptions"]["known"]
    assert "new" not in original["exemptions"]
    assert updated["exemptions"]["new"]["family"] == "needs_review"
    assert updated["implementations"]["new"]["engine"] == "needs_review"
    assert any("needs_review is not classified" in failure
               for failure in inventory_check.validate_operations(found, updated))


def test_write_inventory_cli_scaffolds_new_gaps_and_still_fails(tmp_path, monkeypatch):
    path = tmp_path / "inventory.json"
    original = manifest({"known": exemption(operation)})
    path.write_text(json.dumps(original), encoding="utf-8")
    found = inventory_check.discover_operations(SimpleNamespace(known=operation, new=operation))
    monkeypatch.setattr(inventory_check, "discover_operations", lambda: found)
    monkeypatch.setattr(inventory_check, "find_text_casts", lambda: [])
    monkeypatch.setattr(inventory_check.sys, "argv", [
        "check_data_contracts.py", "--inventory", str(path), "--write-inventory",
    ])
    assert inventory_check.main() == 1
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated["exemptions"]["known"] == original["exemptions"]["known"]
    assert updated["exemptions"]["new"]["family"] == "needs_review"
    assert updated["implementations"]["new"]["engine"] == "needs_review"


def test_core_engine_is_required_for_decorated_operations_and_each_alias():
    @data_contract("text_transform")
    def boundary(values):
        return values

    boundary.__doc__ = SCHEMA_DOC
    found = inventory_check.discover_operations(SimpleNamespace(boundary=boundary, alias=boundary))
    core = {"engine": "python", "core": "synthetic.text_transform",
            "notes": "Python performs the cell transform; the recipe wrapper owns pandas column assignment."}
    partial = manifest(implementations={"boundary": core})
    assert inventory_check.validate_operations(found, partial) == []
    assert inventory_check.validate_implementations(found, partial) == [
        "alias: missing core implementation classification",
    ]
    complete = manifest(implementations={"boundary": core, "alias": core})
    assert inventory_check.validate_implementations(found, complete) == []


@pytest.mark.parametrize("entry", [
    {"engine": "needs_review", "core": "needs_review", "notes": "Review is pending."},
    {"engine": "python", "core": "", "notes": "Missing core reference."},
    {"engine": "pandas", "core": "pandas.DataFrame.query", "notes": ""},
    {"engine": "python", "core": "synthetic.transform", "notes": "Python transform.", "missing": "empty"},
])
def test_unreviewed_or_policy_duplicating_core_implementations_fail(entry):
    found = inventory_check.discover_operations(SimpleNamespace(boundary=operation))
    assert inventory_check.validate_implementations(found, manifest(implementations={"boundary": entry}))


def test_removed_operations_leave_failing_stale_core_records():
    failures = inventory_check.validate_implementations({}, manifest(implementations={
        "retired": {"engine": "python", "core": "synthetic.retired", "notes": "Old Python transform."},
    }))
    assert failures == ["retired: stale core implementation record; operation is no longer schema-exposed"]


def test_scaffold_requires_implementation_review_even_when_callable_has_descriptor():
    @data_contract("typed")
    def boundary(values):
        return values

    boundary.__doc__ = SCHEMA_DOC
    found = inventory_check.discover_operations(SimpleNamespace(boundary=boundary))
    updated = inventory_check.scaffold_inventory(found, manifest())
    assert updated["exemptions"] == {}
    assert updated["implementations"]["boundary"]["engine"] == "needs_review"
    assert inventory_check.validate_implementations(found, updated)


def test_ast_guard_catches_builtin_string_casts_including_keyword_and_nested_function():
    source = '''
def boundary(frame):
    frame.astype(str)
    frame.astype(dtype="str")
    def nested():
        return frame.astype(builtins.str)
    frame.astype("string")  # Explicit nullable dtype, not Python stringification.
    return frame
'''
    casts = inventory_check.scan_text_casts(source, module="synthetic.owner", path="synthetic.py")
    assert [(cast.line, cast.function) for cast in casts] == [
        (3, "synthetic.owner.boundary"), (4, "synthetic.owner.boundary"),
        (6, "synthetic.owner.boundary.nested"),
    ]
    assert len(inventory_check.validate_text_casts(casts, {})) == 3
    assert inventory_check.validate_text_casts(casts, {
        "synthetic.owner.boundary": {"reason": "Synthetic reviewed compatibility boundary."},
        "synthetic.owner.boundary.nested": {"reason": "Synthetic nested compatibility boundary."},
    }) == []


def test_ast_guard_rejects_blank_module_wide_and_stale_exemptions():
    casts = inventory_check.scan_text_casts("frame.astype(str)", module="synthetic", path="synthetic.py")
    assert inventory_check.validate_text_casts(casts, {"synthetic.<module>": {"reason": "Too broad."}})
    assert inventory_check.validate_text_casts([], {"synthetic.old": {"reason": "No longer present."}})
    casts = inventory_check.scan_text_casts("def operation(frame):\n    return frame.astype(str)\n",
                                          module="synthetic", path="synthetic.py")
    assert inventory_check.validate_text_casts(casts, {"synthetic.operation": {"reason": ""}})
