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

With `--json`, model commands write exactly one JSON result to stdout.
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
| 3 | Authentication/access failure |
| 4 | Service/network failure or uncertain submission outcome |
| 5 | Reserved for model-operation deadline exceeded |
| 6 | Reserved for saved-content verification mismatch |
| 130 | Model operation interrupted by the user |

## Create, update, inspect, and export

```powershell
$created = wrangles model create --type extract-ai --file "power supply.json" --name "Power Supply" --json | ConvertFrom-Json
wrangles model inspect $created.model_id --json
wrangles model export $created.model_id --output "saved power supply.json" --json
wrangles model update $created.model_id --file "revised power supply.json" --json
```

These commands use the existing Wrangles credentials and configured SDK target.
`--request-timeout SECONDS` defaults to 30 and must be finite and positive. It
bounds connection/read inactivity for each request, including authentication;
it is not an overall operation deadline. The new operations make one attempt per
request and do not follow redirects. Existing SDK callers retain their existing
retry behavior outside this opt-in request context.

`create` supports only `extract-ai`, mapped to service `type=extract` and
`variant=extract-ai`. It validates before making exactly one creation POST.
`update` takes an explicit model ID and checks metadata purpose/type and variant
before submitting. It never renames a model or chooses one by name.

Updates replace the submitted Columns/Data table. Settings come from saved
**content**, not metadata, and merge through the shared #1182 contract:

- Omitted `Settings`, `Settings: null`, and `Settings: {}` preserve existing settings.
- Supplied setting keys override those keys; other settings remain.
- Explicit setting values `false`, `0`, `null`, and empty strings remain explicit.
- Instruction aliases are normalized/mirrored by the existing shared contract.

`inspect` returns a safe metadata subset, including processing status when the
service supplies it. It does not return the saved definition or metadata settings.
`export` reads the full definition without requesting secret-store contents and
writes a separate UTF-8 JSON document suitable for validation/update. It replaces
an existing destination only after the complete file has been written. The parent
directory must exist. Export status stays on stdout; it is never appended to the file.

Successful create/update returns `outcome: "accepted"` and the model ID, with
`readiness` and `verification` both `"not_checked"`. HTTP acceptance or a status
observed before update does not establish that this submission is Ready. Inspect
and export use `outcome: "success"`; inspecting a Ready status is only a metadata
observation. The envelope adds `target`, plus `metadata` for inspect or `output`
for export. Target diagnostics omit URL credentials, query strings, and fragments.

A timeout, connection loss, or server failure during a write produces an unknown
submission outcome (exit 4). A successful creation response without an unambiguous
ID produces `outcome: "accepted"` with an error and exit 4. Neither case triggers
a repeated creation. Reconcile with the service before retrying: if an ID is
known, inspect/export it; if none was returned, recover the ID through the service.
A user interruption also does not prove a submitted write was rolled back.

Waiting and saved-content verification will be added in the next step. No live
service run is implied by the offline test results.

## Python helpers

```python
from wrangles.model_operations import SavedModelClient, ModelOperationError

client = SavedModelClient(request_timeout=30)
result = client.create(definition, name="Power Supply")
model_id = result["model_id"]
metadata = client.inspect(model_id)
exported = client.export_definition(model_id)
result = client.update(model_id, revised_definition)
```

Submission results also contain `submitted_content`: the effective payload after
settings rules, for subsequent Python verification. The CLI excludes it from the
status envelope. `ModelOperationError` exposes a safe message, `code`, `exit_code`,
`outcome`, and `model_id` when known. Existing `wrangles.train.extract` signatures
and HTTP response return values are unchanged.
