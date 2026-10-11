# Search-result scoring

`compute.score_search_results` ranks structured web-search results for a product
using part numbers, supplier names, description terms, and URL signals. It
normally follows `search.find_links` in a Product Research Agent recipe.

The wrangle does not perform another search, visit the pages, verify stock, or
use an AI model. It evaluates the supplied titles, snippets, URLs, and search
metadata. A high score is a useful ranking signal, not proof that a page describes
the correct product.

Three kinds of information describe different aspects of a result:

| Information | Purpose |
| --- | --- |
| Numeric score and `scoring_details` | Rank results and explain the contributing points. |
| `part_code_matches` and `part_code_match_count` | Inspect the actual part-code evidence, with redundancy reduced. |
| `summary.filtered` and match-category fields | Decide whether a result satisfies the recipe's configured eligibility rules. |

## Inputs and recipe setup

### Input columns

Supply three to five column names in this order. Names are arbitrary; position
determines their role.

| Position | Role | Cell contents |
| --- | --- | --- |
| 1 | Search results | A list of search payload dictionaries; each contains `search_metadata` and a `search_results` list. |
| 2 | Suppliers | A supplier/manufacturer name or list of names and aliases. Used for brand text, supplier-domain, and context scoring. |
| 3 | Part codes | A candidate code or list of possible part codes. Used for identity and context scoring. |
| 4, optional | MPNs | The believed manufacturer's part number, or a list of candidates. Receives a higher default identity score. |
| 5, optional | Descriptions | A description or list of descriptions. Used for context scoring, not a separate description-match score. |

The text inputs accept scalar values or lists. Blank scalar values and empty
lists contribute no candidates. MPN data may be dirty or absent; it does not have
to be populated to score other codes. Include the MPN as the first element of
`part_codes` for completeness; the wrangle does not insert it automatically.

To use descriptions without an MPN, supply all five columns and leave the fourth
column's values blank. A fourth input is always interpreted as MPNs.

### Search payload

This synthetic example uses one query and one result:

```json
[
  {
    "search_metadata": {
      "query": "INA NATV6 track roller",
      "query_index": 1
    },
    "search_results": [
      {
        "input_row_id": 13,
        "source": "INA",
        "title": "INA NATV6-PP-A track roller",
        "snippet": "Replacement track roller",
        "link": "https://www.ina.com/product/natv6-pp-a",
        "google_rank": 1,
        "pricing": {
          "price": 12.5,
          "currency": "$",
          "availability": "In stock"
        }
      }
    ]
  }
]
```

Use absolute URLs and one-based `query_index` and `google_rank` values. Missing
indices are treated as query 1 and rank 1 for scoring, even though the corresponding
output metadata remains unpopulated. The `query` is retained for provenance;
context terms come from the other input columns, not by parsing this query string.

For the worked example below, the other input values are:

| Column | Value |
| --- | --- |
| `suppliers` | `["INA"]` |
| `part_codes` | `["NATV6-PP-A", "NATV6"]` |
| `MPN` | `NATV6-PP-A` |
| `Description` | `NATV6 track roller` |

### Recipe

```yaml
wrangles:
  - compute.score_search_results:
      input:
        - results
        - suppliers
        - part_codes
        - MPN
        - Description
      output:
        - scored_results
        - Score Summary
      must_match_part_code: true
```

One output name, or a one-element output list, receives a list of scored
dictionaries for each input row. Two names receive parallel lists of scored
dictionaries and formatted strings. These lists have the same length and order;
scoring does not expand the DataFrame into one row per search result.

There is no third output column for part-code evidence. That evidence is nested
inside each scored dictionary. An empty or non-list results cell produces empty
output lists.

## Result preparation and ordering

Results from all payloads in an input row are pooled before scoring. Results
without a link are omitted.

Repeated links are reduced using their host and path. For ordinary lowercase
URLs, this ignores the scheme, query string, fragment, and `www.` / `shop.` host
prefixes. A root slash is equivalent to an empty path. Other path differences,
such as a trailing slash on a non-root path, are not necessarily equivalent.

