from collections import UserDict
from copy import deepcopy

import pandas as pd
import pytest
import yaml

import wrangles
from wrangles.recipe_wrangles import search as recipe_search


@pytest.fixture(autouse=True)
def offline_recipe_context(monkeypatch):
    """Keep local search tests independent of the user's Wrangles credentials."""
    monkeypatch.setattr("wrangles.auth.get_applied_permission_group", lambda: None)

    def unexpected_network(*args, **kwargs):
        pytest.fail("AI Mode output tests must not make network requests")

    monkeypatch.setattr("socket.socket.connect", unexpected_network)


def _classic_response(query: str, query_index: int = 1):
    return {
        "search_metadata": {
            "query_index": query_index,
            "query": query,
            "search_type": "classic",
        },
        "search_results": [
            {
                "google_rank": 1,
                "title": "Classic Result",
                "link": "https://example.com/classic",
                "source": "example.com",
                "snippet": "classic snippet",
                "pricing": {},
                "query_index": query_index,
            }
        ],
    }


def _ai_response(query: str, query_index: int = 1):
    return {
        "search_metadata": {
            "query_index": query_index,
            "query": query,
            "search_type": "ai",
        },
        "product_details": {
            "manufacturer": "WESTFALIA",
            "part_number": "DN65",
        },
        "pricing": {
            "price": 12.5,
            "currency": "USD",
        },
        "misc": {},
        "content_like_results": [
            {
                "title": "Union Nut Listing",
                "link": "https://example.com/union-nut",
                "snippet": "WESTFALIA DN65 UNION NUT",
                "price": 12.5,
                "currency": "USD",
                "position": 1,
            }
        ],
        "raw_response": {"ok": True},
        "validation": {
            "is_valid": True,
            "warnings": [],
            "counts": {
                "product_detail_fields": 2,
                "pricing_fields": 2,
                "content_like_results": 1,
            },
            "has_error": False,
        },
    }


def test_find_links_conflict_google_domain_and_country_raises():
    data = pd.DataFrame({"query": ["abc"], "ID": [1]})
    recipe = """
    wrangles:
      - search.find_links:
          queries: query
          id: ID
          output: results
          google_domain: google.co.uk
          country: uk
    """

    with pytest.raises(ValueError, match="google_domain cannot be combined"):
        wrangles.recipe.run(recipe, dataframe=data)


def test_ai_mode_conflict_google_domain_and_language_raises():
    data = pd.DataFrame({"query": ["abc"], "ID": [1]})
    recipe = """
    wrangles:
      - search.ai_mode:
          queries: query
          id: ID
          output: ai_results
          google_domain: google.com
          language: en
    """

    with pytest.raises(ValueError, match="google_domain cannot be combined"):
        wrangles.recipe.run(recipe, dataframe=data)


def test_ai_mode_recipe_assigns_search_type_and_row_id(monkeypatch):
    def _fake_ai_mode(queries, client, client_config, n_results, threads, **kwargs):
        return [_ai_response(q, i) for i, q in enumerate(queries, start=1)]

    monkeypatch.setattr(recipe_search._search_core, "ai_mode", _fake_ai_mode)

    data = pd.DataFrame(
        {
            "query": [["Find product details and pricing data for this item: WESTFALIA DN65 UNION NUT"]],
            "ID": [42],
        }
    )

    recipe = """
    wrangles:
      - search.ai_mode:
          queries: query
          id: ID
          output: ai_results
          n_results: 3
    """

    df = wrangles.recipe.run(recipe, dataframe=data)
    payload = df.iloc[0]["ai_results"][0]

    assert payload["search_metadata"]["search_type"] == "ai"
    assert payload["content_like_results"][0]["input_row_id"] == 42


def test_ai_mode_dual_output_uses_formatter(monkeypatch):
    def _fake_ai_mode(queries, client, client_config, n_results, threads, **kwargs):
        return [_ai_response(q, i) for i, q in enumerate(queries, start=1)]

    monkeypatch.setattr(recipe_search._search_core, "ai_mode", _fake_ai_mode)

    data = pd.DataFrame({"query": ["PEPPERL+FUCHS KFU8-GUT-EX1.D"], "ID": [7]})
    recipe = """
    wrangles:
      - search.ai_mode:
          queries: query
          id: ID
          output:
            - ai_raw
            - ai_text
    """

    df = wrangles.recipe.run(recipe, dataframe=data)
    assert isinstance(df.iloc[0]["ai_raw"], list)
    assert isinstance(df.iloc[0]["ai_text"], str)
    assert "Query 1 (ai)" in df.iloc[0]["ai_text"]


