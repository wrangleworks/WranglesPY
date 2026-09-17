# AI Mode trials

Run `run_search_ai_mode.py` in VS Code using the repository's `.venv`
interpreter. The runner supplies the example records as a DataFrame to
`wrangles.recipe.run`. Set `SERPAPI_API_KEY` in your environment, or in the
ignored `.env` file when `python-dotenv` is installed.

The runner's editable defaults include `NROWS`, concurrency, locale and the
shared query configuration:

```python
AI_MODE_QUERY = [
    {"base_query": "Provide the following product information:"},
    {"Product Description": "1-3 sentences including the product name and key features."},
    {"Technical Specifications": "List confirmed technical specifications."},
    {"Sources & Pricing": "List suppliers and available pricing with source links."},
    {"query_suffix": (
        "Use the requested headings exactly as written. "
        "Include only the requested sections, and do not include follow-up questions."
    )},
]
```

`search_ai_mode_test.recipe` uses this same variable for its Jinja query and
`search.ai_mode.query_config`. The template combines the prefix, ordered
heading instructions, each row's product details, and suffix. The temporary
configuration column is removed before searching.

```yaml
- search.ai_mode:
    queries: search_query
    id: ID
    query_config: ${AI_MODE_QUERY}
    output:
      - ai_mode_result
      - ai_mode_markdown
    client: serpapi
    threads: ${THREADS}
    country: ${COUNTRY}
    language: ${LANGUAGE}
```

Each row must contain one query string. Explode query lists before searching.
The first output is a dictionary, and the second is a string:

```text
ai_mode_result = {
    "Product Description": [original content blocks],
    "Technical Specifications": [original content blocks],
    "Sources & Pricing": [original content blocks],
    "references": [all original reference dictionaries],
    "meta_data": {query, input_row_id, provider metadata, parse diagnostics}
}
ai_mode_markdown = original reconstructed_markdown
```

Section values preserve paragraphs, lists, tables, nested blocks, links,
LaTeX and citation indexes. They are not inferred product attributes or
price dictionaries. References retain their original indexes and ordering;
they are not truncated, deduplicated, or requested again as a heading.

Heading matching ignores case and whitespace differences. When Google omits
the first heading and the response begins with paragraphs followed by the
second requested heading, those paragraphs populate the first section. This
fallback requires a successful response and no explicit first heading anywhere
in the answer. It records `meta_data.inferred_headings` and an `inferred_heading`
warning; `parse_status` stays `partial` to make the inference visible.

Other missing sections produce empty lists and warnings. Repeated headings
append to the same section. Unrequested headings and remaining preamble
content are preserved in
`meta_data.unmatched_sections` and `meta_data.unsectioned_text_blocks`.
`meta_data.parse_status` is `complete`, `partial`, `error`, or `skipped`.
Provider errors remain attached to the input row. Blank queries skip the
provider and return empty sections and Markdown.

`base_query` and `query_suffix` are prompt controls. All other configuration
keys must be unique headings. `references`, `meta_data`, and `raw_response`
are reserved output keys. Instructions must be strings.

The trial recipe retains raw Markdown and creates `ai_mode_markdown_clean`
using the opt-in `standardize.clean` Unicode/LaTeX controls and the runner's
link-label repair. Search itself does not clean or truncate either output.
The compact result omits duplicated raw payloads, but very large responses
can still exceed spreadsheet cell capacity. Set `include_raw_response: true`
only when the complete provider response is needed under `raw_response`.

This replaces the earlier experimental three-output contract: one output
now returns just the result dictionary; two return result and Markdown.
Remove `n_results` from AI Mode recipes, since all references are retained.
`google_domain` and `num` are also unsupported for AI Mode.
Classic `search.find_links` keeps its existing output and result limit.

For direct Python usage, `wrangles.search.ai_mode(query, AI_MODE_QUERY)`
returns an envelope with `ai_mode_result` and `ai_mode_markdown` keys. A list
of queries returns a list of these envelopes in input order.
