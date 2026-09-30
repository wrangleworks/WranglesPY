# Retrieve content from links

`search.retrieve_link_content` retrieves targeted content from URLs using the
Google URL-context client. In recipes, its `prompt` can include values from
other columns in the same row using `{{ column_name }}` placeholders.

## Use row values in the prompt

Add this step to your recipe's `wrangles` list:

```yaml
- search.retrieve_link_content:
    input: URL
    prompt: |
      retrieve the product specs for this item: {{ item_details }}
      verify the following attributes: {{ product_attribute_dictionary }}
    output: Verification Results
    client: google_url_context
    output_format: json
    threads: 10
    api_key: ${GEMINI_API_KEY}
```

Each row supplies its own `URL`, `item_details`, and
`product_attribute_dictionary`. The `input` setting selects the URL column;
prompt placeholders can reference **any column in the full input row**. Only
referenced values are inserted into the prompt. `${GEMINI_API_KEY}` uses the
existing recipe-variable syntax and is separate from column placeholders.

For example, these cell values:

```yaml
item_details: Stainless steel hex bolt, M8
product_attribute_dictionary:
  Material: Stainless steel
  Thread Size: M8
```

produce this prompt for that row:

```text
retrieve the product specs for this item: Stainless steel hex bolt, M8
verify the following attributes: {"Material":"Stainless steel","Thread Size":"M8"}
```

## Column names and values

Replace each character outside `A-Z`, `a-z`, `0-9`, and `_` in a source column
name with `_` when writing its placeholder. Case is preserved: `Item Details`
becomes `{{ Item_Details }}`. The resulting alias must start with an ASCII
letter or `_`; rename a column such as `2026 Sales` before referencing it.

A referenced alias must identify exactly one column. For example, `Item Details`
and `Item-Details` both normalize to `Item_Details`, so that reference is
ambiguous. Missing, ambiguous, or invalid references raise an error before any
retrieval provider calls.

String values are inserted as text. Dictionaries, lists, numbers, booleans, and
`null` are inserted as JSON text. Referenced values must be finite and
JSON-compatible: dictionaries need string keys, and values such as `NaN` or
infinity are rejected. A dictionary or list cell can therefore be referenced
directly without converting it to text first.

Substitution is literal and runs once. Placeholders accept column aliases only;
Python expressions, attribute access, and Jinja filters are not supported.
Braces inside inserted values stay literal, including dictionary keys and
nested string values. For example, a cell containing `{{ other_column }}`
inserts that exact text without looking up `other_column`.

Prompts without placeholders retain their existing behavior. Omitting `prompt`
continues to use the client's default prompt. This feature does not add a
`for_each` option.

## URLs and results

An input cell can contain a URL, a list of URLs, or search-result dictionaries
containing links. Every URL from the same row receives that row's rendered
prompt. Results remain grouped in a list in the corresponding output cell,
in the original URL order, even when requests run concurrently. Empty URL cells
produce empty result lists.

To retrieve from several input columns, supply equally many output columns;
they map by position. Each selected URL column uses the same row's prompt
values. With exactly one input column, two output names enable the existing
dual output mode: `output: [page_data, page_text]` stores the result list in
`page_data` and a formatted text summary in `page_text`. Empty URL cells produce
`[]` and an empty string respectively.

`output_format: json` or `markdown`, `model_id`, `client`, and `threads` retain
their existing meanings. See [AI configuration](ai_configuration.md) for model
and runtime settings.

## Model, thinking, and request options

The packaged defaults are `gemini-3.5-flash`, `thinking_level: minimal`, a
10-second deadline per URL, and no retries. Omitted options use the active AI
configuration, so a replacement catalog can change these defaults. Override
`model_id`, `thinking_level`, or `request_timeout_seconds` in the recipe when
needed. For example:

```yaml
- search.retrieve_link_content:
    input: URL
    output: Page Content
    api_key: ${GEMINI_API_KEY}
    model_id: gemini-3.6-flash
    thinking_level: minimal
    request_timeout_seconds: 10
    max_output_tokens: 2048
    seed: 42
```

`thinking_level` accepts `minimal`, `low`, `medium`, or `high`; support depends
on the selected model. Additional options such as `max_output_tokens`, `top_p`,
and `temperature` are passed as top-level Gemini `GenerateContentConfig`
settings. Explicit options override configured generation defaults. The
installed Google SDK validates these options; their availability depends on
the selected model and SDK version.

Retrieval manages `system_instruction`, `tools`, `response_mime_type`,
`response_modalities`, and `http_options`; those names and their SDK aliases
cannot be passed as additional options. Use `prompt`, `output_format`, and
`request_timeout_seconds` for the corresponding controls. For advanced thinking
settings, an explicit `thinking_config` replaces the entire thinking
configuration, including any `thinking_level`, rather than merging with it.

The positive, finite `request_timeout_seconds` value limits the total provider
request time for each URL, including any retries enabled in the AI catalog.
When the deadline expires, that URL returns a `Failure` result with an error
and no extracted content; its position in the output is preserved. Cancellation
and client cleanup may add a little time after the deadline. The deadline
applies separately to each URL after its worker starts, so batches that need
several waves of concurrent requests can take longer than 10 seconds.

## Direct Python calls

Column substitution applies to recipe execution, where a full row is available.
Direct calls to `wrangles.search.retrieve_link_content(...)` continue to use
the supplied prompt literally and do not resolve column placeholders. The
`thinking_level`, `request_timeout_seconds`, and additional Gemini generation
options are also available as Python keyword arguments.