def test_find_links_formatter_handles_search_type(monkeypatch):
    def _fake_find_links(queries, client, client_config, n_results, threads, **kwargs):
        return [_classic_response(q, i) for i, q in enumerate(queries, start=1)]

    monkeypatch.setattr(recipe_search._search_core, "find_links", _fake_find_links)

    data = pd.DataFrame({"query": ["union nut"], "ID": [9]})
    recipe = """
    wrangles:
      - search.find_links:
          queries: query
          id: ID
          output:
            - raw
            - text
    """

    df = wrangles.recipe.run(recipe, dataframe=data)
    assert "Query 1 (classic)" in df.iloc[0]["text"]


@pytest.fixture
def ai_mode_provider(monkeypatch):
    """Exercise the real client mapper with synthetic SerpAPI-shaped responses."""
    import serpapi

    responses = {}
    calls = []

    def fake_search(client, params):
        calls.append(dict(params))
        query = params["q"]
        response = responses.get(query, {
            "search_metadata": {"status": "Success"},
            "reconstructed_markdown": f"# {query}\n\nAnswer for {query}.",
            "references": [{
                "title": query,
                "link": "https://example.com/product",
                "snippet": "Synthetic source for offline testing.",
            }],
        })
        if isinstance(response, Exception):
            raise response
        return UserDict(deepcopy(response))

    monkeypatch.setenv("SERPAPI_API_KEY", "offline-test-key")
    monkeypatch.setattr(serpapi.Client, "search", fake_search)
    return responses, calls


def _run_ai_mode(data, outputs, queries="query"):
    recipe = {"wrangles": [{"search.ai_mode": {
        "queries": queries,
        "id": "ID",
        "output": outputs,
        "threads": 1,
    }}]}
    return wrangles.recipe.run(yaml.safe_dump(recipe), dataframe=data)


@pytest.mark.parametrize("markdown", [
    "  # Product specifications\n\n[Source](https://example.com/item?q=a&b=c)\n\n"
    "| Part | Size |\n| --- | --- |\n| NATV6\\-PP\\-A | 6 mm |\n\nCafé – Ω\n",
    "# Long answer\n\n" + "x" * 40000,
], ids=["formatting-and-unicode", "beyond-excel-cell-limit"])
def test_ai_mode_third_output_preserves_provider_markdown(ai_mode_provider, markdown):
    responses, calls = ai_mode_provider
    responses["product"] = {
        "search_metadata": {"status": "Success"},
        "text_blocks": [{"type": "paragraph", "snippet": "y" * 40000}],
        "reconstructed_markdown": markdown,
        "references": [{"title": "Product", "link": "https://example.com/product"}],
    }
    df = _run_ai_mode(
        pd.DataFrame({"query": ["product"], "ID": [42]}),
        ["raw", "text", "markdown"],
    )

    assert df.iloc[0]["markdown"] == markdown
    assert df.iloc[0]["raw"][0]["raw_response"]["reconstructed_markdown"] == markdown
    assert len(str(df.iloc[0]["raw"])) > 32767
    assert isinstance(df.iloc[0]["text"], str)
    assert len(calls) == 1
    assert calls[0]["engine"] == "google_ai_mode"


@pytest.mark.parametrize("outputs", [["raw"], ["raw", "text"]])
def test_ai_mode_third_output_preserves_existing_outputs(ai_mode_provider, outputs):
    _, calls = ai_mode_provider
    data = pd.DataFrame({"query": ["product"], "ID": [1]})
    existing = _run_ai_mode(data.copy(), outputs)
    extended = _run_ai_mode(data.copy(), ["raw", "text", "markdown"])

    for column in outputs:
        assert existing[column].tolist() == extended[column].tolist()
    assert extended["markdown"].tolist() == ["# product\n\nAnswer for product."]
    assert len(calls) == 2


