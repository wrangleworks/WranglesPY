# `extract.ai` configuration

For a task-oriented introduction to defining attributes in Excel or directly
in recipe YAML, see [`extract_ai_user_guide.md`](extract_ai_user_guide.md).

The packaged defaults and base prompt live in
`wrangles/ai_defaults.yml`. Set `WRANGLES_AI_CONFIG` to the path of a
versioned replacement YAML file to override the complete configuration.

## Runtime defaults

- Provider: `openai`
- Protocol: `responses`
- Model: `gpt-5.4-mini`
- Default worker concurrency (`default_concurrency`): 32 per `extract.ai` call
- Network timeout per HTTP attempt: 12 seconds
- Retries: 1 additional attempt per row after a retryable failure
- Reasoning effort: `none`
- Response storage: enabled

Recipes and Python calls can override these settings individually. Saved XL
models and recipe outputs are compiled through the same definition compiler.

When `threads` is omitted, the call uses `extract_ai.default_concurrency`.
An explicit `threads` value can raise or lower concurrency for that call.
Custom `WRANGLES_AI_CONFIG` files should use `extract_ai.default_concurrency`.

Each retry receives the full configured timeout. Queued rows and retry delays
do not consume that timeout, so a complete batch can take much longer than one
request. Long-running Python and GitHub jobs can process rows in successive
waves; WranglesXL batches must still fit within XL's approximately 20-second
request window. See [`extract_ai/README.md`](extract_ai/README.md) for timing
and batch-size guidance.

## Response storage and OpenAI logs

