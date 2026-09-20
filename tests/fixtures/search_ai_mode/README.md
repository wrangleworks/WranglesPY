# AI Mode Markdown fixture

`response.md` is a synthetic, single-response SerpAPI Markdown fixture. It has
YAML frontmatter, three answer sections, a table with two offers from one source,
references (including an irrelevant candidate), inline Google viewer boilerplate,
LaTeX, a literal Unicode escape, and tracking/functional URL parameters.
All product/source domains are reserved `.invalid`; Google/SerpAPI URLs are
synthetic and no network requests are made. There are no credentials or user data.

The fixture is deliberately authored rather than sampled. To regenerate it,
edit this UTF-8 Markdown file directly and run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_search-ai_mode.py tests/test_search_ai_extraction.py -q
```

This replaces the JSON fixture for the retired deterministic section parser.
Tests exercise Markdown transport and model output validation; supplier and
specification interpretation belongs to `extract.ai`.
