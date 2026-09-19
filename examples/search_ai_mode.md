# AI Mode trials

Run `run_search_ai_mode.py` in VS Code using the repository's `.venv`
interpreter. The runner supplies the example records as a DataFrame to
`wrangles.recipe.run`. Set `SERPAPI_API_KEY` in your environment, or in the
ignored `.env` file when `python-dotenv` is installed.
The recipe expands compact fields into columns and writes the selected trial
results to `ai_mode_results.xlsx`. Terminal pretty-printing is currently
commented out in the runner.

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
      - ai_mode_result_complete
      - ai_mode_markdown
    client: serpapi
    threads: ${THREADS}
    country: ${COUNTRY}
    language: ${LANGUAGE}
```

Each row must contain one query string. Explode query lists before searching.
The outputs are compact result, complete result, and original Markdown, in
that order. Supply one, two, or three output column names as needed.
Parsing uses the provider's structured JSON: first group blocks under the
requested headings, then derive compact values from those groups. The parser
does not reconstruct sections from Markdown or make another model call to
interpret the answer.

```text
ai_mode_result = {
    "Product Description": "The Example Power P12 supplies 12 VDC.",
    "Technical Specifications": [{"Output Voltage": "12 VDC"}, {"Output Current": "5 A"}],
    "Sources & Pricing": [{"Supplier A": "$13.17 USD per pack of 10"}],
    "references": ["https://example.invalid/product"]
}
ai_mode_result_complete = {
    "Product Description": [original content blocks],
    "Technical Specifications": [original content blocks],
    "Sources & Pricing": [original content blocks],
    "references": [all original reference dictionaries],
    "meta_data": {query, input_row_id, provider metadata, parse diagnostics}
}
ai_mode_markdown = original reconstructed_markdown
```

The compact result includes the requested headings and a flat list of
reference URLs. Paragraphs become text; list items and table rows become
flat lists. Sections whose heading includes "specification" or "specifications"
contain single-entry dictionaries such as `{"Inner Bore Diameter": "6 mm"}`.
Names and values are separated at the first colon or spaced en/em dash;
units, ranges and repeated specification names are retained. Unlabeled content
is preserved as `{"text": "original content"}` instead of inventing a name.
Section content omits URLs, block wrappers, citation metadata,
Google's product-viewer instruction, and recognized follow-up invitations.
It reuses `standardize.clean` to repair encoding, Unicode escapes and simple
LaTeX units. Tables follow the header-and-row structure in the
[SerpAPI table example](https://serpapi.com/google-ai-mode-api).

In sections whose heading includes "price", "prices", or "pricing", entries
written as `Supplier: details`, `Supplier – details` or `Supplier — details`
become single-entry dictionaries. It also recognizes supplier sentences such
as `Available at Supplier for $13.17 USD`, including the corresponding
offered/sold and from/by variations. Navigation
phrases such as "via Supplier Product Page" are removed. Price ranges,
currencies, per-pack quantities and other price qualifiers stay as text;
no currency or price is guessed. Text without an identifiable supplier or value
is preserved as `{"text": "original content"}`, keeping every pricing entry a
dictionary. Multiple offers from one supplier remain separate entries.
Supplier/price/link tables omit navigation columns and a single price-column
heading from compact values. Currency conversions, quantity columns and labels
that distinguish multiple price columns are retained. Links and citation IDs
attached to table cells remain available for associating offers with sources.

The complete result preserves paragraphs, lists, tables, nested blocks,
links, LaTeX and citation indexes, with three noise filters: `srsltid` URL
parameters, `source_icon` fields and `thumbnail` fields are removed throughout.
URL pruning reuses `wrangles.web.clean_link` with full URLs and remaining
query encoding preserved. Other query parameters and fragments remain intact.
Classic search retains the sanitizer's existing defaults.

Complete references retain their original indexes, ordering and duplicates.
Compact references combine direct web URLs from that list with `snippet_links`
in the requested sections, including nested lists and tables. The shared
`wrangles.web.clean_link` sanitizer removes known tracking parameters such as
`srsltid` and `utm_source`, preserving full URLs, functional query parameters,
encoding and fragments. The initial URL list removes duplicate cleaned URLs
and keeps first-seen order: provider references first, then section links.

Compact pricing and references are then aligned by position so they can be
zipped. Each offer is associated using its inline source URLs first, then
reference indexes matched against provider reference IDs, then a unique
normalized supplier/site-name match. Different regional sites or multiple
pages with the same source name are not resolved by guessing from the domain.
Inline links can associate an offer with more than one source URL.

Pricing follows reference order, which can differ from the order of offers in
Google's answer. A reference without an offer receives `{site_name: ""}`, using
the provider's source name or the URL hostname without `www.`. Multiple offers
for one URL repeat that URL in the final reference list. Unmatched prices are
appended with `""` as their reference. If more than one pricing section is
requested, all pricing lists use the same reference positions and empty-value
padding.

Google product-viewer URLs containing product/catalog IDs are omitted from
compact references; they remain in the complete output. Supplier URLs are
collected from the supplied content, without guessing destinations from IDs.
This populates compact references when the provider's reference list is empty
but inline supplier links are available. If no direct source URLs were returned,
each remaining pricing entry has an empty reference string; without pricing
entries, compact references remain empty. References are not requested again
as a heading.

Heading matching ignores case and whitespace differences. It recognizes native
heading blocks and paragraph blocks containing an exact requested label, either
alone or followed by a colon and content (for example, `Product Description: The
INA roller ...`). Content after the label stays in that section, retaining its
links and citation indexes in the complete result. Matching applies only at the
start of a top-level heading or paragraph; nested blocks and ordinary mentions
of a heading stay as content. The original Markdown remains unchanged.

When Google omits the first heading and the response begins with paragraphs
followed by the second requested heading, those paragraphs populate the first section. This
fallback requires a successful response and no explicit first heading anywhere
in the answer. The complete result records `meta_data.inferred_headings` and an `inferred_heading`
warning; `parse_status` stays `partial` to make the inference visible.

Other missing sections produce empty lists and warnings in the complete result.
Compact pricing sections still receive an entry for every source URL.
Repeated headings
append to the same section. Unrequested headings and remaining preamble
content are preserved in
`meta_data.unmatched_sections` and `meta_data.unsectioned_text_blocks`.
`meta_data.parse_status` is `complete`, `partial`, `error`, or `skipped`.
Provider errors remain attached to the input row. Blank queries skip the
provider and return empty sections and Markdown.

The current parsing boundaries are deliberate and useful when reviewing new
features:

- Section recognition uses normalized exact labels and colon-delimited labels,
  not synonyms or semantic matching. Only the narrowly defined missing-first-
  heading case is inferred.
- Compact output types are selected by heading words: specification(s) produces
  name/value dictionaries; price(s)/pricing produces supplier/value dictionaries.
  Other sections become joined paragraph text or a list when lists/tables occur.
  The query instructions themselves do not define an output schema.
- Tables use the `table` rows, treating the first row as headers when there are
  multiple rows and the first cell as the key. Alternative `detailed` and
  `formatted` representations are preserved in complete blocks but are not
  independently parsed or used to recover links.
- Unrecognized supplier/specification text remains in a `text` dictionary.
  Price values stay as strings; the parser does not convert currencies, infer
  missing amounts or resolve Google product IDs to supplier URLs.
- Unicode and simple inline LaTeX cleanup are conservative. Numeric dollar
  amounts, ranges and price qualifiers are protected. Unsupported formulas,
  code and link destinations are left alone by the Unicode/LaTeX conversion.
- Unknown content block fields remain in the complete result but may not
  contribute to compact text. Extra top-level provider field names are listed
  in `meta_data.unmapped_fields`; their values require `include_raw_response`.
  Parsing warnings describe structural issues, not factual accuracy or
  confidence in a price/source association.

`base_query` and `query_suffix` are prompt controls. All other configuration
keys must be unique headings. `references`, `meta_data`, and `raw_response`
are reserved output keys. Instructions must be strings.

The trial recipe retains original Markdown and creates `ai_mode_markdown_clean`
using the opt-in `standardize.clean` Unicode/LaTeX controls and the runner's
link-label repair. The third output stays exactly as returned by the provider,
including its original URLs. Large complete responses can still exceed
spreadsheet cell capacity. Set `include_raw_response: true` when the provider
payload is needed under `ai_mode_result_complete.raw_response`; the same
three noise filters apply there. The compact output never includes that copy.

This replaces the earlier experimental output contracts: one output returns
the compact result, two add the complete result, and three add Markdown.
Remove `n_results` from AI Mode recipes, since all references are retained.
`google_domain` and `num` are also unsupported for AI Mode.
Classic `search.find_links` keeps its existing output and result limit.

For direct Python usage, `wrangles.search.ai_mode(query, AI_MODE_QUERY)`
returns an envelope with `ai_mode_result`, `ai_mode_result_complete`, and
`ai_mode_markdown` keys. A list of queries returns a list of these envelopes
in input order.