The packaged default is `store: true`. Responses API requests retain their
inputs and outputs at OpenAI for later inspection in the project's **Logs >
Responses** view. No `protocol` or `url` override is needed with the packaged
Responses defaults. OpenAI's standard policy retains stored response data for
at least 30 days; see its [data controls](https://developers.openai.com/api/docs/guides/your-data#v1responses)
for retention exceptions and project controls.

Set `store: false` on an individual recipe step to disable response storage:

```yaml
wrangles:
  - extract.ai:
      input: Description
      api_key: ${OPENAI_API_KEY}
      store: false
      output:
        Product Type:
          type: string
```

Direct Python calls can likewise pass `store=False`. A per-call value overrides
the configuration. A replacement `WRANGLES_AI_CONFIG` file should set
`extract_ai.store` explicitly; if it omits that key, the runtime's fallback
is `true`.

Response storage is separate from the local result cache. Cache hits do not
send another OpenAI request or create another stored response. Changing
`store` changes the effective cache key, so stored and unstored calls do not
reuse each other's cached results. Use `cache: false` only when a fresh
request is needed for diagnosis, and keep caching enabled for normal runs.

The `store` option applies to the Responses path and does not select the API
protocol or create Agents SDK workflow traces. The Chat Completions
compatibility path does not forward this option.

## Recipe and user labels in OpenAI logs

`extract.ai` automatically adds available recipe and user labels to the
request's `metadata`:

| Label | Automatic source |
| --- | --- |
| `recipe_name` | Saved recipe title, local recipe file basename, or the caller's `recipe_name` run variable |
| `wrangles_user` | `WRANGLES_USER` from run variables or the environment, then XL's `user_email`, then the configured Wrangles login |

Once the companion WranglesXL and WranglesPY updates are both deployed,
WranglesXL supplies the Recipe editor's displayed name and its existing user
email automatically. Existing recipes need no edits. With an older XL client,
provide `recipe_name` as a run variable or set `metadata.recipe_name` on the
step. Python callers can likewise pass
`variables={"recipe_name": "Product classification"}` to `recipe.run` for an
inline recipe. Anonymous nested recipe steps inherit the enclosing name.

Direct `wrangles.extract.ai` calls use the configured Wrangles login; when
called from inside a recipe, they also use that recipe's context. Missing
labels are omitted. Only these selected labels are added automatically, using
already available context without another authentication request. They help
diagnose runs and are not authenticated audit identities.

Use explicit `metadata` to override either label or attach other labels:

```yaml
wrangles:
  - extract.ai:
      input: Description
      api_key: ${OPENAI_API_KEY}
      metadata:
        recipe_name: Product classification
        wrangles_user: ${WRANGLES_USER}
        batch: trial-01
      output:
        Product Type:
          type: string
```

For an explicit user override in XL, `${user_email}` is also available.
`metadata: {}` disables all automatic labels for that step. Otherwise,
explicit values take precedence and available automatic labels fill the
remaining slots. OpenAI permits up to 16 string pairs, with keys up to 64
characters and values up to 512 characters; see the
[Responses API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create).
Automatically discovered labels are shortened to 512 characters if needed;
invalid explicit metadata fails before any OpenAI request.

Metadata is forwarded with both Responses and Chat Completions requests and
is separate from model instructions. Stored Responses logs show the labels
when response storage is enabled. Effective metadata is part of the local
result-cache identity, so changing a label causes a cache miss. It does not
change the OpenAI prompt-cache key or enable workflow tracing.

## Instructions

Use `instructions` for guidance that applies to every input row:

```yaml
wrangles:
  - extract.ai:
      input: Description
      api_key: ${OPENAI_API_KEY}
      instructions:
        - Prefer explicit evidence over inferred evidence.
        - Normalize dimensions to inches.
      output:
        Product Type:
          type: string
```

Instructions are useful for decision rules, evidence priorities,
normalization requirements, or other behavior that applies to the complete
extraction. The former `messages` parameter remains available as a compatibility
alias but is no longer advertised in the recipe schema. Do not provide both.

## Nullable output fields

Defined output keys remain required so strict Structured Outputs always return
the complete response shape. Top-level values are nullable by default, allowing
the model to return JSON `null` when the input does not support a value. Named
nested properties are non-null by default. Python
represents that value as `None`; presentation layers such as WranglesXL may
convert it to an empty cell or empty string at their serialization boundary.

Nullable enums automatically include JSON `null`. In an Excel Enum cell, an
unquoted `null` token means JSON `null`; combining it with `Nullable: FALSE` is
rejected. Use an explicit JSON string list such as `["null"]` only when the
literal word is an intended enum value. A future or existing saved-model
`Nullable` column is supported: blank or `true` uses the nullable default,
while `false` explicitly opts out.

Saved-model Examples cells accept strict JSON or restricted, human-friendly
YAML-like values. Pipe-delimited lists are preferred; comma-delimited values
remain compatible. For example, these are compiled into structured examples:

```text
{value: 12, uom: VDC},{value: 110, uom: VAC}
Ceramic Tile | Slate
```

The compiler uses JSON-compatible scalar rules and rejects YAML tags, anchors,
aliases, duplicate keys, and non-JSON values. Users do not need to quote every
object key and value.

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
Plain, multiline Example Input text remains text even when its lines use a
`Label: value` format. Use an explicitly bracketed object such as
`{Title: drill, Voltage: 20V}` only when the runtime input is itself structured.

An object-valued expected output must include every named nested property that
does not allow null. Omitted nullable properties are filled with JSON `null`.
For example, `{value: 120}` is incomplete for the default
`value: number | uom: string` schema; either supply `uom` or define that child
with `nullable: true` in a complete property schema.

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
record. Their output may omit nullable top-level fields: the compiler inserts
`null` so every example demonstrates the complete required response shape.
Required non-null nested properties must still be supplied. Unknown fields and
values that do not match the output schema fail during compilation. Optional
`name` and `notes` metadata are included in model guidance at both levels.

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
prompt, schema, model options, endpoint, response storage, effective metadata,
and exact serialized input. A change to any of these produces a cache miss.
Errors, timeouts, invalid structured responses, and oversized values are not
cached.

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
| `WRANGLES_EXTRACT_AI_CACHE_LOG_EVERY` | Emit aggregate counters every N lookups; `0` disables aggregate logs |

Cache telemetry contains aggregate counters and sizes plus INFO-level
`extract_ai_cache_lookup` events. Lookup events contain a hashed `request_key`
and an outcome (`miss`, `hit`, `coalesced`, or `batch_duplicate`), never input
values or credentials. `wrangles.ai_cache.stats()` returns the current counters,
and `wrangles.ai_cache.clear()` clears the warm-process cache. Set the
`wrangles.ai_cache` logger to WARNING to suppress per-lookup events.

## Dynamic object schemas

Fixed object definitions use strict structured outputs. An object with
`additionalProperties: true`, a schema-valued `additionalProperties`, or no
named properties is treated as a dynamic dictionary. Dynamic definitions use
non-strict provider mode and are validated locally so unknown keys can be
preserved without opening the top-level response object.

## PDF and image attachments

`extract.ai` can send the original PDF pages or images to a vision-capable
OpenAI model through the **Responses** protocol. No Docling, image conversion,
local GPU, or separate API client is required. The model must support both
visual input and structured output (for example, `gpt-4.1` or `gpt-5.4`).
Choose the actual model ID available to your OpenAI project, not an application
display name. Known incompatible legacy/text/audio-only models are rejected
locally; other model IDs, account access, document validity, and context-window
limits are checked by the provider. A rejected visual request is never retried
as text-only. Chat Completions, other providers, streaming, and background
Responses are not supported for this attachment contract.

### Explicit input contract

For a **single Python input**, pass an ordered `attachments` list:

```python
[{"path": "/data/specification.pdf", "id": "datasheet"},
 {"path": "/data/photo.png", "id": "photo", "detail": "high"}]
```

- `path`: local filesystem path (`str` or Python `Path`); relative paths are
  relative to the process working directory, **not the recipe file**.
- `id`: optional unique identifier within the record; defaults to `source-1`,
  `source-2`, etc., in attachment order. Use 1–64 letters, digits, dots,
  underscores, or hyphens, starting with a letter or digit.
- `detail`: images only, `auto` (default), `low`, or `high`. Higher image detail
  can use more tokens. Do not supply it for PDFs.
- Supported formats: PDF, PNG, JPEG (`.jpg`/`.jpeg`), and WebP. The extension and
  file signature must agree; full decoding/validation remains provider-side.
  GIF, raw bytes, Base64/data URLs, HTTP URLs, and provider file IDs are not
  supported in this first slice.

Use `input=None` for attachment-only extraction, or supply text/a record for
context. Omitting `attachments` preserves the original text-only request.
Ordinary strings containing paths or URLs—and ordinary dictionaries containing
a `path` key—are **never** automatically opened or uploaded.

A Python **input list still means separate extractions**. When supplying
attachments, provide a list of attachment lists with exactly the same length,
in the same order. Use `[]` for a text-only record. There is no implicit
broadcasting in Python. Return shapes, structured schemas, saved definitions,
and configuration precedence are unchanged.

```python
import os
import wrangles

fields = {
    "summary": "Summarize the explicitly visible product information",
    "source_id": "ID of the attachment supporting the summary",
    "page": {"type": "integer", "description": "PDF page, starting at 1; null for an image"},
    "quote": "Short supporting quote, or null when no text is visible",
}
options = dict(
    api_key=os.environ["OPENAI_API_KEY"],
    model="gpt-5.4",
    output=fields,
    timeout=180,
    threads=1,
    retries=0,
    reasoning={"effort": "medium"},
    max_output_tokens=16000,
    store=False,
)

# PDF only
document = wrangles.extract.ai(
    None, attachments=[{"path": "/data/specification.pdf", "id": "datasheet"}],
    **options,
)

# Standalone image, then a separate record combining text and an image
records = wrangles.extract.ai(
    [None, "Read the rating label; do not infer hidden values."],
    attachments=[
        [{"path": "/data/diagram.png", "id": "diagram"}],
        [{"path": "/data/photo.jpg", "id": "label", "detail": "high"}],
    ],
    **options,
)
```

To combine multiple attachments in one extraction, use the first list above
with scalar input, not as the `input` argument.

### Normal YAML recipes

Recipes use the same ordered descriptor list. A literal `path` attaches that
file to **each selected row**. Alternatively, use `column` instead of `path`
to take one local path string from that column in each row. Column names are
exact, not wildcard selections; do not supply both `path` and `column`.
Attachment columns are resolved independently of text `input` selection.
Null/empty attachment paths fail validation; filter such rows first or use
separate recipe steps for records with different attachment sets.

For a dataframe containing multiple `Context` and `Image Path` rows:

```yaml
wrangles:
  - extract.ai:
      input: Context
      attachments:
        - column: Image Path
          id: photo
          detail: high
        - path: /data/reference.pdf
          id: reference
      api_key: ${OPENAI_API_KEY}
      model: gpt-5.4
      timeout: 180
      threads: 1
      retries: 0
      reasoning:
        effort: medium
      max_output_tokens: 16000
      store: false
      output:
        summary: Describe the visible product and compare it with the reference
        source_id: ID of the source supporting the description
```

This creates one extraction per row, pairing that row's context and photo with
the reference PDF. `input: []` explicitly omits text for attachment-only rows;
omitted `input` still sends all dataframe columns as text. Existing `where`,
row order, output formats, and saved-model output mapping remain intact.
Environment variables, recipe variables, and existing model/group-scoped
credential resolution still supply `api_key`; attachment code does not select
credentials or modify global client state.

### Limits, memory, time, and storage

The library imposes conservative limits (MiB = 1,048,576 bytes):

| Limit | Value |
| --- | --- |
| Attachments per record | 16 |
| Individual decoded file | 20 MiB |
| Combined decoded attachments per record | 32 MiB |
| Unique local-file snapshots per Python call/recipe step | 128 MiB |

Reduce batch size or split documents when these limits are reached. All files
are checked before submitting the batch. Each unique resolved path is read
once per invocation; requests and retries use that same immutable snapshot.
Base64 encoding adds roughly one-third to the file size and request/HTTP
serialization adds memory overhead. Multiple workers can hold encoded requests
at once: start with `threads: 1` for large documents.

Files are sent inline in the Responses request. There are **no separate Files
API uploads or file IDs to clean up**. Input content goes to the configured
endpoint with the resolved credential. Existing `store: true` defaults also
apply to attachments; use `store: false` when appropriate and follow your
provider/project retention policy. Local snapshots are not persisted by the
library; the result cache stores only successful extracted values.

Cache identity includes ordered source IDs, content hashes, media types, image
detail, text association, and existing model/schema/prompt/options/credential
settings. Replacing bytes at the same path invalidates the result even if size
and timestamps are unchanged. A file changed during an invocation is seen by
the **next** invocation, not halfway through retries.

Visual inputs can take substantially longer and cost more than short text.
Text-only runtime defaults are unchanged: 12 seconds per attempt, 32 workers,
and 1 retry. Set `timeout`, `threads`, `retries`, reasoning, and
`max_output_tokens` explicitly for trials. The output budget includes reasoning
tokens; it is not just the final JSON size. An incomplete attempt may already
be billable. Retries repeat the same request and budget—they do not
automatically increase it. Start with `retries: 0`, inspect diagnostics, then
adjust the budget deliberately. The timeout is per attempt, not a whole-batch
deadline. These examples are not a claim that a long-running visual call fits
WranglesXL's request window or the deployed Lambda's resource limits.

See OpenAI's [PDF inputs](https://developers.openai.com/api/docs/guides/file-inputs)
and [images and vision](https://developers.openai.com/api/docs/guides/images-vision)
for provider-side requirements and limitations.

### Attempt accounting and source references

Enable INFO logging for `wrangles.openai_responses` to retain JSON
`openai_request_attempt` events. Each event includes a local `call_id`,
1-based `attempt`, hashed `request_key`, requested and returned model,
response/request IDs, HTTP/response status, outcome, elapsed request seconds,
and provider usage. Attachment source IDs and hashes associate the attempt
with the original inputs without logging binary content. Retries share a
`call_id`; a later new model call receives a new one.

Events cover successful, failed, incomplete, invalid structured, and transport
attempts—even when the wrangle ultimately raises. Missing usage/counts are
unknown (`null`), not zero. Cached-input, cache-write, and reasoning breakdowns
are retained when returned. Reasoning is already part of provider output
tokens: **do not add it again**. Sum input/output counts across actual attempt
events for accounting; apply your own model-specific prices and effective
dates. Unknown usage (including a timed-out request that may still be running
at the provider) makes the total incomplete. No price table is built in.

`extract_ai_cache_lookup` events distinguish local hits and duplicate
suppression from misses. Their hash matches the attempt's `request_key`.
A local hit makes no provider call and emits no new attempt usage. OpenAI's
reported cached-input tokens instead describe **provider prompt-cache** reuse
on a new request. Neither diagnostic stream changes extraction return shapes
or enables an external tracing exporter. Capture these logs in the caller's
normal logging destination; disabling INFO means the local attempt record is
not retained. Normal diagnostic events exclude full text, paths, binary/
Base64 payloads, API keys, and arbitrary metadata values.

Each PDF is sent with an ID-based filename; each image/PDF has an adjacent
source-ID label in the model input. Use those IDs in caller-defined schemas
and prompts requesting page numbers, quotes, or image references, as above.
They are **model-produced claims requiring validation**, not trusted native
citations. This slice does not compute bounding boxes, crop locations, table
coordinates, or highlights.

### Validation and downstream handoff

Offline tests generate a tiny synthetic PDF and PNG, mock Responses, and check
payload bytes, source/row association, cache identity, credential isolation,
limits, schema compatibility, and incomplete-attempt accounting. They do
**not** measure extraction accuracy.

Live validation and the RSGroup SF_AMF60 integration check remain outstanding:
the implementation sandbox has no OpenAI credentials or RSGroup source PDF,
frozen checks, or local prototype/report. Before release, run the PDF-only,
standalone-image, and mixed text/image trials above with authorized inputs,
`cache=False`, explicit budgets, and INFO attempt logging. Retain every
attempt's usage/timing/IDs, including incomplete attempts; do not report only
the successful retry's cost. Run SF_AMF60 discovery/mapping and the 30 frozen
source checks in RSGroup, record the actual selected model/settings, and
review remaining extraction errors explicitly. The issue's prototype results
are motivation, not validation of this implementation. Product mapping,
Excel presentation, provenance matching, deployment, and UI exposure remain
downstream responsibilities.
