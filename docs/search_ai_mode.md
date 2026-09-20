# AI Mode Markdown trials

Run [run_search_ai_mode.py](../tests/fixtures/search_ai_mode/run_search_ai_mode.py)
in VS Code with the repository's `.venv`
interpreter. The runner passes its JSON-style sample records as a DataFrame to
`wrangles.recipe.run`. Set `SERPAPI_API_KEY` and `OPENAI_API_KEY` in your
existing environment, or the ignored `.env` file when `python-dotenv` is installed.

The runner and [recipe](../tests/fixtures/search_ai_mode/search_ai_mode_test.recipe)
live together in `tests/fixtures/search_ai_mode/`. The fixture
[README](../tests/fixtures/search_ai_mode/README.md) describes their sample data
and live/offline commands. Credentials are loaded from the repository's `.env`,
and relative replay/output paths start at the repository regardless of the
current working directory.

## Why Markdown and downstream extraction

The trials led to a separation between retrieving search evidence and
interpreting product information:

- Google's answer structure varied between headings, paragraphs, nested lists
  and tables. Supplier names, prices and references also appeared in different
  shapes. Section-specific parsing in the search wrangle accumulated fragile
  rules for each variation.
- In three same-search-ID comparisons (INA, Renold and Belden), the body returned
  by SerpAPI `output=md` matched `reconstructed_markdown` after removing
  frontmatter and surrounding whitespace. Markdown simplifies retrieval; these
  trials did not demonstrate more accurate or more complete search results.
- Some API answers contained fewer specifications, prices or references than
  browser answers. Neither the response format nor our tests established the
  cause. Locale, browser session and generation variability remain possible
  factors; a successful request does not guarantee browser-equivalent coverage.
- Product identity now leads the query. `search.ai_mode` retains the original
  Markdown and separates metadata, `standardize.clean` repairs supported
  encoding/LaTeX artifacts, and `extract.ai` interprets identity, specifications,
  offers, source relevance and price-to-reference associations. Reference IDs
  connect offers to sources instead of relying on aligned list positions.

The raw response remains available for diagnosis and replay. Extraction can
still make mistakes or find an uncertain product match; it cannot recover
information absent from the retrieved answer. AI Overview remains a separate
enhancement, with reusable content helpers available for that future work.
The [AI Overview research notes](search_ai_overview_research.md) capture the
conditional two-request trial, source limitations and proposed next steps.

## Pipeline and outputs

```text
search.ai_mode (output=md)
  -> ai_mode_results (original Markdown body)
  -> ai_mode_metadata (JSON-compatible frontmatter and transport status)
standardize.clean
  -> ai_mode_results_clean
custom.clean_ai_mode_links
  -> ai_mode_results_clean (viewer-label repair)
merge.to_dict
  -> Input Product Information (Mfr, MPN, Description)
extract.ai
  -> Product Description, Match Confidence, Specifications, references, Pricing
validate source URLs and offer references in place
  -> ai_mode_structured_meta
```

The search wrangle retrieves one answer per input row. It does not group
headings, flatten tables, interpret prices, select sources or call an extraction
model. The Markdown body retains its original whitespace, links, citations and
text. YAML frontmatter becomes a dictionary; YAML dates become ISO strings.
Metadata also contains `query`, `query_index`, `input_row_id`, `search_id`,
`status` and `error`. Provider metadata and search parameters remain nested.

```yaml
- search.ai_mode:
    queries: search_query
    id: ID
    output: [ai_mode_results, ai_mode_metadata]
    client: serpapi
    threads: 1
    location: null
    country: null
    language: null
```

One output column returns the Markdown body; two add metadata. Direct Python
`wrangles.search.ai_mode(query)` returns a dictionary with those two keys; a
list of queries returns dictionaries in input order. Each recipe row must
contain one query string; explode query lists before searching.

Blank queries are skipped without a provider request. Provider errors, missing
or malformed frontmatter/status, and empty successful answers are explicit
failures in metadata. Non-successful or empty answers do not enter extraction.
The client uses synchronous SerpAPI requests; it does not poll queued or
processing jobs or read Google's browser token stream. A successful provider
response does not establish that Google returned every available source.

This **replaces the experimental compact/complete/Markdown output contract**.
Remove `query_config` from `search.ai_mode`, change its outputs to the two shown
above, and perform structuring in subsequent wrangles. `query_config` is no
longer needed for response parsing. `n_results`, `num` and `google_domain` are
unsupported. These AI Mode parameter/output changes do not apply to
`search.retrieve_links`.

## Query and locale controls

The editable defaults near the top of the runner contain the input records,
paths, heading configuration, row limit, concurrency, extraction model,
reasoning, timeout/retries and locale. `NROWS = None` processes all rows.
The trial uses low reasoning effort for identity and source/offer associations; change
`EXTRACT_REASONING` alongside `EXTRACT_MODEL` to evaluate other settings.

