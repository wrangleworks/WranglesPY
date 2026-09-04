# Search with Google AI Mode

`search.ai_mode` uses SerpAPI's Google AI Mode API to search for sources and
return the synthesized, cited answer in one request. It is intended to replace
the common `search.find_links` followed by `search.retrieve_link_content` flow
when URL-by-URL retrieval is not required.

## Industrial-product search

The input query contains the product evidence assembled by the caller. For
example:

```text
Manufacturer: SKF
Potential part codes: 6205-2RS, 6205 2RS
Description: deep groove ball bearing
```

By default, the wrangle asks AI Mode to find authoritative manufacturer,
product, supplier, and distributor pages; confirm exact manufacturer and part
identifiers; report important attributes and available pricing; cite sources;
distinguish facts from inference; and leave unknown values unknown.

Set `prompt` to replace that instruction for a different research task. The
query cell is appended unchanged to either prompt, preserving manufacturer
names and part-code punctuation.

## Recipe example

```yaml
read:
  - file:
      name: products.csv

wrangles:
  - search.ai_mode:
      queries: Product Search Query
      id: ID
      output:
        - AI Mode Results
        - AI Mode Text
      country: us
      language: en

write:
  - file:
      name: researched-products.xlsx
```

`Product Search Query` may contain a scalar query or a list of queries in each
row. Multiple query columns are also supported when each has one corresponding
output column. A single query column may instead have exactly two output
columns: structured results followed by readable text.

Blank, null, and `NaN` cells remain aligned as empty results and do not make a
provider request. The column named by `id` is copied to every source record as
`input_row_id`.

## Direct Python API

```python
import wrangles

result = wrangles.search.ai_mode(
    "Manufacturer: WESTFALIA\n"
    "Potential part codes: DN65\n"
    "Description: union nut",
    country="us",
    language="en",
)
```

A scalar query returns one dictionary. A list returns an ordered list of
dictionaries.

## Parameters

| Parameter | Description |
| --- | --- |
| `queries` | Query column name(s) in recipes, or query value(s) in Python. |
| `id` | Recipe input row ID column. |
| `output` | Structured output column, or structured/text output pair. |
| `client` | `serpapi` (default and currently supported provider). |
| `api_key` | SerpAPI key; defaults to `SERPAPI_API_KEY`. |
| `prompt` | Optional replacement for the default product-research prompt. |
| `threads` | Concurrent request count; minimum 1. |
| `country` | Friendly alias for SerpAPI `gl`; defaults to `us`. |
| `language` | Friendly alias for SerpAPI `hl`; defaults to `en`. |
| `location` | Human-readable search location. |
| `no_cache` | Request a fresh result rather than a SerpAPI cached response. |
| `include_raw_response` | Add the provider response to each payload; defaults to `false`. |

Other SerpAPI properties may be passed as keyword arguments through the direct
Python API. AI Mode requests always use the supported desktop device.

## Structured output

Every query payload has the same top-level shape:

```json
{
  "search_metadata": {
    "query_index": 1,
    "query": "Manufacturer: SKF ...",
    "search_type": "ai_mode",
    "search_id": "provider search id",
    "status": "Success",
    "search_date": null,
    "response_time": null,
    "json_endpoint": null,
    "google_url": null,
    "language": "en",
    "country": "us",
    "location": null
  },
  "status": "Success",
  "error": null,
  "search_results": [
    {
      "input_row_id": "row id",
      "query_index": 1,
      "google_rank": 1,
      "result_type": "reference",
      "title": "Source title",
      "link": "example.com/product",
      "source": "Example",
      "snippet": "Supporting source snippet",
      "pricing": {
        "price": 12.5,
        "currency": "USD",
        "availability": "In stock",
        "vendor": "Example"
      }
    }
  ],
  "extracted_content": {
    "answer_markdown": "The synthesized answer with citations.",
    "text_blocks": []
  }
}
```

SerpAPI `references`, source-bearing `quick_results`, `shopping_results`, and
`inline_products` become source records. `result_type` preserves their
provenance. Sources are deduplicated by cleaned link and title and ranked in
first-seen order. Pricing is included only when structured shopping data is
available.

`reconstructed_markdown` becomes `answer_markdown`; `text_blocks` is preserved.
The full provider payload is omitted unless `include_raw_response` is true.

## Empty, partial, and error results

- A successful response may have an answer but no sources or prices.
- Missing prices do not turn a successful response into a failure.
- Provider errors and request exceptions return `status: Failure`, a useful
  `error`, empty `search_results`, and empty extracted content.
- One failed query does not shift or remove other query results.
- The readable output includes the query, status, error, answer, numbered
  sources, snippets, and structured pricing that are present.

## Cost and caching

Each nonblank query may incur a SerpAPI Google AI Mode request and associated
provider charges. Review SerpAPI's current pricing and cache policy before
large batches. Cached responses can reduce repeated provider work; setting
`no_cache: true` requests a fresh response and may increase cost and latency.
Use `threads` to control concurrency.

## Unreleased release note

Added `search.ai_mode` for one-request cited search and synthesis through
SerpAPI Google AI Mode, with stable normalized source/content output, readable
dual output, direct Python support, and opt-in raw responses.
