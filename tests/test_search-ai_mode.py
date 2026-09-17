"""Offline contract tests from provider responses through the recipe runner."""

from collections import UserDict
from collections.abc import Mapping
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import ModuleType

import jsonschema
import pandas as pd
import pytest
import yaml

import wrangles
from wrangles.recipe_wrangles import search as recipe_search


QUERY_CONFIG = [
    {"base_query": "Provide the following product information:"},
    {"Product Description": "1-3 sentences including the name and key features."},
    {"Technical Specifications": "List confirmed specifications."},
    {"Sources & Pricing": "List suppliers, prices and source links."},
    {"query_suffix": "Use these exact headings; no additional sections or questions."},
]
HEADINGS = ["Product Description", "Technical Specifications", "Sources & Pricing"]


@pytest.fixture(autouse=True)
def offline_recipe_context(monkeypatch):
    monkeypatch.setattr("wrangles.auth.get_applied_permission_group", lambda: None)

    def unexpected_network(*args, **kwargs):
        pytest.fail("Search contract tests must not make network requests")

    monkeypatch.setattr("socket.socket.connect", unexpected_network)


@pytest.fixture
def provider_response():
    fixture = Path(__file__).parent / "fixtures/search_ai_mode/response.json"
    return json.loads(fixture.read_text(encoding="utf-8"))


@pytest.fixture
def ai_mode_provider(monkeypatch, provider_response):
    """Use the SDK's Mapping shape, not an artificially pre-normalized result."""
    import serpapi

    responses, calls = {}, []

    def fake_search(client, params):
        calls.append(dict(params))
        response = responses.get(params["q"], provider_response)
        if isinstance(response, Exception):
            raise response
        return UserDict(deepcopy(response)) if isinstance(response, Mapping) else response

    monkeypatch.setenv("SERPAPI_API_KEY", "offline-test-key")
    monkeypatch.setattr(serpapi.Client, "search", fake_search)
    return responses, calls


def run_ai_mode(data=None, output=None, **options):
    if data is None:
        data = pd.DataFrame({"query": ["product"], "ID": [42]})
    args = {
        "queries": "query", "id": "ID", "query_config": QUERY_CONFIG,
        "output": ["result", "markdown"] if output is None else output,
        "threads": 1, **options,
    }
    return wrangles.recipe.run({"wrangles": [{"search.ai_mode": args}]}, dataframe=data)


def test_sections_references_and_markdown_preserve_provider_content(ai_mode_provider, provider_response):
    df = run_ai_mode()
    result = df.iloc[0]["result"]
    assert list(result) == HEADINGS + ["references", "meta_data"]
    for index, heading in enumerate(HEADINGS):
        assert result[heading] == [provider_response["text_blocks"][index * 2 + 1]]
    assert len(result["Technical Specifications"][0]["list"]) == 12
    assert len(result["Sources & Pricing"][0]["list"]) == 3
    assert result["references"] == provider_response["references"]
    assert [ref["index"] for ref in result["references"]] == list(range(6))
    assert df.iloc[0]["markdown"] == provider_response["reconstructed_markdown"]
    meta = result["meta_data"]
    assert meta["input_row_id"] == 42
    assert meta["query"] == "product"
    assert meta["query_index"] == 1
    assert meta["search_id"] == "synthetic-ai-mode"
    assert meta["google_ai_mode_url"] == provider_response["search_metadata"]["google_ai_mode_url"]
    assert meta["status"] == "Success"
    assert meta["parse_status"] == "complete"
    assert meta["warnings"] == []


def test_public_search_namespace_and_ordered_batch(ai_mode_provider):
    assert wrangles.search.__name__ == "wrangles.search"
    assert recipe_search._search_core is wrangles.search
    scalar = wrangles.search.ai_mode(" first ", QUERY_CONFIG)
    assert scalar["ai_mode_result"]["meta_data"]["query"] == "first"
    results = wrangles.search.ai_mode(["first", "second"], QUERY_CONFIG, threads=2)
    assert [r["ai_mode_result"]["meta_data"]["query"] for r in results] == ["first", "second"]
    assert [r["ai_mode_result"]["meta_data"]["query_index"] for r in results] == [1, 2]
    assert results[0] == scalar


