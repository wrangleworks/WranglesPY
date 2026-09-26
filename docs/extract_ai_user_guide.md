# Defining an `extract.ai`

Use `extract.ai` when each input row should produce one or more consistently
named attributes. You can define the attributes in an Excel saved model or
directly in a recipe. Both routes compile to the same output contract.

## Model defaults and capabilities

`wrangles/ai_defaults.yml` is the packaged source of model configuration.
The `extract.ai` default role selects `gpt-6-luna`. Omit `model` in ordinary
recipes to follow the configured default. Saved extraction model selection
retains its existing precedence; saved model names are not automatically migrated.

Version 2 groups models by provider, separates lifecycle status from default
roles, and records model defaults and supported enum values together. Extraction
settings such as concurrency, cache, and the base prompt belong to the operation.
See [AI model configuration](ai_configuration.md) for the schema, caller coverage,
override precedence, test-role selection, and version-1 compatibility.

The public parameters remain `reasoning: {effort: ...}` and
`verbosity: low | medium | high`. Supported values in the catalog describe the
model; they are separate from the value requested by a recipe. Existing saved
model validation and legacy model-family compatibility behavior are preserved.

For each model upgrade, verify capabilities against
[OpenAI's model documentation](https://developers.openai.com/api/docs/models)
and run credentialed extraction checks. Mocked tests verify request construction,
not provider availability or extraction quality.

## Start with the output

Define the result you want before writing general instructions or examples.
For each attribute, decide:

1. its name;
2. its type;
3. what evidence supports it;
4. how it should be normalized; and
5. whether it contains child properties or array items.

Use `null` for information that is absent or unsupported. Do not use a default
to disguise missing evidence: `Default` is a schema annotation, not a guaranteed
runtime substitution.

## Excel saved models

A newly created Excel model has these columns:

| Column | What to enter |
| --- | --- |
| `Find` | Required output attribute name |
| `Description` | Evidence, selection, inference, normalization, and conflict rules for this attribute |
| `Type` | `string`, `number`, `integer`, `boolean`, `array`, or `object` |
| `Default` | Optional annotated default value |
| `Examples` | Optional output-only examples |
| `Enum` | Allowed output values |
| `Notes` | Human notes; not sent to the model |
| `Properties` | Named child fields for an object |
| `Items` | Schema for one array element |
| `Required` | Required named object properties; blank means all named properties |
| `Additional Properties` | Whether an object accepts unknown keys; blank means `FALSE` when named properties exist |
| `Nullable` | `TRUE` or `FALSE`; blank uses the applicable default |
| `Example - Input` | Source text for one field-specific example |
| `Example - Output` | Expected value for the paired input |

Legacy saved models with fewer columns remain valid. Columns may be reordered,
and newer columns that this version of Excel does not recognize are preserved.
`Find` is the only required worksheet column.

### Easy cell formats

Excel values do not need to be strict JSON. Use the simplest unambiguous form:

| Need | Recommended entry | Also accepted |
| --- | --- | --- |
| Simple list | `Corded | Battery` | `Corded, Battery`, `[Corded, Battery]`, or strict JSON |
| Object value | `{value: 120, uom: VAC}` | Strict JSON or a YAML-style block |
| Object properties | `value: number | uom: string` | `value | uom` or a complete JSON/YAML schema |
| Array of strings | `string` in `Items` | `{type: string}` |
| Array of objects | `value: number | uom: string | material: string` in `Items` | A complete item schema |
| Boolean | An Excel `TRUE` or `FALSE` value | The text `true` or `false` in Boolean/schema cells |

Prefer `|` for human-entered lists. Commas remain supported for compatibility,
but a comma may also be part of a value. Quote or bracket a value containing a
literal comma, such as `["500-3,100"]`.

The parser accepts JSON and a restricted, JSON-compatible form of YAML. It
rejects duplicate object keys, YAML tags, anchors, aliases, non-string object
keys, non-finite numbers, and excessively deep values. Words such as `yes` and
`on`, ISO-formatted dates, and identifiers such as `001` remain strings.
In an Enum cell, an unquoted `null` token means JSON `null` and therefore
requires a nullable field. Use `["null"]` when the literal word is intended.

### Object and array defaults

- Output fields are nullable by default, but the output key is always returned.
- Named properties nested inside an object or array item are non-null by
  default. Set `nullable: true` in a complete child schema when a nested value
  genuinely may be null.
- Blank `Required` means every named property is required.
- Blank `Additional Properties` means `FALSE` when named properties exist.
- An object without named properties is a dynamic dictionary. It uses
  non-strict provider mode and local result validation.

These defaults make this sufficient for a normal value-and-unit object:

| Find | Type | Properties |
| --- | --- | --- |
| Voltage | object | `value: number | uom: string` |

It compiles as a closed object with both `value` and `uom` required and
non-null.

### Instructions and examples

Put attribute-specific rules in `Description`. Put rules that apply to every
attribute in **General Instructions**.

Good general instructions state evidence and conflict policy, for example:

```text
Extract values supported by the input. Return null when information is absent.
When two numeric values differ only by rounding, use the more precise value.
Power source and AC/DC may be inferred from explicitly stated voltage when the
range is strongly characteristic; otherwise return null.
```

Use `Examples` for output-only guidance:

```text
Corded | Battery
```

Use the paired columns when the source wording matters:

| Example - Input | Example - Output |
| --- | --- |
| `Rating 120V` | `{value: 120, uom: VAC}` |

`Example - Output` is required whenever `Example - Input` is populated. The
expected output is validated against the attribute schema before any model call.
Multiline input text remains text even when it contains lines such as
`Description: Cordless drill`; use braces only when the real input is a
structured object.

Object examples must include every non-null named property. For the Voltage
schema above, `{value: 120}` is incomplete because `uom` is non-null by default.
Supply `{value: 120, uom: VAC}`, or define `uom` with `nullable: true` in a
complete property schema if omission is genuinely valid.

### Calling a saved model from a recipe

```yaml
wrangles:
  - extract.ai:
      input: Desc and Specs
      model_id: 4cf3ef34-7a8c-4beb
      output: AI Attributes
      api_key: ${OPENAI_API_KEY}
```

With `model_id`, `output` is the destination dataframe column or columns. The
saved model supplies the attribute schema, model, general instructions, and
reasoning effort.

The Excel settings panel currently offers reasoning effort `none` (default) and
`low`. It stores this as `ReasoningEffort` and the runtime maps it to the
Responses API reasoning setting.

## Saving AI definitions from Python or recipes

The `train.extract` write connector accepts the same optional schema columns as
Excel. Use `variant: ai` when creating an AI model by name:

```python
import pandas as pd
import wrangles

definition = pd.DataFrame({
    "Find": ["Voltage"],
    "Type": ["object"],
    "Properties": ["value: number | uom: string"],
})

wrangles.connectors.train.extract.write(
    definition,
    name="Voltage schema",
    variant="ai",
    settings={
        "GPTModel": wrangles.ai_config.extract_ai()["model"],
        "ReasoningEffort": "none",
    },
)
```

Only `Find` is universally required. Existing seven-column models, models with
paired examples instead of `Examples`, reordered columns, and smaller valid
subsets are supported. An object can omit the `Properties` column for legacy
compatibility, but when that column is present its object cells must be populated.

Native dictionaries, lists, booleans, and numbers are preserved. For example,
this table combines a closed object, an enum, and an array:

```python
definition = pd.DataFrame([
    {
        "Find": "OutputVoltage",
        "Type": "object",
        "Properties": {
            "value": {"type": "number", "nullable": False},
            "uom": {"type": "string", "enum": ["VAC", "VDC", "V"]},
        },
        "Required": ["value", "uom"],
        "Additional Properties": False,
        "Example - Input": "Output: 24 VDC",
        "Example - Output": {"value": 24, "uom": "VDC"},
    },
    {"Find": "PlugType", "Type": "string", "Enum": "Type A | Type B | Other"},
    {"Find": "StandardsApprovals", "Type": "array", "Items": "string"},
])

wrangles.connectors.train.extract.write(
    definition, name="Power Supply example", variant="ai",
)
```

Missing dataframe cells (`NaN`, `pd.NA`, and `NaT`) become JSON null cells,
without changing the input dataframe or replacing false/zero with blanks.
An intentionally null example should use the text `null` in the example cell;
a native null cell is blank for the paired-example requirement. Nested schema
values must be JSON-compatible; malformed structured cells and non-finite
nested numbers fail with a row/column error before submission.

To update an existing model, use `model_id` and omit `variant`. The connector
reads the existing variant and preserves its content-level AI settings,
including `GPTModel`, `ReasoningEffort`, and `GeneralInstructions`. Supplied
settings replace individual keys; omitted settings or `{}` preserve existing
keys. Explicit blank, false, zero, or null setting values are sent as overrides,
and must be valid for the particular setting. This is a shallow settings merge,
not an implicit clear or a merge of schema rows. General Instructions aliases
are treated as one setting, as described below.

```yaml
read:
  - file:
      name: revised-definition.xlsx
write:
  - train.extract:
      model_id: ${SAVED_MODEL_ID}
      settings:
        GeneralInstructions: Extract only values supported by the primary product.
```

With `columns` omitted, every input column is submitted, including extra columns
that this version does not recognize. With `columns` supplied, the connector
honors that selection and its wildcards; `Find` must remain selected. Updates
replace the submitted schema table, so omitted rows or columns are not merged
back from the old model. Pattern-model behavior is unchanged, and `settings`
is an AI-only connector option.

Saving validates the known authoring columns and retains their original values.
Blank rows are retained and skipped by the authoring validator. Optional defaults
such as all named object properties being required are applied by the extraction
runtime, not written into blank cells. Runtime compilation is stricter: a model
can be saved with extra columns or blank rows that execution rejects. A successful
save does not establish runtime compatibility, processing readiness, or extraction
accuracy.

For code that already has a full content document, the lower-level SDK accepts
`Columns`, `Data`, and optional `Settings` directly:

```python
response = wrangles.train.extract(
    {"Columns": ["Find", "Type"], "Data": [["Power", "number"]]},
    name="Power schema",
    variant="extract-ai",
)
response.raise_for_status()
```

This AI dictionary path shares the connector's authoring validation. When
updating through the lower-level method, pass `model_id` instead of `name` and
retain `variant="extract-ai"` to use the same settings-preservation behavior.
The existing seven-value list input and HTTP-response return type remain
supported. All service operations continue to use the normal Wrangles credentials.

### General Instructions across Excel, saved models, and recipes

The display label is **General Instructions**. In a saved model's `Settings`
object, use `GeneralInstructions` (a string or list of strings). For an
`extract.ai` Python call or recipe, continue to use `instructions`. Instructions
on the call are appended to the saved model's instructions; they do not replace
them. The Python `messages` argument remains a compatibility alias for
`instructions`; do not supply both arguments together.

Existing saved settings named `AdditionalMessages`, `instructions`, or `messages`
are still read. Key matching ignores case, spaces, and punctuation. Within one
settings document the precedence is `GeneralInstructions`, `AdditionalMessages`,
`instructions`, then `messages`. An explicitly present empty string, null, or
empty list clears that setting, even when another alias contains stale text.
An explicit update through any alias overrides the existing saved value.

Updated Excel and Python save paths write `GeneralInstructions` and an identical
`AdditionalMessages` compatibility copy, removing other instruction aliases.
Omitting instructions preserves the existing value. This also normalizes legacy
instructions when a model is next saved; no bulk model migration is required.
Both names in storage represent one setting and are applied only once.

### Rolling out the naming change

Release the updated Excel authoring paths first. Their compatibility copy lets
older Python runtimes continue reading `AdditionalMessages`. Verify creating,
editing, clearing, saving, and reopening a disposable model, then run an
extraction using the currently deployed runtime. Reload existing Excel task
panes so authors use the updated editor before releasing the new Python reader.
An older editor can change only `AdditionalMessages` and leave a conflicting
`GeneralInstructions` value; the new reader will prefer `GeneralInstructions`.

Release Python next, and separately promote that package in the Lambda-Recipes
runtime used by Excel. Confirm extraction through both Excel and recipes, with
saved and call-specific instructions. A merged PR or published Python package
alone does not verify the deployed runtime. Keep the compatibility copy until
all supported readers and writers have migrated, including direct API clients.
If an old writer or a rollback creates conflicting keys, reconcile the intended
value through an updated save path before executing with the new reader.

## Defining the schema in a recipe

For a recipe-owned definition, put the schema under `output`. Recipe YAML is
already structured, so use normal nested YAML rather than Excel shorthand.

```yaml
wrangles:
  - extract.ai:
      input:
        - Title
        - Technical Data
      api_key: ${OPENAI_API_KEY}
      reasoning:
        effort: low
      instructions:
        - Extract values supported by the supplied product information.
        - Return null when a top-level attribute is absent.
        - When two numeric values differ only by rounding, use the more precise value.
      output:
        Voltage:
          type: object
          description: >-
            Voltage of the product. Normalize AC voltage to VAC and DC or
            battery voltage to VDC. AC/DC may be inferred when an explicitly
            stated voltage is strongly characteristic of one current type.
          properties:
            value:
              type: number
            uom:
              type: string

        Power Source:
          type: string
          description: >-
            How the product is powered. Return Corded or Battery when stated or
            when an explicitly stated voltage provides strong conventional
            evidence; otherwise return null.
          enum:
            - Corded
            - Battery

        Cutting Depth:
          type: array
          description: One result per explicitly stated material.
          items:
            type: object
            properties:
              value:
                type: number
              uom:
                type: string
              material:
                type: string

        Dust Blower:
          type: boolean
          description: >-
            Whether the product explicitly has a dust blower. Return false only
            when the input explicitly says it does not.
```

The compiler supplies `required` and `additionalProperties: false` for each
named object when those keywords are omitted. Top-level fields allow `null`;
the named child properties shown above do not.

### Recipe examples

Add a paired example under one field when it teaches that field only:

```yaml
output:
  Power Source:
    type: string
    examples:
      - name: conventional corded rating
        input: 120V top-handle jigsaw
        output: Corded
```

Use `record_examples` when fields should be learned together:

```yaml
record_examples:
  - name: corded jigsaw
    input:
      Title: BOSCH JS260 120-Volt Top-Handle Jigsaw
      Technical Data: Rating 120V; Amperage 6.1
    output:
      Voltage:
        value: 120
        uom: VAC
      Power Source: Corded
```

Record-example outputs may omit unrelated nullable top-level fields; the
compiler fills them with `null`. Required non-null nested properties must still
be present. Unknown fields and values that do not match the schema fail before
the model is called.

## Review checklist

Before saving or running the definition, verify:

- every row has a distinct `Find` name;
- each `Description` says what evidence is allowed;
- normalization units and conflict rules are explicit;
- arrays define the intended item type;
- objects use named properties unless dynamic keys are intentional;
- examples demonstrate decisions rather than repeating the description;
- object examples contain every required non-null nested property; and
- uncertain or absent information is represented by `null`, not invented data.
