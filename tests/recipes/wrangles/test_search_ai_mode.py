import json

import pandas as pd
import pytest
import yaml

import wrangles
from wrangles import format as wrangles_format
from wrangles.clients.serp_api import SerpApiWranglesClient
from wrangles.recipe_wrangles import search as recipe_search


PRODUCT_QUERY = (
    "Manufacturer: SKF\n"
    "Potential part codes: 6205-2RS, 6205 2RS\n"
    "Description: deep groove ball bearing"
)


@pytest.fixture
def ai_mode_response():
    return {
        "search_metadata": {
            "id": "search-123",
            "status": "Success",
            "created_at": "2026-08-20 20:00:00 UTC",
            "total_time_taken": 1.25,
            "json_endpoint": "https://serpapi.com/searches/search-123.json",
            "google_ai_mode_url": "https://www.google.com/search?q=SKF&utm_source=test",
        },
        "search_parameters": {
            "engine": "google_ai_mode",
            "q": PRODUCT_QUERY,
            "hl": "en",
            "gl": "us",
            "location_used": "Austin, Texas",
        },
        "reconstructed_markdown": "SKF identifies **6205-2RS** as a sealed bearing.[1]",
        "text_blocks": [
            {
                "type": "paragraph",
                "snippet": "SKF identifies 6205-2RS as a sealed bearing.",
                "reference_indexes": [0],
            }
        ],
        "references": [
            {
                "title": "SKF 6205-2RS product page",
                "link": "https://www.skf.com/products/6205-2RS?utm_source=google",
                "source": "SKF",
                "snippet": "Official product specifications.",
            }
        ],
        "quick_results": [
            {
                "title": "SKF 6205-2RS product page",
                "link": "https://skf.com/products/6205-2RS",
                "source": "SKF",
                "snippet": "Official product specifications.",
            },
            {
                "title": "6205-2RS datasheet",
                "link": "https://example.com/datasheet",
                "source": "Example",
                "snippet": " Bearing dimensions. | Bearing dimensions. ",
            },
        ],
        "shopping_results": [
            {
                "title": "SKF 6205-2RS bearing",
                "product_link": "https://supplier.example/skf-6205?gclid=tracking",
                "source": "Bearing Supplier",
                "snippet": "Available for immediate dispatch.",
                "extracted_price": 12.5,
                "currency": "USD",
                "availability": "In stock",
            }
        ],
        "inline_products": [
            {
                "title": "SKF 6205 2RS",
                "link": "https://distributor.example/6205",
                "source": {"name": "Distributor", "link": "https://distributor.example"},
                "price": {"value": 14.25, "currency": "USD"},
            }
        ],
    }


class FakeSerpApiClient:
    response = {}
    requests = []

    def __init__(self, api_key):
        self.api_key = api_key

    def search(self, params):
        self.requests.append(params)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_client(response):
    FakeSerpApiClient.response = response
    FakeSerpApiClient.requests = []
    client = SerpApiWranglesClient(api_key="test-key")
    client.client_class = FakeSerpApiClient
    return client


def normalized_payload(query, query_index=1):
    return {
        "search_metadata": {
            "query_index": query_index,
            "query": query,
            "search_type": "ai_mode",
            "search_id": "search-123",
            "status": "Success",
            "search_date": None,
            "response_time": None,
            "json_endpoint": None,
            "google_url": None,
            "language": "en",
            "country": "us",
            "location": None,
        },
        "status": "Success",
        "error": None,
        "search_results": [
            {
                "query_index": query_index,
                "google_rank": 1,
                "result_type": "reference",
                "title": "Source title",
                "link": "example.com/product",
                "source": "Example",
                "snippet": "Supporting source snippet",
                "pricing": {},
            }
        ],
        "extracted_content": {
            "answer_markdown": "A cited answer.",
            "text_blocks": [],
        },
    }


