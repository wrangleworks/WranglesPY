# Defining an `extract.ai`

Use `extract.ai` when each input row should produce one or more consistently
named attributes. You can define the attributes in an Excel saved model or
directly in a recipe. Both routes compile to the same output contract.

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
      model: gpt-5.6-luna
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
compiler fills them with `null`. Unknown fields and values that do not match the
schema fail before the model is called.

## Review checklist

Before saving or running the definition, verify:

- every row has a distinct `Find` name;
- each `Description` says what evidence is allowed;
- normalization units and conflict rules are explicit;
- arrays define the intended item type;
- objects use named properties unless dynamic keys are intentional;
- examples demonstrate decisions rather than repeating the description; and
- uncertain or absent information is represented by `null`, not invented data.