@pytest.mark.parametrize("output", ["result", ["result"]])
def test_single_output_is_a_dictionary(ai_mode_provider, output):
    df = run_ai_mode(output=output)
    assert isinstance(df.iloc[0]["result"], dict)
    assert "markdown" not in df.columns


@pytest.mark.parametrize("output", [[], ["a", "b", "c"], ["a", "a"], ["a", 1], ""])
def test_invalid_outputs_fail_before_search(ai_mode_provider, output):
    with pytest.raises(ValueError, match="1 or 2 distinct output columns"):
        run_ai_mode(output=output)
    assert ai_mode_provider[1] == []


@pytest.mark.parametrize("value", [["one", "two"], ("one", "two"), {"q": "one"}, 123])
def test_query_cells_require_one_string(ai_mode_provider, value):
    data = pd.DataFrame({"query": ["valid", value], "ID": [1, 2]})
    with pytest.raises(TypeError, match="one query string per row"):
        run_ai_mode(data)
    assert ai_mode_provider[1] == []


def test_multiple_query_columns_rejected(ai_mode_provider):
    with pytest.raises(ValueError, match="one query column"):
        run_ai_mode(queries=["query"])
    assert ai_mode_provider[1] == []


@pytest.mark.parametrize("config", [
    None, {}, [], ["Description"], [{"a": "one", "b": "two"}],
    [{"": "empty"}], [{"a\nb": "multiline"}], [{1: "numeric key"}], [{"a": 1}],
    [{"Description": "a"}, {" description ": "b"}],
    [{"Technical  Specifications": "a"}, {"technical specifications": "b"}],
    [{"References": "sources"}], [{"meta_data": "data"}], [{"raw_response": "raw"}],
    [{"base_query": "only prompt"}, {"query_suffix": "only suffix"}],
    [{"Base_Query": "prefix"}, {"Description": "a"}],
])
def test_invalid_configuration_fails_before_search(ai_mode_provider, config):
    with pytest.raises(ValueError):
        run_ai_mode(query_config=config)
    assert ai_mode_provider[1] == []


def test_heading_matching_missing_repeated_and_unmatched_content(ai_mode_provider, provider_response):
    responses, _ = ai_mode_provider
    blocks = [
        {"type": "paragraph", "snippet": "Preamble"},
        {"type": "heading", "snippet": " product   DESCRIPTION "},
        {"type": "paragraph", "snippet": "First description"},
        {"type": "heading", "snippet": "Unrequested Section"},
        {"type": "paragraph", "snippet": "Unexpected content"},
        {"type": "heading", "snippet": "Product Description"},
        {"type": "paragraph", "snippet": "Second description"},
        {"type": "heading", "snippet": "Sources & Pricing"},
    ]
    responses["product"] = {**provider_response, "text_blocks": blocks}
    result = run_ai_mode().iloc[0]["result"]
    assert result["Product Description"] == [blocks[2], blocks[6]]
    assert result["Technical Specifications"] == []
    assert result["Sources & Pricing"] == []
    meta = result["meta_data"]
    assert meta["missing_headings"] == ["Technical Specifications"]
    assert meta["repeated_headings"] == ["Product Description"]
    assert meta["unsectioned_text_blocks"] == [blocks[0]]
    assert meta["unmatched_sections"] == [{"heading": blocks[3], "text_blocks": [blocks[4]]}]
    assert "empty_heading: Sources & Pricing" in meta["warnings"]
    assert meta["parse_status"] == "partial"