def test_client_maps_documented_ai_mode_response(ai_mode_response):
    client = make_client(ai_mode_response)

    result = client.ai_mode_single(
        PRODUCT_QUERY,
        prompt="Research this exact industrial product.",
        n_results=3,
        query_index=2,
        country="us",
        language="en",
        location="Austin, Texas",
        device="desktop",
        no_cache=True,
    )

    request = FakeSerpApiClient.requests[0]
    assert request["engine"] == "google_ai_mode"
    assert request["output"] == "json"
    assert request["gl"] == "us"
    assert request["hl"] == "en"
    assert request["location"] == "Austin, Texas"
    assert request["device"] == "desktop"
    assert request["no_cache"] is True
    assert "num" not in request
    assert request["q"].startswith("Research this exact industrial product.")
    assert "Find authoritative manufacturer" not in request["q"]
    assert request["q"].endswith(PRODUCT_QUERY)
    assert "6205-2RS, 6205 2RS" in request["q"]

    assert result["status"] == "Success"
    assert result["error"] is None
    assert result["search_metadata"]["query_index"] == 2
    assert result["search_metadata"]["query"] == PRODUCT_QUERY
    assert result["search_metadata"]["search_type"] == "ai_mode"
    assert result["search_metadata"]["google_url"] == "www.google.com/search?q=SKF"
    assert result["extracted_content"] == {
        "answer_markdown": "SKF identifies **6205-2RS** as a sealed bearing.[1]",
        "text_blocks": ai_mode_response["text_blocks"],
    }
    assert len(result["search_results"]) == 3
    assert [item["result_type"] for item in result["search_results"]] == [
        "reference",
        "quick_result",
        "shopping_result",
    ]
    assert [item["google_rank"] for item in result["search_results"]] == [1, 2, 3]
    assert result["search_results"][0]["link"] == "www.skf.com/products/6205-2RS"
    assert result["search_results"][1]["snippet"] == "Bearing dimensions."
    assert result["search_results"][2]["pricing"] == {
        "price": 12.5,
        "currency": "USD",
        "availability": "In stock",
        "vendor": "Bearing Supplier",
    }
    assert "raw_response" not in result
    json.dumps(result)


def test_client_raw_response_and_partial_success(ai_mode_response):
    ai_mode_response["references"] = []
    ai_mode_response["quick_results"] = []
    ai_mode_response["shopping_results"][0].pop("extracted_price")
    ai_mode_response["shopping_results"][0].pop("currency")
    client = make_client(ai_mode_response)

    result = client.ai_mode_single(
        PRODUCT_QUERY,
        n_results=10,
        include_raw_response=True,
    )

    assert result["status"] == "Success"
    assert result["search_results"][0]["pricing"] == {
        "availability": "In stock",
        "vendor": "Bearing Supplier",
    }
    assert result["raw_response"] == ai_mode_response
    assert result["search_results"][1]["result_type"] == "inline_product"
    assert result["search_results"][1]["pricing"] == {
        "price": 14.25,
        "currency": "USD",
        "vendor": "Distributor",
    }
    json.dumps(result)


@pytest.mark.parametrize(
    ("formatted_price", "expected_currency"),
    [
        ("CA$12.50", "CAD"),
        ("A$12.50", "AUD"),
        ("US$12.50", "USD"),
        ("$12.50", None),
    ],
)
def test_client_does_not_guess_ambiguous_price_currency(
    formatted_price,
    expected_currency,
):
    response = {
        "search_metadata": {"status": "Success"},
        "shopping_results": [
            {
                "title": "Industrial product",
                "link": "https://supplier.example/product",
                "source": "Supplier",
                "price": formatted_price,
            }
        ],
    }
    client = make_client(response)

    result = client.ai_mode_single("industrial product")

    pricing = result["search_results"][0]["pricing"]
    assert pricing["price"] == 12.5
    if expected_currency:
        assert pricing["currency"] == expected_currency
    else:
        assert "currency" not in pricing


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ({"search_metadata": {"status": "Error"}, "error": "API limit reached"}, "API limit reached"),
        (RuntimeError("network unavailable"), "network unavailable"),
    ],
)
def test_client_returns_stable_failure_payload(response, message):
    client = make_client(response)

    result = client.ai_mode_single(PRODUCT_QUERY, query_index=1)

    assert result["status"] == "Failure"
    assert result["error"] == message
    assert result["search_results"] == []
    assert result["extracted_content"] == {
        "answer_markdown": None,
        "text_blocks": [],
    }


