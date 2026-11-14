# Data-contract inventory

This fixture is derived from the schema-exposed Python callables in
`wrangles.recipe_wrangles`. It contains no customer records, credentials or
external-service responses. Each exemption is keyed by its public operation
name, with a `legacy`, `typed` or `orchestration` family, its implementation's
owner module, and a reason for retaining that boundary during phased adoption.

Policies attached to callables through `__data_contract__` remain in the owning
source file and must not be repeated in this inventory. Aliases are discovered
individually; aliases of decorated functions inherit the same descriptor.

The independent `implementations` map covers **every** discovered operation,
including decorated operations and aliases. Each record identifies an `engine`
(`python`, `pandas`, `numpy`, `sql`, `external` or `hybrid`), a reviewed `core`
function/backend reference, and brief `notes`. Classify the actual transform:
a pandas recipe adapter passing cell lists into Python does not make that core
transform a pandas implementation. Use `hybrid` when branches or substantial
combined stages use different engines, explaining those paths in the notes.
These records do not repeat the decorator's missing-value or output policies.

Run the guard from the repository root:

```shell
python scripts/check_data_contracts.py
```

To scaffold newly exposed, unclassified operations:

```shell
python scripts/check_data_contracts.py --write-inventory
```

The scaffold uses `needs_review` for new contract gaps and core implementation
records, and deliberately continues to fail checks.
Review each new operation, then attach a descriptor or replace that placeholder
with an explicit exemption family and reason. Remove exemptions when the
implementation acquires a descriptor; removed or renamed operations leave
stale exemptions that also fail the guard.

`astype_str_exemptions` is a separate function-keyed map of reasons for any
deliberately retained `.astype(str)` boundary. The AST guard also catches
`astype('str')`, `astype(dtype=str)` and `astype(builtins.str)`. Explicit nullable
`astype('string')` conversions are outside that Python-stringification guard.
An empty map means no such exceptions have been approved. This is an operation
inventory rather than a row-oriented dataset; its entry count changes with
reviewed operations and is reported by the guard.
