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
| 5 | Waiting deadline exceeded; the model may still complete |
| 6 | Saved-content verification mismatch |
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

Without `--wait` or `--verify`, successful create/update returns `outcome: "accepted"` and the model ID, with
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

## Wait and verify

```powershell
$created = wrangles model create --type extract-ai --file definition.json --name "Power Supply" --wait --verify --wait-timeout 300 --json | ConvertFrom-Json
wrangles model verify $created.model_id --file definition.json --json
wrangles model update $created.model_id --file revised.json --verify --json
```

`--wait` polls status after successful submission. `--verify` implies waiting and
compares readback against the effective submitted document, including merged
update settings. `--wait-timeout` defaults to 300 seconds and must be finite and
positive. The Python helper also accepts `poll_interval` (default 2 seconds).
These options are validated before submission. The waiting deadline starts after
acceptance and is separate from recipe execution timeouts.

Each waiting HTTP request, including authentication, receives at most the
remaining deadline budget. An isolated daemon transport worker lets the caller
stop waiting at the deadline even if a response is still arriving. The worker
owns/closes its Session and discards a late response; no subsequent polling
request is issued. The in-flight request may finish on the server. Waiting does
not cancel server processing, roll back a write, or repeat a submission.

Creation can report `readiness: "ready"` after observing Ready for its newly
returned ID. Updates report `readiness: "unconfirmed"`: the current SDK/API
contract does not provide a confirmed submission-to-version link. A pre-existing
Ready status, a production recipe version ID, or a processing transition is not
proof that this particular update is ready.

For updates, Ready with mismatching readback continues polling. Once readback
matches, the result includes `freshness.readback_matches: true` and an explicit
version-correlation limitation. `--wait` alone returns `outcome: "accepted"` in
this case; `--verify` returns `outcome: "verified"` and `verification: "passed"`,
while readiness stays unconfirmed. Identical-content updates have the same
limitation. After an observed processing-to-Ready transition, a mismatching
`--verify` readback returns exit 6, still without claiming version readiness.
Stale Ready with mismatching content until the deadline returns exit 5.

Standalone `model verify MODEL_ID --file FILE` is read-only. It compares the full
expected authoring document (normalized through the shared authoring contract)
against the saved document, without waiting for Ready or merging existing
settings into the expected file. For that reason, supply the full expected
settings when verifying an earlier update that preserved settings. Omitted
expected Settings means the authoring contract's empty settings, not a wildcard.

Comparison ignores object-key order and retains array order, missing versus
null, boolean versus number, blank versus false, nested values, unknown fields,
and numeric type differences (for example integer 1 versus floating-point 1.0).
It does not drop server fields to force a match. The shared authoring preparation
normalizes expected instruction aliases; no further service transformations are
silently normalized on readback. Storage verification does not measure extraction
accuracy or exercise the Excel UI.

Results may add `freshness` and `comparison`. Comparison reports at most 20
field paths and difference kinds (`missing`, `unexpected`, `type`, `value`), plus
`differences_truncated`; it never includes the compared values. Paths use JSON
bracket notation, such as `$["Data"][0][1]`. Errors retain a known model ID.
`verification` can be `passed`, `failed`, `pending` (the deadline was reached
before readback could be confirmed within budget), or `not_checked`. Readiness may be `ready`, `failed`, `unconfirmed`, or
`not_checked`. A processing failure returns exit 4; interruption returns 130.
No live service run is implied by offline test results.

## Python helpers

```python
from wrangles.model_operations import SavedModelClient, ModelOperationError

client = SavedModelClient(request_timeout=30)
result = client.create(definition, name="Power Supply")
model_id = result["model_id"]
metadata = client.inspect(model_id)
exported = client.export_definition(model_id)
result = client.update(model_id, revised_definition, verify=True, wait_timeout=300)
comparison = client.verify(model_id, result["submitted_content"])
```

Submission results also contain `submitted_content`: the effective payload after
settings rules, for subsequent Python verification. The CLI excludes it from the
status envelope. `ModelOperationError` exposes a safe message, `code`, `exit_code`,
`outcome`, and `model_id` when known, plus readiness, verification, freshness,
and comparison diagnostics when applicable. Existing `wrangles.train.extract` signatures
and HTTP response return values are unchanged.

## End-to-end example and live evidence

See the [Power Supply walkthrough](../examples/power-supply/README.md) for a complete
23-attribute definition, synthetic input, explicit recipe I/O, guarded PowerShell
commands, opt-in CLI save/readback testing, and disposal of the test model.
Offline tests, live storage checks, extraction evaluation, Excel interaction,
and CI results must be reported separately.


### Service-added submission settings

Live API readback can include write query parameters in Settings: name, type,
and variant after create; type and model_id after update. Submission verification
allows these additions only when absent from the submitted settings and checks
their values against the original request parameters. Explicitly submitted
settings, unknown additions, and all other content still compare strictly.
The submitted_content Python field remains the actual payload sent. Standalone
model verify still requires a complete expected document, including service-added
settings; use an export as the baseline for subsequent updates and verification.
