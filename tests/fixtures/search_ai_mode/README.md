# AI Mode runner, recipe and fixture

This directory contains the runnable AI Mode trial and the synthetic response
used by automated tests. See the [usage guide](../../../docs/search_ai_mode.md)
for the pipeline, outputs and extraction rules.

- `run_search_ai_mode.py` supplies three user-provided product records (INA,
  Renold and Belden) as an input DataFrame. Each record contains `ID`, `Mfr`,
  `MPN`, `Description`, `part_codes` and `query`; only manufacturer, part number
  and description enter the generated query. These examples are product
  identifiers/descriptions, not captured provider results or customer records.
- `search_ai_mode_test.recipe` declares query generation, Markdown retrieval,
  cleanup, extraction and exports. The offline extraction tests use this same
  runner/recipe pair with mocked services.
- `response.md` is the synthetic response described below.

## Run the trial

Select the repository's `.venv` interpreter in VS Code and run
`run_search_ai_mode.py`, or run this command from the repository root:

```powershell
.\.venv\Scripts\python.exe tests/fixtures/search_ai_mode/run_search_ai_mode.py
```

This makes live SerpAPI and extraction requests using the existing
`SERPAPI_API_KEY` and `OPENAI_API_KEY` environment variables. The runner can also
load the repository's ignored `.env` when `python-dotenv` is installed. Keep
credentials outside these files. The editable configuration block holds the
model, row limit, concurrency, locale and replay controls. Searches are synchronous
and are not retried or polled. `THREADS = 5` runs up to five independent searches
concurrently through local workers; it does not enable SerpAPI async mode.
`EXTRACT_THREADS = 1` processes extraction rows one at a time, with
`EXTRACT_RETRIES = 0` for a single extraction attempt.

All generated Markdown, JSON and XLSX files stay under the repository's ignored
`.data/` directory by default. Relative replay/output paths start at the
repository root; launching the runner from another directory does not relocate
these files. Set `REPLAY_FILE` to reuse a saved answer without another search.

## Synthetic response and offline verification

`response.md` is a synthetic, single-response SerpAPI Markdown fixture. It has
YAML frontmatter, four answer sections, a table with two offers from one source,
references (including an irrelevant candidate), inline Google viewer boilerplate,
LaTeX, a literal Unicode escape, and tracking/functional URL parameters. Results
Summary omits the Google viewer URL; structuring captures it from Product
Description for reference `"00"` with source `Google`, while removing description
links and retaining source evidence elsewhere for extraction.
All product/source domains are reserved `.invalid`; Google/SerpAPI URLs are
synthetic and no network requests are made. There are no credentials or user data.

The response is deliberately authored rather than sampled. To regenerate it,
edit this UTF-8 Markdown file directly. Update the three product examples in
the runner's `INPUT_ROWS` list. No raw production payloads, credentials or
generated workbooks belong in this fixture directory.

Run these offline checks from the repository root (services are mocked):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_search-ai_mode.py tests/test_search_ai_extraction.py --basetemp .data/pytest_ai_mode_fixtures -p no:cacheprovider -q
```

Use a fresh `--basetemp` path for each execution. `response.md` replaces the JSON
fixture for the retired deterministic section parser.
Tests exercise Markdown transport and model output validation; supplier and
specification interpretation belongs to `extract.ai`.
