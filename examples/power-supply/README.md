# Power Supply: saved model and recipe walkthrough

This example contains a synthetic 23-attribute definition, three invented product
records, and a recipe that reads/writes JSON explicitly. Run commands from the
repository root with Wrangles installed in your active Python environment.

## Files

- `definition.json`: Settings/Columns/Data with all 14 known headings. Includes
  nested OutputVoltage, input ranges, dimensions, booleans, a PlugType enum, and
  a paired output-voltage example.
- `input.json`: three synthetic descriptions; these are not real product claims.
- `recipe.wrgl.yml`: uses `${POWER_SUPPLY_MODEL_ID}`, `${POWER_SUPPLY_INPUT}`,
  `${POWER_SUPPLY_OUTPUT}`, and the existing `${OPENAI_API_KEY}`.

## 1. Validate locally

```powershell
wrangles model validate examples/power-supply/definition.json --json
if ($LASTEXITCODE -ne 0) { throw "Definition validation failed" }
```

This performs no authentication, model writes, or extraction calls. The example
passes both saved-model authoring validation and local runtime compilation.

## 2. Create and verify storage

Use your existing Wrangles credential provider. No passwords are supplied as
command-line arguments. The following command creates a new disposable model:

```powershell
$name = "CLI synthetic Power Supply " + [guid]::NewGuid().ToString("N")
$created = wrangles model create --type extract-ai --file examples/power-supply/definition.json --name $name --verify --wait-timeout 300 --json | ConvertFrom-Json
$createExit = $LASTEXITCODE
$created | ConvertTo-Json -Depth 20
if ($createExit -ne 0) { throw "Create/readback failed. Keep the returned ID and reconcile before retrying." }
$env:POWER_SUPPLY_MODEL_ID = $created.model_id
```

Record the returned ID even on a timeout or verification failure. Never blindly
repeat creation. Successful storage verification does not measure extraction
accuracy. Update readiness has a separate version-correlation limitation; see the
[CLI reference](../../docs/cli.md#wait-and-verify).

## 3. Inspect and export

```powershell
$runDir = Join-Path $env:TEMP ("wrangles-power-supply-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $runDir | Out-Null
$savedFile = Join-Path $runDir "saved.json"
wrangles model inspect $env:POWER_SUPPLY_MODEL_ID --json
if ($LASTEXITCODE -ne 0) { throw "Inspect failed" }
wrangles model export $env:POWER_SUPPLY_MODEL_ID --output $savedFile --json
if ($LASTEXITCODE -ne 0) { throw "Export failed" }
wrangles model validate $savedFile --json
if ($LASTEXITCODE -ne 0) { throw "Exported definition validation failed" }
```

Inspect returns metadata; export writes the complete definition to its own file.
The status JSON on stdout is separate from that document. Do not merge stderr
into stdout when using `ConvertFrom-Json`.

## 4. Update the same ID, preserving settings

Change one description and omit Settings in the submitted update. Save the full
expected document separately so standalone verification can compare retained
settings as well as the new table.

```powershell
$revision = Get-Content -LiteralPath $savedFile -Raw | ConvertFrom-Json
$descriptionColumn = [Array]::IndexOf($revision.Columns, "Description")
$revision.Data[0][$descriptionColumn] += " Use the explicitly printed manufacturer name only."
$revision.Settings | Add-Member -NotePropertyName model_id -NotePropertyValue $env:POWER_SUPPLY_MODEL_ID -Force
$expectedFile = Join-Path $runDir "expected-after-update.json"
$revision | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $expectedFile -Encoding utf8
$revision.PSObject.Properties.Remove("Settings")
$updateFile = Join-Path $runDir "update.json"
$revision | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $updateFile -Encoding utf8
wrangles model update $env:POWER_SUPPLY_MODEL_ID --file $updateFile --verify --json
if ($LASTEXITCODE -ne 0) { throw "Update/readback failed; retain the model ID" }
wrangles model verify $env:POWER_SUPPLY_MODEL_ID --file $expectedFile --json
if ($LASTEXITCODE -ne 0) { throw "Saved definition differs from the expected document" }
```

The table is replaced; existing settings survive because they were omitted.
`verification: passed` confirms matching content. Update `readiness: unconfirmed`
explicitly records that the API does not prove readiness of this submission's
particular version.

## 5. Run the extraction recipe

This step calls the configured extraction provider and requires the existing
`OPENAI_API_KEY`. The saved definition uses the SDK's configured default model.

```powershell
$env:POWER_SUPPLY_INPUT = (Resolve-Path examples/power-supply/input.json).Path
$env:POWER_SUPPLY_OUTPUT = Join-Path $runDir "extracted.json"
wrangles recipe run examples/power-supply/recipe.wrgl.yml --timeout 120
if ($LASTEXITCODE -ne 0) { throw "Extraction recipe failed" }
Get-Content -LiteralPath $env:POWER_SUPPLY_OUTPUT -Raw
```

Each output row retains its `record_id` and description and adds an `attributes`
object. Inspect the values against the supplied text. This walkthrough is not an
accuracy benchmark, and it does not exercise Office.js, WranglesJS serialization,
or actual Excel save interactions. The legacy `wrangles.recipe` command also
accepts the recipe and the same environment variables.

## Opt-in live storage test

The default test suite skips `tests/test_cli_live.py`. To explicitly create one
new disposable model and test CLI create/wait/export/update/verify:

```powershell
$env:WRANGLES_CLI_LIVE_OUTPUT = Join-Path $runDir "live-evidence"
$env:WRANGLES_RUN_LIVE_CLI = "1"
try {
    python -m pytest tests/test_cli_live.py -q
} finally {
    Remove-Item Env:WRANGLES_RUN_LIVE_CLI
}
```

Choose a persistent evidence directory; the test requires this setting. Each run
creates a UUID-named subdirectory containing `evidence.json`, the export, the
settings-omitting update, and its full expected document. Evidence records the
package version, commit, tracked dirty state, Python/platform, service target,
unique model name, model ID, and each CLI result. Raw stderr, credentials, and
environment-variable contents are not copied into evidence. The test saves the
creation result/known ID before asserting success. A failure stops the workflow
without repeating creation or choosing an existing model by name.

This live test covers API save/readback through the CLI. It does not call the
extraction provider, run the example recipe, perform an accuracy evaluation,
interact with Excel, or claim a CI result. Those are separate checks.

## Cleanup

The example and live test leave their disposable models in place for inspection.
Use your existing model-management UI to delete **only the ID recorded for this
run**, checking its unique `CLI synthetic Power Supply` name. No existing user
model is used as a mutable fixture. If creation timed out without returning an
ID, reconcile the uniquely named submission with the service before another run.
Deletion/permission-management CLI commands are outside this enhancement.

Keep the evidence until the result has been reviewed. Remove local artifacts
from the specific run directory when no longer needed.
