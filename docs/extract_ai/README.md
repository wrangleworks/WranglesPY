# `extract.ai` runtime operation

This document explains how an `extract.ai` workload moves from WranglesXL or
Python through a recipe and into OpenAI. It focuses on row batching,
concurrency, time limits, retries, and the two cache layers.

For schema compilation, nullable fields, examples, and configuration-file
details, see [`../extract_ai_configuration.md`](../extract_ai_configuration.md).

## Runtime layers

The word **batch** can refer to several different boundaries. They should not
be treated as one setting.

| Layer | Unit of work | Controlled by | Purpose |
| --- | --- | --- | --- |
| WranglesXL request batch | A selected number of worksheet rows | WranglesXL Recipe editor | Bounds the rows sent to one Lambda request so the complete round trip can fit within the approximately 20-second XL window |
| Recipe DataFrame | The rows received by one `recipe.run` call | Caller and recipe | Runs the recipe's read, wrangle, and write steps |
| `extract.ai` execution batch | All rows passed to one `extract.ai` call | WranglesPY | Deduplicates identical effective requests, checks the local cache, and schedules row requests |
| OpenAI request | One unique, uncached input row | WranglesPY thread pool | Performs one Responses API call, with any retry occurring inside the same row task |

This implementation does **not** use the OpenAI Batch API, and `extract.ai`
does not combine multiple input rows into one Responses API request. Each
unique, uncached row is a separate synchronous OpenAI request.

## End-to-end XL flow

For an XL recipe using a batch size of 10:

1. WranglesXL sends up to 10 rows to the AWS Lambda endpoint.
2. Lambda passes those rows to WranglesPY as one DataFrame and runs the recipe.
3. Recipe wrangles execute in recipe order. Non-AI work consumes part of the
   same approximately 20-second XL round trip.
4. When the recipe reaches `extract.ai`, the wrangle passes all applicable
   DataFrame rows to the lower-level `wrangles.extract.ai` function.
5. WranglesPY groups duplicate effective requests, checks its warm-process
   result cache, and submits cache misses to a thread pool.
6. Each worker sends one row to OpenAI. It may make one additional attempt
   after a retryable failure when the default retry is used.
7. Results are restored to the original row order and merged into the
   DataFrame.
8. Remaining recipe wrangles and writes run before Lambda serializes the
   response and returns it to XL.

The XL batch size therefore controls the maximum rows entering one Lambda
invocation. It does not create an additional OpenAI request batch and does not
replace the `threads`, `timeout`, or `retries` settings.

## Current defaults

The packaged defaults are defined in
[`../../wrangles/ai_defaults.yml`](../../wrangles/ai_defaults.yml):

| Setting | Default | Scope |
| --- | ---: | --- |
| `threads` / `default_concurrency` | 32 | Worker concurrency for one `extract.ai` call when `threads` is omitted |
| `timeout` / `request_timeout_seconds` | 12 seconds | Network timeout for each HTTP attempt |
| `retries` | 1 | One additional attempt per row after a retryable failure |
| Local result-cache TTL | 3,600 seconds | Lifetime within one warm Python/Lambda process |

Recipes and direct Python calls can override the first three settings for one
call. A deployment can replace the complete packaged AI configuration by
setting `WRANGLES_AI_CONFIG`.

## Threads and row concurrency

`threads` is the maximum size of the I/O thread pool used by one
`extract.ai` call. It is not the number of rows included in an OpenAI request.
When omitted, it uses `extract_ai.default_concurrency` from the configuration,
which defaults to 32. Set `threads` higher or lower to override that default
for an individual call.

With caching enabled, WranglesPY first groups rows by their complete effective
request identity. The worker count is:

```text
min(threads, number of unique effective requests)
```

The first unique row completes before the remaining rows are submitted. This
validates the shared model setting: a `model_not_found` response fails the
wrangle immediately instead of returning and logging the same error per row.

Examples with the default `threads: 32`:

| XL rows reaching `extract.ai` | Unique effective requests | Maximum active row tasks |
| ---: | ---: | ---: |
| 10 | 10 | 10 |
| 20 | 20 | 20 |
| 50 | 50 | 32, followed by another wave |
| 50 | 8 | 8 |

Increasing `threads` above the number of unique rows has no benefit. Increasing
it can reduce elapsed time for I/O-bound requests, but it also increases
instantaneous request and token pressure against provider rate limits.

Concurrency is per Python process and per `extract.ai` call. If WranglesXL has
several Lambda requests active at once, a useful upper-bound estimate is:

```text
active Lambda invocations × min(threads, unique rows per invocation)
```

Actual OpenAI calls may be lower because of local result-cache hits and
duplicate suppression. Separate Lambda instances do not share the local
in-memory cache.

