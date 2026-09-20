# AI Overview research and proposed direction

Research date: 2026-09-20. Status: evaluated, implementation deferred.

The conditional two-request SerpAPI flow retrieved AI Overview answers for all
three trial products. It did **not** establish that Overview consistently
returns more complete or accurate product information than AI Mode. We continued
with the [AI Mode Markdown pipeline](search_ai_mode.md); `search.ai_overview`
remains a separate enhancement.

These notes preserve the Overview investigation separately from the implemented
AI Mode contract. They combine the saved provider responses, an archived HTML
inspection and primary documentation. The supplied Gemini conversation helped
identify hypotheses; its explanations are not treated as verified findings.

## Retrieval flow and timing

Start with `engine=google` and inspect the raw `ai_overview` object before
classic link-result normalization:

1. If the answer is embedded, consume its content directly.
2. If `page_token` is returned, immediately request `engine=google_ai_overview`
   with that token. The classic result also supplies `serpapi_link`.
3. If neither usable content nor a token exists, distinguish an unavailable
   Overview from a provider error; an otherwise successful classic search is
   not sufficient evidence of a successful Overview.

SerpAPI documents that the rendered preview can report that an Overview cannot
be generated even when a usable token is present. Inspect the JSON state instead
of treating that preview message as the final result.
[SerpAPI embedded Overview documentation](https://serpapi.com/ai-overview#api-examples-example-with-an-extra-request-required).

The documentation checked on the research date gives conflicting token windows:
four minutes on the embedded-results page and one minute on the dedicated
endpoint page. Follow tokens immediately within each row's worker and design
for the shorter window; do not collect a whole batch of tokens first.
[Embedded flow](https://serpapi.com/ai-overview#api-examples-example-with-an-extra-request-required),
[dedicated endpoint](https://serpapi.com/google-ai-overview-api).

This content-retrieval step is distinct from SerpAPI `async=true`. That option
submits a search job for later archive retrieval; the default synchronous call
waits for a response. The trial used synchronous calls. Switching to async does
not itself establish more complete answers.
[SerpAPI request controls](https://serpapi.com/google-ai-overview-api).

## What the live probe returned

The 2026-09-20 probe used the runner's INA, Renold and Belden samples.
Each initial request sent `engine=google`, the
recipe-rendered `q`, `output=json` and `no_cache=true`. No country, language,
location, domain, device or async overrides were supplied. The provider reported
its own google.com/desktop defaults.

All three initial responses contained only `page_token` and `serpapi_link` in
`ai_overview`. Each worker immediately made the dedicated request with
`output=json`. All six requests returned HTTP 200 and provider status Success.
No downstream extraction model was called. A later Renold HTML archive read
did not create another search.

| Product | Specification entries | Pricing/availability entries | Cleaned inline source URLs | Provider reference entries | Combined request time |
| --- | ---: | ---: | ---: | ---: | ---: |
| INA NATV6-PP-A | 13 | 5 | 6 | 0 | 8.17 s |
| Renold GY08B2S26I | 9 | 2 | 2 | 0 | 8.98 s |
| Belden FI3F001N0W | 6 | 1 | 1 | 0 | 21.78 s |

These are counts of returned content, not independently verified facts or
distinct suppliers. The six INA URLs include a product page and homepage for
one supplier. Its pricing list contains one entry with a missing supplier label.
Renold's specification list includes a malformed MPN entry containing only
product-viewer navigation text. Belden's single availability entry requires an
inquiry/account login and contains no numeric price.

Every dedicated answer had `text_blocks` and all three requested headings.
None contained `references` or `reconstructed_markdown`. Missing link labels,
product-viewer boilerplate and other markup issues persisted.

**Comparison boundary:** this probe used the earlier instruction-first query
beginning "Provide the following product information", before the product-first
query was adopted. It is not a controlled comparison against the final AI Mode
recipe. Renold returned two suppliers (Acorn and Klium), while the supplied
browser example had four; one trial does not establish a general ranking of
the two endpoints.

## Sources and the organic-results fallback

Renold's archived HTML included Acorn and Klium source cards despite the absence
of a JSON `references` list. Both destinations were available in JSON
`snippet_links`. The pricing answer itself also contained only those two
suppliers. This distinguishes a missing reference list from missing answer
content; it does not show that two additional prices were lost in JSON parsing.
The HTML inspection read archived text and cards, not a live browser's visibility
state.

Each initial classic response also contained nine `organic_results`. They were
not reliable substitutes for Overview citations:

- Renold's results were unrelated pricing pages, including Intercom, Datadog,
  New Relic and Stripe.
- INA included two specific product listings, a general bearing catalog and
  several unrelated labeling/food pages.
- Belden included generic cable guides and category/supplier pages, with no
  exact requested MPN in the returned titles, snippets or URLs.

None of those organic URLs overlapped the cleaned inline Overview sources.
Instruction-heavy wording may have contributed to the unrelated results; this
probe does not prove the cause.

For a future implementation, retain organic results as **separate candidates**
with provenance. Prefer provider references and inline links when present, then
let `extract.ai` assess relevance and associations. A relevant organic result is
not automatically a citation supporting an Overview claim. Preserve whether a
source came from an Overview reference, an inline link or an organic result.
Use reference IDs to connect offers and sources, as in the current AI Mode
recipe; do not restore positional alignment or invent empty offers for unpriced
references.

## Findings versus hypotheses

The deferred token proves that a follow-up request is needed. It does not prove
that the answer will be richer, that a scrape finished too early or that Google
is performing deeper research. Google says both AI Overviews and AI Mode may
issue multiple related searches to build an answer; that general capability
does not explain the delay in a particular response.
[Google's description of AI search features](https://developers.google.com/search/docs/appearance/ai-features).

Browser session, personalization, locale, generation variability and capture
timing remain possible explanations for differences. We did not isolate their
effects, establish a guaranteed answer-length difference for anonymous users,
or show that synchronous versus asynchronous submission causes missing prices.

## Proposed next slice

1. Implement a dedicated Overview transport adapter with embedded and deferred
   routes, immediate per-row token follow-up, bounded timeouts/retries, and
   explicit unavailable/error states. Preserve both search IDs, statuses,
   timings, effective parameters and original responses. If partial content and
   a token coexist, retain both and evaluate the completed answer. An expired
   token may justify one controlled fresh initial search, recorded as an extra
   request; avoid unbounded polling.
2. Evaluate `output=md` for the dedicated endpoint first. It is documented, but
   the Overview probe used JSON, so its Markdown shape and completeness remain
   untested here. Do not infer unsupported Markdown from the absence of a
   `reconstructed_markdown` JSON key, or extend AI Mode's observed format equality
   to Overview without testing. If a derived rendering is needed, label it as
   derived and retain the original structured answer.
   [SerpAPI output formats](https://serpapi.com/google-ai-overview-api).
3. Reuse markup cleanup, URL sanitation and downstream `extract.ai` definitions
   where the evidence format permits. The current Markdown/frontmatter parser
   and Markdown-based URL validator are reusable components, not a completed
   Overview adapter. Keep semantic product/specification/price parsing in
   extraction and keep organic candidates distinguishable from cited evidence.
4. Re-run the same products with the current product-first query and explicit
   identical locale settings before comparing coverage. Add small offline
   fixtures for embedded/deferred success, absent Overview, nested content,
   missing references with usable links, expired tokens, failed follow-up and
   explicit Overview errors despite top-level Success. Evaluate Markdown and
   relevant/unrelated organic candidates separately.

This is a proposed implementation scope, not an implemented output contract or
a promise of better retrieval. The current AI Mode feature can be reviewed and
delivered independently.

## Local evidence retained

The original captures stay in ignored `.data/`; these filenames are local
provenance references, not files included in the repository:

- `Debugging SerpAPI Google AI Mode.md`: supplied conversation export.
- `serpapi_ai_overview_probe_260920_a0508494_findings.md`: original probe report.
- `serpapi_ai_overview_probe_260920_a0508494.json`: input rows, frozen queries,
  initial/follow-up responses and timing evidence; credentials and ephemeral
  token/link fields were redacted.
- `serpapi_ai_overview_probe_260920_a0508494_renold.html` and
  `serpapi_ai_overview_probe_260920_a0508494_renold_html_review.json`: archived
  HTML and its inspection notes.

The original probe report predates the final Markdown design and includes
superseded suggestions about structural normalization and price-list alignment.
Use the proposal above and the [current AI Mode guide](search_ai_mode.md) for the
intended separation of responsibilities. No new live search was needed to
prepare these research notes.