def test_client_skips_blank_queries_without_provider_call():
    client = make_client({})

    results = client.ai_mode_batch(["", None, float("nan")], threads=2)

    assert FakeSerpApiClient.requests == []
    assert len(results) == 3
    assert all(result["status"] == "Success" for result in results)
    assert all(result["search_results"] == [] for result in results)


def test_client_batch_keeps_partial_failures_in_order(ai_mode_response):
    class PartiallyFailingClient:
        def __init__(self, api_key):
            self.api_key = api_key

        def search(self, params):
            if params["q"].endswith("bad query"):
                raise RuntimeError("request failed")
            return ai_mode_response

    client = make_client(ai_mode_response)
    client.client_class = PartiallyFailingClient

    results = client.ai_mode_batch(
        ["first query", "bad query", "last query"],
        threads=3,
        n_results=1,
    )

    assert [result["search_metadata"]["query"] for result in results] == [
        "first query",
        "bad query",
        "last query",
    ]
    assert [result["status"] for result in results] == [
        "Success",
        "Failure",
        "Success",
    ]
    assert results[1]["error"] == "request failed"


def test_direct_python_api_is_public_and_preserves_order(mocker):
    calls = []

    class FakeClient:
        def ai_mode_batch(self, queries, **kwargs):
            calls.append(kwargs)
            values = queries if isinstance(queries, list) else [queries]
            results = [
                normalized_payload(query, query_index=index)
                for index, query in enumerate(values, start=1)
            ]
            return results if isinstance(queries, list) else results[0]

    factory = mocker.patch("wrangles.search._get_client", return_value=FakeClient())

    scalar = wrangles.search.ai_mode(PRODUCT_QUERY, api_key="key")
    multiple = wrangles.search.ai_mode(["first", "second"], api_key="key")

    assert isinstance(scalar, dict)
    assert scalar["search_metadata"]["query"] == PRODUCT_QUERY
    assert [item["search_metadata"]["query"] for item in multiple] == ["first", "second"]
    assert calls[0]["prompt"].startswith(
        "Find authoritative manufacturer, product, supplier, and distributor pages"
    )
    assert factory.call_args.kwargs == {
        "client_name": "serpapi",
        "config": {"api_key": "key"},
    }
    assert wrangles.search.SerpApiWranglesClient is SerpApiWranglesClient


def test_direct_python_api_returns_empty_without_creating_client(mocker):
    factory = mocker.patch("wrangles.search._get_client")

    scalar = wrangles.search.ai_mode(None)
    multiple = wrangles.search.ai_mode(["", float("nan")])

    factory.assert_not_called()
    assert scalar["search_results"] == []
    assert len(multiple) == 2
    assert all(result["status"] == "Success" for result in multiple)


def test_classic_find_links_public_api_remains_available(mocker):
    class FakeClient:
        def search_batch(self, queries, **kwargs):
            return {"search_metadata": {"query": queries}, "search_results": []}

    mocker.patch("wrangles.search._get_client", return_value=FakeClient())

    result = wrangles.search.find_links(
        "classic search",
        client_config={"api_key": "key"},
        n_results=3,
    )

    assert result == {
        "search_metadata": {"query": "classic search"},
        "search_results": [],
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_results": 0}, "n_results must be at least 1"),
        ({"threads": 0}, "threads must be at least 1"),
        ({"device": "watch"}, "device must be one of"),
        ({"location": "Austin", "uule": "encoded"}, "location and uule"),
    ],
)
def test_direct_python_api_validates_parameters(kwargs, message):
    with pytest.raises(ValueError, match=message):
        wrangles.search.ai_mode(PRODUCT_QUERY, api_key="key", **kwargs)