The first result for a normalized link is retained, except that a later URL
containing `shop.` replaces it. Its title, snippet, query metadata, and rank are
used; evidence from duplicate results is not merged. URLs that identify different
products only through query parameters can therefore collapse to one result.

The final list places unfiltered results first, followed by filtered results.
Each group is sorted by descending total score, with tied scores retaining their
existing order. `scored_result_index` is then assigned from 1 across the entire
list. It is not the original Google rank.

## How the score is calculated

The score is the sum of seven components, rounded to one decimal place:

```text
score = part_match_score + brand_score + context_score
        + position_weight + query_weight + supplier_site + product_url
```

| Component | Contribution |
| --- | --- |
| `part_match_score` | The higher of the MPN and other-part-code scores; they are not added together. An equal score prefers the MPN explanation. |
| `brand_score` | The strongest supplier/manufacturer text match in title, snippet, or URL. |
| `context_score` | The fraction of unique input terms matched, multiplied by `context_match_base`, rounded to one decimal place. |
| `position_weight` | A bonus for appearing earlier within the original query's search results. |
| `query_weight` | An additive bonus favoring earlier queries. It does not multiply the other components. |
| `supplier_site` | A bonus for a supplier-like hostname. |
| `product_url` | A bonus or penalty for the URL's apparent page type. |

Scores are not probabilities or percentages. Their scale depends on the weights,
and a non-product URL can contribute negative points. Pricing and the number of
part-code evidence records do not add points.

Rank, query-order, domain, and URL contributions follow fixed rules. The tunable
match and context settings are listed below.

### Part-number scoring

MPNs and other codes are compared separately against the title, snippet, and
URL. Comparisons ignore case and normalize punctuation, spaces, and supported
international characters.

With the default positive weights, a recognized MPN contributes 8 points and a
recognized other code contributes 6 points. Only one identity contribution is
used, regardless of how many codes or sources match.

The scorer uses a broad meaning of **exact**: a normalized candidate of at least
four characters contained anywhere in a normalized field receives the exact
score, even when it is embedded in a longer identifier. Shorter codes require
matching normalized tokens. The partial/variant scoring settings and categories
are retained, but ordinary longer-code containment already receives exact
points rather than a partial score.

This is different from the more precise `part_code_matches.match_level`. For
example, `NATV6` inside `NATV6-X-PP-A` can produce `other_code_exact` for scoring
and filtering, while its evidence record correctly says `partial`. Disabling
`allow_other_partial` does not reject such a scoring-exact result. Use the
evidence records when complete-code identity matters.

### Brand text and supplier-domain scoring

Supplier names are normalized and compared with the same three source fields.
A name equal to a complete field receives `supplier_exact_score` (3 by default).
A name embedded within a longer field receives `supplier_partial_base` (1 by
default). A source token of at least five characters contained within a longer
supplier name can receive 95% of that base. A fuzzy text match of at least 0.8
similarity can receive the similarity multiplied by that base. Partial text
contributions are rounded to two decimals, and only the strongest is retained.

The fuzzy supplier-text scoring cutoff is fixed at 0.8. The configurable
`fuzzy_match_threshold` instead affects context-term matching and whether the
supplier-text match sets `brand_found`.

Domain evidence is scored separately:

| Domain relationship | `supplier_site` |
| --- | --- |
| Normalized supplier name equals the hostname label immediately before the final suffix | 2 |
| One normalized name contains the other, and the contained name has more than four characters | 1 |
| Neither relationship is found | 0 |

For example, `INA` can match the `ina` label in `www.ina.com`. This is a naming
heuristic, not an authoritative manufacturer-domain registry. Compound suffixes
such as `.co.uk` and URLs without a scheme can weaken this signal.

`brand_found` is true when either supplier-domain evidence exists or the supplier
text match meets `fuzzy_match_threshold`. It does not require both. A positive
brand score and a true `brand_found` are therefore not interchangeable, especially
when the threshold is changed. There is no required-brand-match filter.

### Context scoring