The recipe's Jinja template begins with product identity:

```text
Search for RENOLD GY08B2S26I RENOLD SYNERGY GY08B2S26I DUPLEX CONN LINK. Summarize information in 3 sections: Product Description | Specifications (as name value pairs) | Pricing (including the supplier name and source link). Summarize the information you found (e.g. matched the part number, 5 sources, 3 prices), but do not ask follow-on questions.
```

`AI_MODE_QUERY` drives the prompt's summary instruction, heading labels and
optional suffix. Only `Description`, `Mfr` and `MPN` supply product information;
`ID` identifies the row. Extra fields such as `query` and `part_codes` remain
available in the DataFrame and JSON snapshot but are not inserted into the query.
The generated `search_query` is the exact text sent as `q`.

`LOCATION`, `COUNTRY` and `LANGUAGE` default to `None`, which omits those
request parameters. Explicit country/language values map to SerpAPI `gl`/`hl`,
matching the aliases used by classic search. For example, set `COUNTRY = "uk"`,
`LANGUAGE = "en"`, and `LOCATION = "London, England, United Kingdom"` for a
localized trial. Conflicting alias values are rejected. Omitting locale does
not reproduce a signed-in browser's location, history or session context.

## Cleanup and extraction

The recipe immediately applies `standardize.clean` with `unescape_unicode`
and `latex_to_text`. It preserves Markdown line breaks and destinations, and
leaves unsupported formulas intact for the model. Raw and cleaned bodies are
separate columns. Cleanup controls remain opt-in for other recipes.

The trial then applies `custom.clean_ai_mode_links` to the cleaned column. It
removes the exact trailing text `Go to product viewer dialog for this item.`
from Markdown link labels before extraction. Product wording, escaped
punctuation, link destinations and code examples are retained. The original
`ai_mode_results` remains untouched. This repairs the label only; it does not
turn a Google viewer link into a supplier URL or add it to accepted references.

`merge.to_dict` builds **Input Product Information** from `Mfr`, `MPN` and
`Description`, retaining blank fields. `extract.ai` receives that dictionary
alongside `ai_mode_results_clean`. The original input identity and the search
evidence have distinct labels. Web search is disabled.

The extraction definition uses the final column names directly under `output:`;
there is no outer extraction object, presentation wrapper or dictionary-split
step. The outputs are:

- **Product Description**: the field definition asks for a verbatim copy of the
  description passage from cleaned Markdown, excluding its heading and retaining
  its wording and Markdown. No downstream helper rewrites it. The strict schema
  controls output keys and types; faithful copying is a model instruction.
- **Match Confidence**: `Certain`, `Likely` or `Uncertain`, assessing product
  identity against all three input fields. Certain requires matching manufacturer
  and exact part number plus a compatible description; Likely indicates a probable
  match with incomplete identity evidence; Uncertain covers conflicts, different
  variants or insufficient evidence. An answer that repeats the requested MPN
  while citing only other parts is Uncertain; discarded references still count
  when evaluating that conflict. It is not a rating of price accuracy or
  reference count. Skipped extraction defaults to Uncertain.
- **Specifications**: a list of records such as `{"name": "Voltage", "value": "12 VDC"}`.
- **references**: selected relevant source records, including sources without prices.
- **Pricing**: offer records associated with references by ID.

For specifications, pricing and references, extraction interprets prose, lists,
tables and links and removes residual formatting and UI text. Near-match parts
and unrelated pages must not support product-specific claims. Quoted offers
remain even when no usable supporting link was supplied. The search's concluding
summary remains in the Markdown; it is not appended to Product Description.

`record_examples` is a list. Each example's `input` is a dictionary matching one
DataFrame row: `Input Product Information` and `ai_mode_results_clean`. Its
`output` is a dictionary with the five direct output keys. The examples cover
supplier-link association and mismatched reference evidence whose claimed product
description is retained verbatim while confidence is Uncertain.

An offer has this shape:

```json
{
  "price": 13.15,
  "currency": "USD",
  "uom": "pack",
  "source": "Supplier A",
  "reference_ids": ["02"],
  "price_text": "$13.15 USD per pack of 10, excluding VAT"
}
```

Its reference is a separate record:

```json
{"id": "02", "source": "Supplier A", "url": "https://supplier.invalid/product"}
```

IDs are local strings independent of Google's citation numbering. Join offers
and references by ID. Lists are **not positionally aligned or padded**. Multiple
offers may share a reference, and an offer may have multiple references.
Uncertain associations use an empty `reference_ids` list. Unknown price,
currency and unit are `null`; a dollar sign alone does not imply USD, and the
unit is never assumed to be each. `price_text` preserves ranges, quantities,
taxes, shipping and availability without currency conversion or unit pricing.