## Request timeout

`timeout` applies to each HTTP attempt and defaults to 12 seconds. Each retry
uses the same configured timeout. Queued rows and retry delays do not consume
it.

The timeout measures network connection and read waits; it is not a strict
limit on the total elapsed time of an HTTP request. A request timeout normally
produces a row-level error result after the available attempts are exhausted.

## Retry behavior

`retries: 1` means at most two HTTP attempts for a row:

```text
initial attempt + one retry
```

Retryable HTTP responses are 408, 409, 429, 500, 502, 503, and 504. Transport
timeouts, connection failures, and invalid structured responses can also use
the remaining attempt. Invalid schemas and invalid API keys fail immediately.

Retry delay honors `Retry-After` when OpenAI supplies it; otherwise it uses
bounded exponential backoff with jitter. Each delay is capped at 60 seconds
and is separate from the next attempt's timeout.

## Long-running Python and GitHub jobs

An `extract.ai` call processes all queued rows with the configured concurrency,
timeout, and retry count. Total batch time includes successive waves of row
requests and their retry delays, so it can be much longer than the timeout of
one attempt.

For long-running jobs, choose `timeout` for the expected response time of one
row and `retries` for the additional attempts allowed after a retryable
failure. Set `threads` according to the provider's request and token limits.
Any time limit imposed by the calling job or application still applies.

## Choosing the XL row batch size

The safe XL batch size depends primarily on:

- the slowest OpenAI row request, not merely the average;
- the number of concurrency waves;
- provider request and token rate limits;
- retry frequency;
- cache-hit and duplicate rates; and
- time spent in other recipe steps and response serialization.

With `threads: 32`, 20 unique rows can begin together. Fifty unique rows
require at least two scheduling waves. This does not mean that 50 rows are
unsafe, but all waves and the rest of the recipe must fit within the
approximately 20-second XL round trip.

A conservative rollout is:

1. Keep XL batches at 5-10 while measuring real request durations and rate
   limits.
2. Test 20 rows with representative long inputs and a cold local cache.
3. Increase toward 50 only if the second wave reliably finishes with enough
   time for the rest of the recipe and Lambda response.
4. Reduce `threads` when aggregate concurrency across simultaneous Lambda
   invocations causes 429 responses; increasing threads cannot solve a
   provider rate limit.

Cache-warm tests are useful for capacity planning but should not be the only
acceptance test.

## Local result caching and duplicate suppression

The WranglesPY result cache stores successful row results in the current warm
process. Its request identity includes the provider, protocol, credential
hash, endpoint, model, instructions, examples, schema, model options, and
exact row input.

With the cache enabled:

- identical rows within one `extract.ai` call are computed once and copied
  back to every matching row;
- concurrent identical calls in the same process are coalesced by
  single-flight handling;
- later calls in the same warm process can reuse an unexpired result; and
- failed, invalid, timed-out, and oversized results are not cached.

The cache preserves input row order after deduplication. Disable it for one
call with `cache: false` in YAML or `cache=False` in Python.

## OpenAI prompt caching

OpenAI prompt caching is separate from the WranglesPY result cache.

WranglesPY keeps the instructions, examples, and structured-output definition
stable and places row data at the dynamic end of the request. It also sends a
stable `prompt_cache_key` based on the complete static request prefix.

An OpenAI prompt-cache hit can reduce the work associated with repeated input
tokens. It does not skip the OpenAI request and does not reuse a previous
extracted result. The local WranglesPY result cache is the layer that can avoid
the provider call entirely.

## Worked example

Suppose an XL request contains 20 rows:

- 4 rows are exact duplicates of other effective requests;
- 6 unique requests are already in the warm-process result cache; and
- `threads` remains 32.

WranglesPY groups the 20 output positions into 16 unique request identities.
Six are served locally, leaving 10 OpenAI calls. Those calls can run
concurrently because 10 is below the thread limit. WranglesPY then copies
results into all duplicate positions and restores the original 20-row order.

If the same request lands on another Lambda instance, its local cache starts
independently. OpenAI prompt caching may still help with the stable prefix, but
it does not eliminate those row requests.

## YAML and Python overrides

Recipe:

```yaml
wrangles:
  - extract.ai:
      input: Description
      api_key: ${OPENAI_API_KEY}
      threads: 20
      timeout: 12
      retries: 1
      output:
        Product Type:
          type: string
```

Direct Python:

```python
result = wrangles.extract.ai(
    rows,
    api_key=api_key,
    output=output_schema,
    threads=20,
    timeout=30,
    retries=1,
)
```

The Python example allows a longer timeout for each attempt. The configured
defaults otherwise apply equally to XL, recipes run locally or in GitHub,
saved models, and direct Python calls.