Context terms include supplier names, part-code candidates, MPN candidates, each
complete description, and description words longer than two characters.
Normalized duplicates count once. Terms are compared with tokens from title,
snippet, and URL using normalized equality, containment, or fuzzy similarity at
`fuzzy_match_threshold`.

Each term contributes at most once, even if it appears repeatedly or in several
sources. The score is matched terms divided by all unique terms, multiplied by
`context_match_base` (2 by default). With no terms, it is zero.

The denominator includes whole descriptions and whole code candidates, not just
individual words. Context coverage is therefore not simply the percentage of
description words found. The explanation lists the matched input terms; the
`summary.matches` list also includes a display form of the selected part match.

### Original rank and query order

| Original `google_rank` | `position_weight` |
| --- | --- |
| 1–2 | 2.0 |
| 3–4 | 1.5 |
| 5 | 1.0 |
| 6 or later | 0.0 |

`query_weight` is `0.9` raised to `query_index - 1`, rounded to two decimals:

| `query_index` | `query_weight` |
| --- | --- |
| 1 | 1.00 |
| 2 | 0.90 |
| 3 | 0.81 |
| 4 | 0.73 |

For a link found in several queries, the retained duplicate's metadata determines
these contributions; the bonuses are not accumulated across queries.

### Product-page URL scoring

The URL signal uses path and query features, not page content:

| Signal | Effect |
| --- | --- |
| Root domain; top-level products collection (including translated names), brands, or industries page; any brands/industries path | Immediate `product_url` of -2. |
| Search, cart, account, login, blog, or category page pattern; a `.csv`, `.jpg`, `.jpeg`, `.zip`, `.docx`, or `.png` path | Immediate `product_url` of -2. |
| Product-like path segments such as `/product/`, `/item/`, `/sku/`, `/p/`, `/dp/`, or `/shop/`, including supported translated product forms | Positive signal. |
| Product identifiers in query parameters (`product_id`, `pid`, `item_id`, or `sku`) | Positive signal. |
| A hierarchy below a products collection; at least three path segments | Positive signals, stronger for deeper product hierarchies. |
| Final path segment with a hyphen and digit, or a sufficiently long digit-heavy identifier without underscores | Positive signal. |
| At least two entirely numeric path segments | Archive/repository demotion. |

Unless an immediate penalty applies, these signals combine into a final
contribution of 0, 1, or 2. The reason text describes the underlying signals;
numbers such as `(+2)` in that text are not necessarily the returned contribution.
For example, a slug-with-ID signal on its own can produce `product_url: 1`.
A neutral or negative URL score does not itself filter a result.

### Scoring settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `mpn_exact_score` | 8.0 | Exact-score MPN contribution, including the broad normalized-containment rule. |
| `mpn_partial_base` | 4.0 | Base for a partial/variant MPN contribution; containment can already receive exact points. |
| `part_code_exact_score` | 6.0 | Exact-score other-code contribution. |
| `part_code_partial_base` | 2.0 | Base for a partial/variant other-code contribution. |
| `supplier_exact_score` | 3.0 | Supplier name equal to a complete source field. |
| `supplier_partial_base` | 1.0 | Base for embedded, reverse-contained, or fuzzy supplier text. |
| `context_match_base` | 2.0 | Contribution when every unique context term matches. |
| `fuzzy_match_threshold` | 0.8 | Context similarity threshold and supplier-text threshold for `brand_found`; not a part-code evidence threshold. |

These settings change ranking, not the diagnostic evidence records. Keep exact
match weights positive: zero or negative exact weights can also change how the
score-based match categories are interpreted.

## Filtering and match categories

Filtering marks results; it does not remove their dictionaries or erase their
scores. This keeps rejected results available for analysis at the end of the
output list.

### Match categories

`summary.part_match_type` is one of the following scoring categories:

| Category | Meaning | Eligibility setting |
| --- | --- | --- |
| `mpn_exact` | An MPN receives its exact score. | `allow_mpn_exact` |
| `mpn_partial` | An MPN receives a positive partial score. | `allow_mpn_partial` |
| `other_code_exact` | No positive MPN match is recognized, and another code receives its exact score. | `allow_other_exact` |
| `other_code_partial` | No positive MPN match is recognized, and another code receives a positive partial score. | `allow_other_partial` |
| `none` | No scoring match is recognized. | Never an allowed match category. |

