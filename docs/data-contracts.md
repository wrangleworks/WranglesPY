# Data contracts for wrangles

[Back to the overview](../README.md)

For the underlying Python, pandas, and JSON behavior, read
[Missing values across Python, pandas, and JSON](missing-values.md).

This preparatory layer makes data handling explicit on pandas 2.3.3. It does not
enable pandas 3 or change pandas' process-wide string or Copy-on-Write settings.
PyArrow is part of the baseline installation; the supported pandas range remains
`>=2.3.3,<3.0` until the separate migration is validated.

## Shared mechanics, explicit policies

The internal [`_data_contracts.py`](../wrangles/_data_contracts.py) module owns
the reusable mechanics. Owning wrangles use these adapters at their input or
output boundaries, so recipes and direct DataFrame accessors use the same code.

| Adapter | Contract |
| --- | --- |
| `is_missing_scalar` | Recognizes scalar nulls such as `None`, NaN, `pd.NA`, and NaT. Zero, false, literal marker strings, and containers are values. |
| `is_empty_scalar` | Adds empty text to missing scalars; whitespace-only text is empty only when explicitly requested. |
| `text_values`, `text_matrix`, `joined_text_rows` | Prepare temporary text inputs without overwriting source columns. Series formatting preserves pandas' dtype-specific numeric/date formatting; ordinary sequences use Python formatting. |
| `normalize_missing_values`, `structured_values` | Opt in to Python `None` for missing values in lists/dictionary values. Preserve native types and literal strings. These are not JSON validators. |
| `assign_result` | Assigns values positionally, validates masks/lengths before mutation, and preserves indexes and untouched cells. Only a destination that needs mixed/structured storage is promoted. |

Text policies are named rather than inferred from truthiness:

- `missing='stringify'` preserves the legacy spelling of the actual missing
  sentinel (`"None"`, `"nan"`, `"<NA>"`, or `"NaT"`). This deliberately records
  existing text-consumer behavior; it is not a universal missing-value policy.
- `missing='empty'` produces empty text; `none` produces the literal `"None"`;
  `preserve` keeps the scalar; `raise` rejects it.
- `non_text='stringify'`, `preserve`, or `raise` determines whether non-text
  cells are converted, retained, or rejected. Containers remain whole cells.

The `@data_contract(...)` decorator records the family and policies on the
original callable. It does not wrap the function or normalize a DataFrame.
Signatures, YAML schema docstrings, aliases, and callable namespace children
therefore retain their existing discovery and parameter-injection behavior.

## Behavior and remaining decisions

The current adoption centralizes text boundaries in extraction, comparison,
splitting, formatting, model wrappers, and concatenation. Mixed matrix lookup
writes use the shared destination adapter, including non-default/duplicate
indexes. Case/cleanup operations continue preserving non-text values.

Dictionary builders now keep native booleans and literal `"True"`, `"False"`,
and `"None"` strings distinct, rather than stringifying and guessing their types
afterward. Missing structured values become Python `None`; source containers
are not mutated. The existing `convert` JSON validator remains strict and
continues rejecting unsupported/non-finite input.

Key/value builders retain dictionary keys as supplied after pandas row
extraction; missing-value normalization applies to values. Collapsing distinct
missing keys into one key would silently discard a pair.

Operation-specific empty-value rules are still visible. For example,
`merge.to_dict(include_empty=False)` retains its legacy zero filtering, whereas
`merge.key_value_pairs(skip_empty=True)` preserves zero and false. The operation
inventory records these as reviewable differences; the shared missing detector
does not silently redefine every existing option.

The operation audit also distinguishes the DataFrame adapter from the core
execution engine: Python, pandas, NumPy/native, SQL, external service, or hybrid.
Classification alone is not evidence that an operation's entire behavior has
been tested. Remaining exemptions identify typed, orchestration, or legacy
boundaries explicitly and retain their reasons for a later focused slice.

## Verification and adding an operation

Run the credential-free selection described in the [README](../README.md#local-development).
The focused dependency-floor CI job runs the contracts on pandas 2.3.3 and
PyArrow 22.0.0. Tests also scope pandas' future string inference and CoW modes to
individual cases; they do not enable them in application code.

```powershell
.venv\Scripts\python.exe scripts/check_data_contracts.py
.venv\Scripts\python.exe -m pytest -c pytest-local.ini tests/test_data_contracts.py tests/test_data_contract_boundaries.py tests/test_data_contract_outputs.py tests/test_data_contract_inventory.py
```

The [reviewed inventory](../tests/fixtures/data-contracts/inventory.json) covers
schema-exposed operations, aliases, and callable namespace children. A new
operation must have a descriptor or a justified exemption, plus a core-engine
record. CI rejects unclassified/stale entries and raw `.astype(str)` boundaries
outside explicitly reviewed exceptions. The scaffolding command
`python scripts/check_data_contracts.py --write-inventory` deliberately leaves
new entries as `needs_review` and fails until their policies are reviewed.

Add behavioral cases for the affected family: scalar nulls, empty/whitespace
text, literal markers, zero/false, containers, typed numeric/date formatting,
first/later recipe steps, direct accessors, partial writes, and duplicate indexes
where applicable. Test clear semantic fixes explicitly rather than asserting
only a decorator or implementation detail.

After this preparation merges, the separate pandas 3.1.1 work can expand the
compatibility matrix against these contracts. Removing defensive copies,
changing additional dtype defaults, and performance tuning remain later work.
