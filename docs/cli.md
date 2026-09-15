# Wrangles command-line interface

## Validate a saved Extract-AI definition locally

```powershell
wrangles model validate "power supply.json"
$result = wrangles model validate "power supply.json" --json | ConvertFrom-Json
$LASTEXITCODE
```

Input is a UTF-8 JSON document (an optional UTF-8 BOM is accepted):

```json
{
  "Settings": {},
  "Columns": ["Find", "Type", "Default"],
  "Data": [["Voltage", "number", 0]]
}
```

Validation uses the same saved-model authoring contract as `train.extract` and
its recipe connector. `Find` is the only universally required heading. Optional
headings can be omitted or reordered; the legacy seven-column layout, paired
examples, all known headings, and additional columns are supported. The command
reads the file without modifying it. It makes no service, authentication, model
write, or extraction requests.

The top-level document must be JSON, not YAML. Structured cells retain the shared
contract's JSON/YAML-compatible values and shorthand. Duplicate JSON object keys
and non-finite numeric literals are rejected rather than silently discarded.

Successful authoring validation does **not** guarantee runtime compatibility or
extraction quality. The existing local compiler is also run as a separate check.
A compiler rejection produces a warning and `validation.runtime: "incompatible"`;
it does not change authoring success or the exit code. `"compatible"` means only
that this local compilation passed, without a provider request or extraction.
No definition values are rewritten or printed by validation.

## Result format

With `--json`, model validation writes exactly one JSON result to stdout.
Diagnostics and warnings go to stderr. Do not merge stderr into stdout when
piping to `ConvertFrom-Json`. Help intentionally prints normal help text.

```json
{
  "schema_version": 1,
  "command": "model.validate",
  "outcome": "valid",
  "model_id": null,
  "readiness": "not_checked",
  "verification": "not_checked",
  "validation": {
    "scope": "saved-model-authoring",
    "runtime": "compatible",
    "rows": 1,
    "columns": 3,
    "warnings": []
  },
  "error": null
}
```

`schema_version` versions this result envelope. Consumers should tolerate new
fields. `outcome` is `valid`, `invalid`, `error`, or `interrupted` for validation.
`validation` is null on failure. `rows` counts all submitted data rows, including
blank rows; it is not a count of compiled extraction attributes.

Errors contain `code` and `message`, plus location information when available:

- `path`: JSON-style path with zero-based indexes, such as `$.Data[0][1]`.
- `row`: authoring table row, starting at 2 because row 1 contains headings.
- `column`: one-based authoring column; `heading` identifies a known heading.
- `line` and `column` on `invalid_json`: one-based JSON source-text location.

Diagnostics use safe summaries instead of raw exception text or cell values.
A runtime warning can identify the affected data row without printing its data.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Command succeeded; for validation, authoring passed even if runtime warns |
| 1 | Unexpected local failure (or recipe execution failure) |
| 2 | Usage, input file, JSON, or authoring-validation error |
| 3 | Reserved for authentication/access failure in service commands |
| 4 | Reserved for service/network/processing failure |
| 5 | Reserved for model-operation deadline exceeded |
| 6 | Reserved for saved-content verification mismatch |
| 130 | Validation interrupted by the user |

Only local validation is implemented in the model command group at this stage.
Create/update/inspect/export/verify will build on this contract. Validation does
not establish model readiness or saved-content verification.