MPN categories take precedence over other-code categories. The category is not
necessarily the same as the source of `part_match_score` when custom weights
make an other-code score larger. Disabling the selected MPN category does not
make the wrangle fall back to an allowed other-code category.

In recipe output, `summary.part_code_found` is a boolean indicating whether this
category is allowed by the four `allow_*` settings. It can be false despite
visible matching evidence, or true on a blacklisted result.

### Filtering settings

| Setting | Default | Behavior |
| --- | --- | --- |
| `must_match_part_code` | `true` | Mark results whose scoring category is not allowed as filtered. |
| `allow_mpn_exact` | `true` | Allow the `mpn_exact` category. |
| `allow_mpn_partial` | `true` | Allow the `mpn_partial` category. |
| `allow_other_exact` | `true` | Allow the `other_code_exact` category. |
| `allow_other_partial` | `true` | Allow the `other_code_partial` category. |
| `blacklist_keywords` | Empty string | Mark URLs containing any listed substring as filtered. Accepts a comma-separated string or a list. |

With `must_match_part_code: false`, disallowed or unmatched categories are not
filtered for that reason, but `part_code_found` still reflects the allowed
categories. Blacklisting applies regardless of this setting.

A comma-separated blacklist string is trimmed and lowercased. List entries are
used as supplied, so use trimmed lowercase strings such as `["ebay", "aliexpress"]`.
They are literal substrings of the lowercased full URL, not regular expressions
or exact domain matches; title and snippet are not searched for blacklist terms.

The optional `filtered_reason` is `blacklisted (<keyword>)` or
`unauthorized match type (<category>)`. If both restrictions apply, the recipe's
unauthorized-category reason is the one displayed.

## Structured output

Each result dictionary has these top-level fields:

| Field | Contents |
| --- | --- |
| `summary` | Source, title, link, score, matching flags, and filtering decision. |
| `part_code_matches` | Reduced part-code evidence records, described below. |
| `part_code_match_count` | Evidence count before redundancy removal. |
| `pricing` | Supplied pricing/availability information, or an empty dictionary. |
| `scoring_details` | Numeric components, reasons, and display text for the selected identity and brand matches. |
| `metadata` | Search-query and original-result provenance. |

### Summary

| Key | Meaning |
| --- | --- |
| `scored_result_index` | One-based position after grouping and sorting. |
| `input_row_id` | The result's supplied input-row identifier; not inferred from the DataFrame index. |
| `source`, `link`, `title`, `snippet` | Fields from the retained search result. |
| `query` | Query string from its search payload. |
| `score` | Total points, rounded to one decimal place. |
| `part_match_type` | Scoring category from the match-category table. |
| `part_code_found` | Whether that category is allowed by the recipe. |
| `brand_found` | Supplier text or domain evidence meets the brand criteria. |
| `matches` | Matched context terms plus the selected part-match display text, which can contain Markdown emphasis. Not the reduced code-evidence list. |
| `filtered` | Whether blacklist or required-match rules reject the result. |
| `filtered_reason`, when filtered | Explanation of the rejection. |

### Scoring details

`score`, `part_match_score`, and `brand_score` are followed by their associated
explanations: `part_match_reason`, `brand_match_reason`, `part_match_visual`, and
`brand_match_visual`. Visual values are display text rather than additional
scores or evidence records.

The remaining numeric keys are `context_score`, `position_weight`, `query_weight`,
`supplier_site`, and `product_url`. Each has a corresponding `<key>_reason`.
These remaining components appear in descending contribution order. Consume
them by key rather than assuming a fixed position.

### Pricing and metadata

Pricing is passed through rather than independently retrieved or validated:

| Pricing key | Meaning |
| --- | --- |
| `price`, `currency`, `availability` | Supplied pricing fields; missing values can be null. |
| `vendor` | The retained result's `source`. |

Missing or empty incoming pricing produces `{}`. A nonempty pricing dictionary
can contain null values and does not mean a price or availability was confirmed.

