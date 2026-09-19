# AI Mode response fixture

This is one entirely synthetic SerpAPI-shaped response; it contains no customer
data or credentials. Product names, commercial details, response IDs and example
URLs are invented. It follows the structure inspected in Eric's product-search
sample, without copying the original payload.

The JSON has search_metadata, search_parameters, text_blocks, references and
reconstructed_markdown. Its three requested headings contain a paragraph, a
12-item specification list and a three-item supplier list. All six references,
citation indexes, snippet links, LaTeX, literal Unicode escapes and the viewer
label artifact are intentional test cases.

Tests derive small in-memory variants for omitted headings, explicit paragraph
labels with and without inline content, nested lists and tables, supplier price
qualifiers, colon/dash pricing separators and unattributed pricing notes,
supplier/price/link tables with reference order differing from supplier order
and a supplier whose product-page label has no URL,
specification name/value separators and unlabeled text, missing
reference URLs, Google product-viewer references with direct inline source links,
duplicate source URLs, tracking parameters and nested image fields.
These variants verify the compact, complete and
Markdown outputs without retaining a real provider export.

`tests/test_search_ai_extraction.py` also authors a small synthetic answer in
memory. It covers parallel table representations, an unfamiliar comparison
block, non-positional citation IDs, actual URLs in detailed table cells,
duplicate URLs and source naming, omitted transport metadata, and unmatched
content. Its fixed model responses cover aligned and unlinked offers, unknown
source IDs, skipped/failed rows and mixed-row batches. The real recipe and
`extract.ai` wrapper run with mocked service endpoints and network access
blocked. Temporary XLSX/JSON snapshots verify replay and preservation of values
longer than an Excel cell; no generated workbooks or provider exports are
committed.

This small fixture is authored directly; there is no dataset sampling or
generation step. Run its consumer tests from the repository root:

    python -m pytest -q tests/test_search-ai_mode.py tests/test_search_ai_extraction.py