def test_nested_lists_tables_and_unknown_blocks_are_preserved(ai_mode_provider, provider_response):
    blocks = [
        {"type": "heading", "snippet": "Details"},
        {"type": "table", "table": [[{"snippet": "Voltage", "reference_indexes": [5]}, "12 V"]]},
        {"type": "list", "list": [{"snippet": "Main", "text_blocks": [
            {"type": "heading", "snippet": "Nested heading"},
            {"type": "list", "list": [{"snippet": "Nested", "reference_indexes": [0]}]},
        ]}]},
        {"type": "future_block", "data": {"answer": [1, 2, 3]}},
    ]
    ai_mode_provider[0]["product"] = {**provider_response, "text_blocks": blocks}
    result = run_ai_mode(query_config=[{"Details": "All details"}]).iloc[0]["result"]
    assert result["Details"] == blocks[1:]
    assert result["meta_data"]["parse_status"] == "complete"


def test_reference_ids_are_not_positions_or_deduplicated(ai_mode_provider, provider_response):
    refs = [{"index": 7, "link": "https://example.invalid/same"},
            {"index": 1, "link": "https://example.invalid/same"}]
    blocks = [{"type": "heading", "snippet": "Details"},
              {"type": "paragraph", "snippet": "Cited", "reference_indexes": [1, 7, 99]}]
    ai_mode_provider[0]["product"] = {**provider_response, "references": refs, "text_blocks": blocks}
    result = run_ai_mode(query_config=[{"Details": "Details"}]).iloc[0]["result"]
    assert result["references"] == refs
    assert result["Details"][0]["reference_indexes"] == [1, 7, 99]
    assert result["meta_data"]["warnings"] == ["unresolved_reference_index: 99"]


