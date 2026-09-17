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

This small fixture is authored directly; there is no dataset sampling or
generation step. Run its consumer tests from the repository root:

    python -m pytest -q tests/test_search-ai_mode.py
