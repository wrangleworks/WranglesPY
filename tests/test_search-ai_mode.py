import pandas as pd
import pytest

import wrangles


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

    monkeypatch.setattr(wrangles.search, "ai_mode", _fake_ai_mode)

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

    monkeypatch.setattr(wrangles.search, "ai_mode", _fake_ai_mode)

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

    monkeypatch.setattr(wrangles.search, "find_links", _fake_find_links)

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