The final validator checks only reference and offer shapes, finite nonnegative
amounts, reference-ID integrity and whether each cleaned source URL occurs in
the supplied Markdown. It leaves Product Description, Match Confidence and
Specifications unchanged. It reuses the existing URL sanitizer to remove tracking parameters
such as `srsltid` while preserving functional parameters. It rejects invented
URLs, Google product viewers and opaque redirects. It does not fetch sources,
match supplier names, decide relevance or reconstruct missing destinations.
Rejected references, unmatched IDs and unselected candidate URLs remain in
`ai_mode_structured_meta`. A `complete` status means these structural checks
passed, not that the content or supplier association has been fact-checked.

The Markdown/frontmatter and URL helpers are engine-independent so a future
`search.ai_overview` can reuse them. Overview retrieval is not implemented here.

## Known recurring glitch: viewer text in description links

Google's product-viewer UI text can be appended directly to a product name in
the first sentence of a description. The Markdown link is syntactically valid,
but its label includes `Go to product viewer dialog for this item.` and its
destination is a Google shopping viewer, not a supplier page. This is a provider
formatting artifact, not product information.

Before cleanup (shortened product label and synthetic viewer URL):

```markdown
The [Renold \(GY08B2S26I\)Go to product viewer dialog for this item.](https://www.google.com/search?ibp=oshop&prds=productid:123) typically ranges in price...
```

Expected cleaned Markdown, with the product wording and destination retained:

```markdown
The [Renold \(GY08B2S26I\)](https://www.google.com/search?ibp=oshop&prds=productid:123) typically ranges in price...
```

This cleanup was removed during the Markdown refactor (`73f9b85a`). Because
Product Description copies cleaned evidence verbatim, the UI text then reached
the extracted description. The dedicated `custom.clean_ai_mode_links` step was
restored in `0bffe32f`, before `extract.ai`. Keep this formatting repair separate
from semantic extraction; filtering viewer URLs out of references does not
repair description text.

When changing the provider adapter, recipe or cleanup path, check these stages:

- **Raw `ai_mode_results`:** the artifact may remain intentionally, preserving
  the provider response for diagnosis.
- **`ai_mode_results_clean`:** the instruction must be absent from affected
  link labels; product names, escaped punctuation and destinations must survive.
- **Product Description:** the instruction must not reappear in the copied
  passage. The viewer URL still must not become an accepted source reference.

The matcher targets this exact instruction at the end of an inline link label.
Different wording or markup may require an update. If it reappears, retain the
new raw response under `.data/`, add a small sanitized regression example, and
adjust the targeted cleanup. Avoid broadly deleting product links or rewriting
the description to hide the symptom.

[Regression coverage](../tests/test_search_ai_extraction.py) includes
`test_viewer_label_cleanup_preserves_product_wording_links_and_raw_evidence`,
the full recipe's cleaned model input, and replay preservation. Keep those
checks when refactoring this pipeline.

## Captures, replay and evaluation

Each run prints its output paths and writes uniquely named XLSX and JSON files
under ignored `.data/`. The workbook shows structured fields, cleaned Markdown,
metadata and validation diagnostics. The JSON snapshot preserves the complete
DataFrame without Excel's cell-length limit.

With `WRITE_OUTPUTS = True`, the recipe requests `include_raw_response` and
saves each complete provider response, including frontmatter, as a separate
`*_row001.md` file. It then replaces the metadata's large `raw_response` copy
with `raw_response_file`. Raw Markdown files and JSON are the full-fidelity
artifacts when a spreadsheet cell is too small.

Set `REPLAY_FILE` to a new-contract JSON snapshot to repeat cleanup and extraction
without calling SerpAPI. Relative paths start at the repository. New output
names preserve the earlier evidence. Replaying earlier Markdown snapshots drops
the retired `search_ai_extracted` and `ai_mode_result_structured` wrapper columns.
Snapshots from the retired three-output
contract must be recaptured or converted first. `EXTRACT_ENABLED = False`
skips the model call and needs no OpenAI key; the structured fields remain empty,
Match Confidence is Uncertain, and diagnostics say `skipped`.
`WRITE_OUTPUTS = False` disables exports, and
`PRETTY_PRINT = True` prints returned records.

Offline tests cover Markdown transport, metadata errors, locale mapping, raw
capture/replay, failure skipping, actual recipe/schema integration with mocked
services, source validation and cleanup. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_search-ai_mode.py tests/test_search_ai_extraction.py tests/test_standardize_clean_markup.py --basetemp .data/pytest_ai_mode -p no:cacheprovider -q
```

Use a new `--basetemp` path for each trial. Live extraction quality should be
reviewed against the retained original Markdown and the direct extraction columns.
