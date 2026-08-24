# `extract.ai` configuration

The packaged defaults and base prompt live in
`wrangles/ai_defaults.yml`. Set `WRANGLES_AI_CONFIG` to the path of a
versioned replacement YAML file to override the complete configuration.

## Runtime defaults

- Provider: `openai`
- Protocol: `responses`
- Model: `gpt-5.4-mini`
- Concurrency: 32
- Per-request timeout: 12 seconds
- Total call deadline: 15 seconds
- Retries: 1, bounded by the total deadline
- Reasoning effort: `none`
- Response storage: disabled

Recipes and Python calls can override these settings individually. Saved XL
models and recipe outputs are compiled through the same definition compiler.

## Nullable output fields

Defined output keys remain required so strict Structured Outputs always return
the complete response shape. Their values are nullable by default, allowing the
model to return JSON `null` when the input does not support a value. Python
represents that value as `None`; presentation layers such as WranglesXL may
convert it to an empty cell or empty string at their serialization boundary.

Enums automatically include JSON `null`. For saved models, either `null` or the
string `"null"` in an Enum cell is normalized to JSON `null` when the field is
nullable. A future or existing saved-model `Nullable` column is supported:
blank or `true` uses the nullable default, while `false` explicitly opts out.

Saved-model Examples cells accept strict JSON or human-friendly YAML-like
values. For example, both of these are compiled into structured examples:

```text
{value: 12, uom: VDC},{value: 110, uom: VAC}
Ceramic Tile, Slate
```

The compiler uses PyYAML's safe loader and treats comma-separated Examples
cells as sequences; users do not need to quote every object key and value.

## Examples

Definitions support both field-specific and record examples. They compile to
the same stable prompt representation and precede each row's dynamic input.

For saved models, the field grid supports:

| Column | Behavior |
| --- | --- |
| `Examples` | Existing output-only value guidance; remains backward compatible |
| `Example - Input` | Source text or data for one field-specific example |
| `Example - Output` | Expected value for that field; output-only guidance when input is blank |

When `Example - Input` is populated, `Example - Output` is required. The
expected output may be human-friendly JSON/YAML-like syntax. Use explicit list
syntax for an array-valued paired output, such as `[Ceramic Tile, Slate]`.
An explicit `null` is valid because output fields are nullable by default.

Field-specific examples teach only the named field. Paired field examples may
include optional `name` and `notes` metadata. Definitions may also provide
`record_examples` that pair one input with a multi-field output:

```yaml
wrangles:
  - extract.ai:
      input: Description
      api_key: ${OPENAI_API_KEY}
      output:
        Power Source:
          type: string
          examples:
            - name: cordless tool
              notes: Voltage without a cord indicates a battery.
              input: 18V cordless drill
              output: Battery
            - Corded
        Voltage:
          type: number
      record_examples:
        - name: corded saw
          notes: Use both fields from this complete example.
          input: 120V corded jig saw
          output:
            Power Source: Corded
            Voltage: 120
```

The first `Power Source` item is a paired field example; `Corded` remains
output-only value guidance. Top-level `record_examples` demonstrate the complete
record. Their output may be sparse: the compiler inserts `null` for omitted
output fields so every example demonstrates the complete required response
shape. Unknown fields and values that do not match the output schema fail during
compilation. Optional `name` and `notes` metadata are included in model guidance
at both levels.

Saved-model content may likewise include a top-level `Examples` array of
record pairs. A dedicated WranglesXL interface for those examples can be
added later without changing the compiler or runtime contract.

## Result cache

The result cache is local to a warm Python or Lambda process. It stores only
successful result values; cache keys contain hashes rather than raw API keys,
prompts, or input rows.

Default limits:

- TTL: 3,600 seconds
- Maximum entries: 512
- Maximum serialized value: 65,536 bytes
- Concurrent duplicate suppression: enabled

The effective key includes the provider, protocol, API credential hash, model,
prompt, schema, model options, endpoint, and exact serialized input. A change
to any of these produces a cache miss. Errors, timeouts, invalid structured
responses, and oversized values are not cached.

Use `cache: false` in a recipe or `cache=False` in Python to bypass the cache
for one call. `cache_ttl` overrides the TTL for one call.

Operational environment controls:

| Variable | Purpose |
| --- | --- |
| `WRANGLES_EXTRACT_AI_CACHE_ENABLED` | Global kill switch |
| `WRANGLES_EXTRACT_AI_CACHE_TTL_SECONDS` | Override entry TTL |
| `WRANGLES_EXTRACT_AI_CACHE_MAX_ENTRIES` | Bound warm-process entry count; `0` disables |
| `WRANGLES_EXTRACT_AI_CACHE_MAX_VALUE_BYTES` | Bound individual result size; `0` disables |
| `WRANGLES_EXTRACT_AI_CACHE_SINGLE_FLIGHT` | Enable concurrent duplicate suppression |
| `WRANGLES_EXTRACT_AI_CACHE_LOG_EVERY` | Emit aggregate counters every N lookups; `0` disables logs |

Cache telemetry contains only aggregate counters and sizes. It does not log
cache keys or values. `wrangles.ai_cache.stats()` returns the current counters,
and `wrangles.ai_cache.clear()` clears the warm-process cache.

## Dynamic object schemas

Fixed object definitions use strict structured outputs. An object with
`additionalProperties: true`, a schema-valued `additionalProperties`, or no
named properties is treated as a dynamic dictionary. Dynamic definitions use
non-strict provider mode and are validated locally so unknown keys can be
preserved without opening the top-level response object.