| Metadata keys | Meaning |
| --- | --- |
| `query`, `query_index`, `status` | Retained payload's query context and search status. |
| `google_rank`, `highlighted_words`, `missing_words` | Retained result's original search details. |
| `search_date`, `response_time`, `google_url`, `search_id` | Supplied search provenance, preserved without reinterpretation. |

Absent metadata values remain null. Status, price, highlighted words, and missing
words are not separate scoring or filtering controls.

## Part-code evidence

### Evidence records

The keys in each record appear in this order:

| Key | Values or meaning |
| --- | --- |
| `match_type` | `MPN` for an MPN input, or `Codes` for a `part_codes` input. |
| `match_level` | `exact`, `stripped`, or `partial`. |
| `match_source` | `title`, `snippet`, or `url`. |
| `matched_code` | The matching text from the result, preserving its case and separators. |
| `input_code` | The input candidate, with surrounding whitespace removed. |

Matching is case-insensitive. `exact` means the complete source code matches the
input apart from case. `stripped` means the codes match after alphanumeric
normalization, which removes punctuation and spaces and folds supported
international characters. `partial` means the normalized input is contained in
a larger source code. Partial evidence requires at least four normalized input
characters to avoid incidental matches for short codes.

| Input code | Source text | Evidence level |
| --- | --- | --- |
| `NATV6-PP-A` | `natv6-pp-a` | `exact` |
| `LBBR14-2LS` | `LBBR 14-2LS` | `stripped` |
| `NATV6` | `NATV6-X-PP-A` | `partial` |
| `085-196-225` | `085-196-225.` | `exact`; sentence punctuation does not extend the code. |
| `085-196-225 M10` | `085-196-225 M100` | `partial`; the larger source code is retained. |

Evidence is independent of score weights and eligibility flags. Its precise
levels must not be substituted for the scorer's broader exact/partial categories
without deliberately adding a downstream identity rule.

### Redundancy removal and counts

Each result contains zero or one MPN record, placed before all Code records even
when the MPN match is partial. The strongest MPN evidence wins: exact before
stripped before partial, then the longer normalized input, then title before
snippet before URL.

Code records are removed when they repeat an MPN input that matched, their
normalized input is contained in the selected MPN input, or their normalized
matched text is contained in the selected MPN matched text. Remaining records
with the same normalized matched code are collapsed across sources, using the
same strength, input-length, and source preferences.

`part_code_match_count` is recorded before these reductions. It includes the MPN
repeated in `part_codes` and evidence from multiple sources, but does not count
identical duplicate candidates or repeated occurrences within one source. It is
an evidence count, not a count of distinct products or codes. No matches produces
an empty list and a count of zero.

For an MPN of `NATV6-PP-A`, codes `["NATV6-PP-A", "NATV6"]`, and a matching title
only, there are three raw records: one MPN, its Code copy, and the shorter Code.
Reduction keeps just the MPN record, while the count remains 3. Matching evidence
in both title and URL makes that count 6, as in the worked example.

## Worked result and formatted summary

For the example inputs and default settings above:

| Component | Points | Explanation |
| --- | --- | --- |
| Part match | 8.0 | MPN exact score; the 6-point other-code score is not added. |
| Brand text | 1.0 | `INA` is embedded in the title. |
| Context | 1.3 | Four of six normalized unique terms match: `INA`, `NATV6`, `track`, and `roller`. |
| Original rank | 2.0 | Rank 1. |
| Query order | 1.0 | Query 1. |
| Supplier domain | 2.0 | Supplier `INA` matches the `ina` hostname label. |
| Product URL | 2.0 | Product path and identifier-like slug. |
| **Total** | **17.3** | Sum of the contributions. |

The six context terms are `INA`, `NATV6-PP-A`, `NATV6`, `NATV6 track roller`,
`track`, and `roller`. The whole MPN and description are not matched as context
tokens here, even though the MPN separately receives its identity score.

This structured-output excerpt omits some provenance and explanation keys for
readability; the complete field definitions are above:

```json
{
  "summary": {
    "scored_result_index": 1,
    "input_row_id": 13,
    "source": "INA",
    "score": 17.3,
    "link": "https://www.ina.com/product/natv6-pp-a",
    "part_code_found": true,
    "part_match_type": "mpn_exact",
    "brand_found": true,
    "filtered": false
  },
  "part_code_matches": [
    {
      "match_type": "MPN",
      "match_level": "exact",
      "match_source": "title",
      "matched_code": "NATV6-PP-A",
      "input_code": "NATV6-PP-A"
    }
  ],
  "part_code_match_count": 6,
  "pricing": {
    "price": 12.5,
    "currency": "$",
    "vendor": "INA",
    "availability": "In stock"
  },
  "scoring_details": {
    "score": 17.3,
    "part_match_score": 8.0,
    "brand_score": 1.0,
    "context_score": 1.3,
    "position_weight": 2.0,
    "query_weight": 1.0,
    "supplier_site": 2,
    "product_url": 2
  },
  "metadata": {
    "query": "INA NATV6 track roller",
    "google_rank": 1,
    "query_index": 1
  }
}
```

With two output columns, the corresponding formatted string is:

```text
## --- Result 13.1 | Score: 17.3 | MPN Exact & Brand Match --- ##
Source:  INA
Link:    https://www.ina.com/product/natv6-pp-a
Title:   INA NATV6-PP-A track roller
Snippet: Replacement track roller
Pricing: $12.5 (In stock) via INA
Scoring Details: 17.3 pts total
  - part_match_score: 8.0 (Exact Match 'NATV6-PP-A' (MPN) in Title)
  - brand_score: 1.0 (Embedded Match 'INA' (Supplier) in Title)
  - product_url: 2 (Product Keyword in Path (+2), Slug with ID (+2))
  - position_weight: 2.0 (Rank 1)
  - supplier_site: 2 (Exact domain match)
  - context_score: 1.3 (Matched 4 terms ('INA', 'NATV6', 'track', 'roller') out of 6 from input query)
  - query_weight: 1.0 (Query Index 1)
```

The header uses `input_row_id.scored_result_index` when an input-row ID exists,
and just the result index otherwise. It adds a rejection badge for filtered
results and a query-number label when the input contains multiple query payloads.
The string includes source, link, title, wrapped snippet, available pricing, and
the score breakdown. It does not print the reduced evidence list or its count;
use the dictionary output for those fields.

## Recipe versus direct Python output

This guide primarily describes the recipe wrangle. The direct
`wrangles.compute.score_search_results` function shares the scoring and evidence
fields, but its calling and filtering contract differs:

| Aspect | Recipe wrangle | Direct Python function |
| --- | --- | --- |
| Inputs | Three to five ordered DataFrame column names. | Named lists: `payloads`, `suppliers`, `part_codes`, `mpns`, and `descriptions`. |
| Output | One dictionary-list column, optionally with a parallel formatted-string column. | A list of scored dictionaries. |
| `summary.part_code_found` | Boolean: is the scoring category allowed? | The scoring-category string itself. |
| `summary.part_match_type` | Stores the scoring-category string. | Not added. |
| Allowed-category flags | Four `allow_*` settings. | Not available; `must_match_part_code` requires any scoring match. |
| Blacklist argument | `blacklist_keywords`; comma-separated string or list. | `blacklist`; a list of lowercase substrings. |
| Missing-code rejection reason | `unauthorized match type (none)`. | `no part code match`. |

## Interpreting and tuning results

- Use MPN evidence for canonical identity, and other Code evidence to recover
  useful candidates when the MPN is missing or dirty.
- Use score weights to change ranking priorities. They do not make the evidence
  matcher stricter or turn a partial identity into a complete-code match.
- Use `must_match_part_code: false` to inspect broader results while retaining
  match flags and reasons. Blacklisted results still remain marked and last.
- Keep the structured output when downstream decisions depend on match source,
  code boundaries, or pre-reduction counts. Formatted summaries are for review.
- Treat domain, URL, price, and snippet signals as search evidence. They do not
  independently confirm product identity, seller authorization, or availability.