def test_recipe_ai_mode_preserves_rows_queries_ids_and_readable_output(mocker):
    calls = []

    def fake_ai_mode(queries, **kwargs):
        calls.append((queries, kwargs))
        return [
            normalized_payload(query, query_index=index)
            for index, query in enumerate(queries, start=1)
        ]

    mocker.patch.object(recipe_search._search_core, "ai_mode", side_effect=fake_ai_mode)
    data = pd.DataFrame(
        {
            "query": [
                "Manufacturer: WESTFALIA\nPotential part code: DN65\nDescription: union nut",
                ["general topic one", "general topic two"],
                None,
                float("nan"),
            ],
            "ID": ["westfalia", "general", "blank", "nan"],
        }
    )
    recipe = """
    wrangles:
      - search.ai_mode:
          queries: query
          id: ID
          output:
            - AI Mode Results
            - AI Mode Text
          prompt: Find primary sources for this topic.
          n_results: 4
          country: gb
          language: en
          device: mobile
          no_cache: true
    """

    result = wrangles.recipe.run(recipe, dataframe=data)

    assert calls[0][0] == [
        "Manufacturer: WESTFALIA\nPotential part code: DN65\nDescription: union nut",
        "general topic one",
        "general topic two",
    ]
    assert calls[0][1]["prompt"] == "Find primary sources for this topic."
    assert calls[0][1]["country"] == "gb"
    assert calls[0][1]["device"] == "mobile"
    assert result.loc[0, "AI Mode Results"][0]["search_results"][0]["input_row_id"] == "westfalia"
    assert [
        payload["search_metadata"]["query_index"]
        for payload in result.loc[1, "AI Mode Results"]
    ] == [1, 2]
    assert result.loc[2, "AI Mode Results"] == []
    assert result.loc[3, "AI Mode Results"] == []
    assert result.loc[2, "AI Mode Text"] == ""
    assert "Query 1" in result.loc[0, "AI Mode Text"]
    assert "A cited answer." in result.loc[0, "AI Mode Text"]


def test_recipe_ai_mode_supports_multiple_query_columns(mocker):
    mocker.patch.object(
        recipe_search._search_core,
        "ai_mode",
        side_effect=lambda queries, **kwargs: [
            normalized_payload(query, index)
            for index, query in enumerate(queries, start=1)
        ],
    )
    data = pd.DataFrame(
        {
            "product_query": [PRODUCT_QUERY],
            "general_query": ["History of ball bearings"],
            "ID": [7],
        }
    )

    result = recipe_search.ai_mode(
        data,
        queries=["product_query", "general_query"],
        id="ID",
        output=["product_results", "general_results"],
        api_key="key",
    )

    assert result["product_results"][0][0]["search_metadata"]["query"] == PRODUCT_QUERY
    assert result["general_results"][0][0]["search_metadata"]["query"] == "History of ball bearings"


def test_ai_mode_formatter_and_classic_formatter_contract():
    payload = normalized_payload(PRODUCT_QUERY)
    payload["search_results"][0]["pricing"] = {
        "price": 12.5,
        "currency": "USD",
        "availability": "In stock",
        "vendor": "Example",
    }

    text = wrangles_format.ai_mode_results_to_text([payload])
    classic_text = wrangles_format.raw_search_results_to_text([payload])

    assert f"Query 1: {PRODUCT_QUERY}" in text
    assert "Status: Success" in text
    assert "A cited answer." in text
    assert "Source 1" in text
    assert "USD 12.5" in text
    assert "##   Query 1:" in classic_text
    assert "Status: Success" not in classic_text

    failure = normalized_payload("failed query")
    failure.update(status="Failure", error="API limit reached", search_results=[])
    failure_text = wrangles_format.ai_mode_results_to_text([failure])
    assert "Status: Failure" in failure_text
    assert "Error: API limit reached" in failure_text


def test_ai_mode_recipe_schema_documents_supported_parameters_only():
    schema = yaml.safe_load(recipe_search.ai_mode.__doc__)

    assert schema["additionalProperties"] is False
    assert schema["required"] == ["queries", "id", "output"]
    assert set(schema["properties"]) == {
        "queries",
        "id",
        "output",
        "client",
        "api_key",
        "prompt",
        "n_results",
        "threads",
        "country",
        "language",
        "location",
        "uule",
        "device",
        "no_cache",
        "include_raw_response",
    }
    assert schema["properties"]["device"]["enum"] == ["desktop", "tablet", "mobile"]