def test_blank_queries_and_empty_dataframe_need_no_credentials(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    data = pd.DataFrame({"query": [None, "", " \t", float("nan"), pd.NA, pd.NaT], "ID": range(6)})
    df = run_ai_mode(data)
    assert df["markdown"].tolist() == [""] * 6
    for index, result in enumerate(df["result"]):
        assert all(result[heading] == [] for heading in HEADINGS)
        assert result["references"] == []
        assert result["meta_data"]["input_row_id"] == index
        assert result["meta_data"]["status"] == "Skipped"
        assert result["meta_data"]["parse_status"] == "skipped"
        assert result["meta_data"]["warnings"] == []
    empty = run_ai_mode(pd.DataFrame(columns=["query", "ID"]))
    assert empty.empty and list(empty.columns) == ["query", "ID", "result", "markdown"]
    assert wrangles.search.ai_mode([], QUERY_CONFIG) == []


def test_row_order_and_ids_survive_provider_errors_and_skips(ai_mode_provider):
    ai_mode_provider[0]["failed"] = RuntimeError("Synthetic error; key=offline-test-key")
    data = pd.DataFrame({"query": ["first", "failed", None, "last"], "ID": [10, 20, 30, 40]},
                        index=[8, 3, 7, 1])
    df = run_ai_mode(data, threads=3)
    metas = [result["meta_data"] for result in df["result"]]
    assert df.index.tolist() == [8, 3, 7, 1]
    assert [m["input_row_id"] for m in metas] == [10, 20, 30, 40]
    assert [m["query"] for m in metas] == ["first", "failed", "", "last"]
    assert [m["query_index"] for m in metas] == [1, 2, 3, 4]
    assert [m["parse_status"] for m in metas] == ["complete", "error", "skipped", "complete"]
    assert metas[1]["error"] == "Synthetic error; key=[redacted]"
    assert df["markdown"].iloc[1:3].tolist() == ["", ""]
    assert sorted(call["q"] for call in ai_mode_provider[1]) == ["failed", "first", "last"]


@pytest.mark.parametrize("response, status", [
    ({"error": "No results", "search_metadata": {"status": "Error"}}, "error"),
    ({"search_metadata": {"status": "Processing"}}, "partial"),
    ({"search_metadata": {"status": "Error"}}, "error"),
    (["not an object"], "error"),
])
def test_provider_failure_shapes_are_reported_per_row(ai_mode_provider, response, status):
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["result"]["meta_data"]["parse_status"] == status
    assert row["markdown"] == ""


@pytest.mark.parametrize("markdown", [
    "  # Answer\n\n[Source](https://example.invalid/?q=a&b=c)\nCafé – Ω\n",
    "# Long answer\n\n" + "x" * 40000,
], ids=["formatting-and-unicode", "long-answer"])
def test_markdown_is_never_cleaned_or_truncated_by_search(ai_mode_provider, provider_response, markdown):
    ai_mode_provider[0]["product"] = {**provider_response, "reconstructed_markdown": markdown}
    assert run_ai_mode().iloc[0]["markdown"] == markdown


@pytest.mark.parametrize("markdown", [None, "", [], {"unexpected": "object"}])
def test_missing_or_nontext_markdown_is_empty_and_diagnosed(ai_mode_provider, provider_response, markdown):
    ai_mode_provider[0]["product"] = {**provider_response, "reconstructed_markdown": markdown}
    row = run_ai_mode().iloc[0]
    assert row["markdown"] == ""
    assert "missing_reconstructed_markdown" in row["result"]["meta_data"]["warnings"]


def test_malformed_fields_are_retained_for_diagnostics(ai_mode_provider, provider_response):
    ai_mode_provider[0]["product"] = {**provider_response, "text_blocks": {"bad": "shape"},
                                    "references": [None, provider_response["references"][5]]}
    result = run_ai_mode().iloc[0]["result"]
    assert result["references"] == [provider_response["references"][5]]
    assert result["meta_data"]["invalid_fields"] == {"text_blocks": {"bad": "shape"}, "references[0]": None}
    assert result["meta_data"]["parse_status"] == "partial"


def test_raw_response_is_opt_in_and_mutations_are_isolated(ai_mode_provider, provider_response):
    provider_response["shopping_results"] = [{"title": "Additional product"}]
    normal = run_ai_mode().iloc[0]["result"]
    assert "raw_response" not in normal
    assert normal["meta_data"]["unmapped_fields"] == ["shopping_results"]
    data = pd.DataFrame({"query": ["product", "product"], "ID": [1, 2]})
    df = run_ai_mode(data, include_raw_response=True)
    first, second = df["result"]
    assert first["raw_response"] == provider_response
    first["Product Description"][0]["snippet"] = "changed"
    first["references"][0]["title"] = "changed"
    assert second["Product Description"][0] == provider_response["text_blocks"][1]
    assert second["references"] == provider_response["references"]
    assert first["raw_response"] == provider_response


def test_request_controls_and_locale_aliases(ai_mode_provider):
    run_ai_mode(country="ca", language="fr", location="Toronto, Canada", device="mobile",
                include_raw_response=True)
    assert ai_mode_provider[1] == [{"engine": "google_ai_mode", "q": "product", "output": "json",
                                    "gl": "ca", "hl": "fr", "location": "Toronto, Canada", "device": "mobile"}]


@pytest.mark.parametrize("options, message", [
    ({"n_results": 3}, "does not support n_results"),
    ({"num": 3}, "does not support num"),
    ({"google_domain": "google.com"}, "does not support google_domain"),
    ({"country": "us", "gl": "ca"}, "Conflicting country"),
    ({"language": "en", "hl": "fr"}, "Conflicting language"),
    ({"threads": 0}, "positive integer"),
    ({"threads": True}, "positive integer"),
])
def test_unsupported_or_conflicting_options_fail_before_search(ai_mode_provider, options, message):
    with pytest.raises(ValueError, match=message):
        run_ai_mode(**options)
    assert ai_mode_provider[1] == []


def test_runner_uses_shared_configuration_and_separate_cleanup(monkeypatch, ai_mode_provider, provider_response):
    import run_search_ai_mode as runner

    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    # Intercept Eric's optional local Excel export without writing to his workbook.
    def no_file_write(df, name, **kwargs):
        return None
    monkeypatch.setattr("wrangles.connectors.file.write", no_file_write)
    config = deepcopy(runner.AI_MODE_QUERY)
    config[2] = {"Specification Details": 'Keep literal {{ sample }} and "quoted" instructions.'}
    monkeypatch.setattr(runner, "AI_MODE_QUERY", config)
    monkeypatch.setattr(runner, "NROWS", 1)
    provider_response["text_blocks"][2]["snippet"] = "Specification Details"
    df = runner.main()
    assert len(df) == 1
    assert "__ai_mode_query_config" not in df.columns
    query = ai_mode_provider[1][0]["q"]
    assert query.startswith(config[0]["base_query"])
    assert 'Specification Details: Keep literal {{ sample }} and "quoted" instructions.' in query
    assert "Product Description:" in query and "Sources & Pricing:" in query
    assert "References:" not in query
    assert "Mfr: INA" in query and "MPN: NATV6-PP-A" in query
    assert query.endswith(config[-1]["query_suffix"])
    result = df.iloc[0]["ai_mode_result"]
    assert result["Specification Details"] == [provider_response["text_blocks"][3]]
    assert result["meta_data"]["parse_status"] == "complete"
    assert df.iloc[0]["ai_mode_markdown"] == provider_response["reconstructed_markdown"]
    clean = df.iloc[0]["ai_mode_markdown_clean"]
    assert "Go to product viewer dialog" not in clean
    assert "[Example Power P12](https://example.invalid/product?part=P12&variant=1)" in clean
    assert "12 VDC" in clean and "Healthcare & ITE" in clean
    assert "\\text" in result["Product Description"][0]["snippet"]


def test_ai_mode_schema_matches_two_output_contract():
    schema = yaml.safe_load(recipe_search.ai_mode.__doc__)
    jsonschema.Draft7Validator.check_schema(schema)
    valid = {"queries": "query", "id": "ID", "query_config": QUERY_CONFIG,
             "output": ["result", "markdown"], "include_raw_response": True}
    jsonschema.validate(valid, schema)
    for change in ({"output": ["a", "b", "c"]}, {"query_config": [{"a": "x", "b": "y"}]},
                   {"n_results": 5}, {"queries": ["query"]}, {"threads": 0}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**valid, **change}, schema)