def test_ai_mode_markdown_preserves_row_and_query_order_with_failures(ai_mode_provider):
    responses, calls = ai_mode_provider
    responses["failed"] = RuntimeError("Synthetic provider failure")
    responses["missing"] = {"search_metadata": {"status": "Success"}}
    data = pd.DataFrame({
        "query": [["first", "failed", "missing", "last"], None, "last"],
        "ID": [10, 20, 30],
    })
    df = _run_ai_mode(data, ["raw", "text", "markdown"])

    assert df["markdown"].tolist() == [
        "# first\n\nAnswer for first.\n\n# last\n\nAnswer for last.",
        "",
        "# last\n\nAnswer for last.",
    ]
    assert len(df.iloc[0]["raw"]) == 4
    assert df.iloc[0]["raw"][1]["search_metadata"]["error"] == "Synthetic provider failure"
    assert df.iloc[1]["raw"] == []
    assert df.iloc[1]["text"] == ""
    assert df["ID"].tolist() == [10, 20, 30]
    assert [call["q"] for call in calls] == ["first", "failed", "missing", "last", "last"]


@pytest.mark.parametrize("markdown", [None, "", [], {"unexpected": "object"}])
def test_ai_mode_missing_or_nontext_markdown_is_empty(ai_mode_provider, markdown):
    responses, _ = ai_mode_provider
    responses["product"] = {"reconstructed_markdown": markdown}
    df = _run_ai_mode(
        pd.DataFrame({"query": ["product"], "ID": [1]}),
        ["raw", "text", "markdown"],
    )
    assert df["markdown"].tolist() == [""]


@pytest.mark.parametrize("queries", [[], [None, " ", []]])
def test_ai_mode_empty_inputs_create_all_three_outputs(ai_mode_provider, queries):
    _, calls = ai_mode_provider
    df = _run_ai_mode(
        pd.DataFrame({"query": queries, "ID": range(len(queries))}),
        ["raw", "text", "markdown"],
    )

    assert df["raw"].tolist() == [[] for _ in queries]
    assert df["text"].tolist() == ["" for _ in queries]
    assert df["markdown"].tolist() == ["" for _ in queries]
    assert calls == []


def test_ai_mode_three_query_columns_keep_three_structured_outputs(ai_mode_provider):
    data = pd.DataFrame({"q1": ["first"], "q2": ["second"], "q3": ["third"], "ID": [1]})
    df = _run_ai_mode(data, ["out1", "out2", "out3"], queries=["q1", "q2", "q3"])

    for column, query in zip(["out1", "out2", "out3"], ["first", "second", "third"]):
        assert isinstance(df.iloc[0][column], list)
        assert df.iloc[0][column][0]["search_metadata"]["query"] == query


def test_ai_mode_four_outputs_are_rejected(ai_mode_provider):
    _, calls = ai_mode_provider
    with pytest.raises(ValueError, match="2 or 3 output columns"):
        _run_ai_mode(
            pd.DataFrame({"query": ["product"], "ID": [1]}),
            ["raw", "text", "markdown", "extra"],
        )
    assert calls == []


def test_ai_mode_schema_documents_third_output():
    import jsonschema

    schema = yaml.safe_load(recipe_search.ai_mode.__doc__)
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate({
        "queries": "query",
        "id": "ID",
        "output": ["raw", "text", "markdown"],
    }, schema)
    assert "reconstructed_markdown" in schema["properties"]["output"]["description"]


def test_trial_runner_keeps_raw_markdown_and_clean_comparison(monkeypatch):
    import sys
    from types import ModuleType

    import run_search_ai_mode as runner

    markdown = (
        r"[PartGo to product viewer dialog for this item.](https://example.com/?a=1&b=2)"
        "\n\n" + r"$12\text{ VDC}$; healthcare \u0026 ITE"
    )
    monkeypatch.setattr(
        recipe_search._search_core,
        "ai_mode",
        lambda queries, **kwargs: [
            {**_ai_response(query), "raw_response": {"reconstructed_markdown": markdown}}
            for query in queries
        ],
    )
    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: False
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    writes = []
    monkeypatch.setattr(
        "wrangles.connectors.file.write",
        lambda df, **kwargs: writes.append(df.copy()),
    )

    result = runner.main()

    assert len(result) == 2
    for written in writes:
        assert written.equals(result)
    assert result["reconstructed_markdown"].tolist() == [markdown, markdown]
    assert result["reconstructed_markdown_clean"].tolist() == [
        "[Part](https://example.com/?a=1&b=2)\n\n12 VDC; healthcare & ITE"
    ] * 2
    for cell in result["ai_mode_results"]:
        # The trial recipe may optionally explode the list of query responses.
        payloads = cell if isinstance(cell, list) else [cell]
        assert all(item["raw_response"]["reconstructed_markdown"] == markdown for item in payloads)