def test_classic_find_links_retains_results_pricing_and_formatter(ai_mode_provider):
    ai_mode_provider[0]["classic"] = {
        "search_metadata": {"status": "Success"},
        "organic_results": [
            {"title": "Part", "link": "https://example.invalid/part", "position": 1,
             "snippet": "Available for $21.00"},
            {"title": "More", "link": "https://example.invalid/more", "position": 2},
        ],
    }
    recipe = {"wrangles": [{"search.find_links": {
        "queries": "query", "id": "ID", "output": ["result", "text"], "n_results": 1,
    }}]}
    data = pd.DataFrame({"query": [["classic", "classic"], None], "ID": [9, 10]})
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df.iloc[0]["result"]) == 2
    for index, response in enumerate(df.iloc[0]["result"], 1):
        assert response["search_metadata"]["query_index"] == index
        assert len(response["search_results"]) == 1
        assert response["search_results"][0]["input_row_id"] == 9
        assert response["search_results"][0]["pricing"]["price"] == 21
    assert "Query 1 (classic)" in df.iloc[0]["text"]
    assert df.iloc[1]["result"] == [] and df.iloc[1]["text"] == ""
    assert all(call["num"] == 1 for call in ai_mode_provider[1])


def test_find_links_locale_conflict_is_unchanged():
    data = pd.DataFrame({"query": ["classic"], "ID": [1]})
    with pytest.raises(ValueError, match="google_domain cannot be combined"):
        wrangles.recipe.run({"wrangles": [{"search.find_links": {
            "queries": "query", "id": "ID", "output": "result",
            "google_domain": "google.co.uk", "country": "uk",
        }}]}, dataframe=data)
