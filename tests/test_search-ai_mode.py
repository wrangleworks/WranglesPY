"""Offline Markdown transport, schema, and classic-search regression tests."""

import json
from pathlib import Path

import jsonschema
import pandas as pd
import pytest
import requests
import yaml

import wrangles
from wrangles import _ai_mode
from wrangles.recipe_wrangles import search as recipe_search
from wrangles._search_ai_content import split_markdown


@pytest.fixture(autouse=True)
def offline_recipe_context(monkeypatch):
    monkeypatch.setattr("wrangles.auth.get_applied_permission_group", lambda: None)

    def unexpected_network(*args, **kwargs):
        pytest.fail("Search contract tests must not make network requests")

    monkeypatch.setattr("socket.socket.connect", unexpected_network)


@pytest.fixture
def provider_response():
    return (Path(__file__).parent / "fixtures/search_ai_mode/response.md").read_text(encoding="utf-8")


@pytest.fixture
def ai_mode_provider(monkeypatch, provider_response):
    responses, calls = {}, []

    def fake_request(session, method, url, params, **kwargs):
        assert method == "GET" and url == "https://serpapi.com/search"
        assert params["api_key"] == "offline-test-key"
        calls.append({key: value for key, value in params.items() if key != "api_key"})
        response = responses.get(params["q"], provider_response)
        if isinstance(response, Exception):
            raise response
        http = requests.Response()
        http.status_code, http.encoding = 200, "utf-8"
        http.headers["Content-Type"] = "text/markdown; charset=utf-8" if isinstance(response, str) else "application/json"
        http._content = (response if isinstance(response, str) else json.dumps(response)).encode("utf-8")
        return http

    monkeypatch.setenv("SERPAPI_API_KEY", "offline-test-key")
    monkeypatch.setattr(requests.Session, "request", fake_request)
    return responses, calls


def run_ai_mode(data=None, output=None, **options):
    if data is None:
        data = pd.DataFrame({"query": ["product"], "ID": [42]})
    args = {"queries": "query", "id": "ID", "output": ["body", "metadata"] if output is None else output,
            "threads": 1, **options}
    return wrangles.recipe.run({"wrangles": [{"search.ai_mode": args}]}, dataframe=data)


def test_markdown_body_and_json_metadata_are_preserved(ai_mode_provider, provider_response):
    row = run_ai_mode().iloc[0]
    assert row["body"] == provider_response.split("\n---\n", 1)[1]
    assert r"$12\text{ VDC}$" in row["body"]  # Cleanup belongs in the next wrangle.
    assert "Go to product viewer" in row["body"]
    meta = row["metadata"]
    assert (meta["status"], meta["search_id"], meta["query"], meta["query_index"], meta["input_row_id"]) == (
        "Success", "synthetic-ai-mode", "product", 1, 42,
    )
    assert meta["search_metadata"]["created_at"] == "2026-09-20T12:00:00+00:00"
    assert meta["search_parameters"]["device"] == "desktop"
    assert "raw_response" not in meta
    json.dumps(meta, allow_nan=False)
    assert ai_mode_provider[1] == [{"engine": "google_ai_mode", "q": "product", "output": "md"}]


def test_raw_response_is_opt_in(ai_mode_provider, provider_response):
    row = run_ai_mode(include_raw_response=True).iloc[0]
    assert row["metadata"]["raw_response"] == provider_response
    assert row["body"] != provider_response


@pytest.mark.parametrize("body", ["\n### Odd heading\n\n- nested:\n  - content\n\n---\nFooter", "Long " * 9000], ids=["nested", "long"])
def test_body_is_not_section_parsed_cleaned_or_truncated(ai_mode_provider, body):
    ai_mode_provider[0]["product"] = "---\nsearch_metadata:\n  status: Success\n---\n" + body
    assert run_ai_mode().iloc[0]["body"] == body


@pytest.mark.parametrize("frontmatter", ["[]", "null", "a: [", "a: !!python/object:bad {}", "a: &x [*x]", "a: .nan", "a: !!set {x: null}"])
def test_invalid_frontmatter_is_an_explicit_error(ai_mode_provider, frontmatter):
    ai_mode_provider[0]["product"] = f"---\n{frontmatter}\n---\nEvidence"
    row = run_ai_mode().iloc[0]
    assert row["metadata"]["status"] == "Error"
    assert row["metadata"]["error"] == "Invalid YAML search metadata."


@pytest.mark.parametrize("response", ["Plain body", "---\nsearch_metadata: {}", None, 123, []])
def test_missing_frontmatter_or_wrong_type_is_an_error(ai_mode_provider, response):
    ai_mode_provider[0]["product"] = response
    assert run_ai_mode().iloc[0]["metadata"]["status"] == "Error"


@pytest.mark.parametrize("metadata", ["{}", "search_metadata: []", "search_metadata: {}", "search_metadata: {status: 42}", "search_metadata: {status: ''}"])
def test_missing_or_invalid_status_is_an_error(ai_mode_provider, metadata):
    ai_mode_provider[0]["product"] = f"---\n{metadata}\n---\nEvidence"
    row = run_ai_mode().iloc[0]
    assert row["metadata"]["status"] == "Error" and row["metadata"]["error"]
    assert row["body"] == "Evidence"


@pytest.mark.parametrize("status", ["Processing", "Queued", "Error", "Unknown"])
def test_non_success_status_does_not_become_success(ai_mode_provider, status):
    ai_mode_provider[0]["product"] = f"---\nsearch_metadata:\n  status: {status}\n---\nEvidence"
    assert run_ai_mode().iloc[0]["metadata"]["status"] == status


def test_empty_success_and_json_errors(ai_mode_provider):
    ai_mode_provider[0]["product"] = "---\nsearch_metadata:\n  status: Success\n---\n \n"
    assert run_ai_mode().iloc[0]["metadata"]["status"] == "Error"
    ai_mode_provider[0]["product"] = {"search_metadata": {"id": "failed", "status": "Success"}, "error": "Provider failed"}
    meta = run_ai_mode().iloc[0]["metadata"]
    assert meta["status"] == "Error" and meta["search_id"] == "failed" and meta["error"] == "Provider failed"
    ai_mode_provider[0]["product"] = {"search_metadata": {"id": "pending", "status": "Processing"}}
    assert run_ai_mode().iloc[0]["metadata"]["status"] == "Processing"


def test_credentials_are_redacted_from_errors_and_raw_responses(ai_mode_provider, provider_response):
    ai_mode_provider[0]["product"] = RuntimeError("failed with offline-test-key")
    assert "offline-test-key" not in json.dumps(run_ai_mode().iloc[0]["metadata"])
    ai_mode_provider[0]["product"] = provider_response + "offline-test-key"
    row = run_ai_mode(include_raw_response=True).iloc[0]
    assert "offline-test-key" not in json.dumps(row.to_dict())


def test_ordered_batch_blanks_and_errors_keep_input_ids(ai_mode_provider):
    ai_mode_provider[0]["failed"] = RuntimeError("Synthetic failure")
    df = run_ai_mode(pd.DataFrame({"query": [" product ", "failed", None, pd.NA, float("nan")], "ID": [7, 8, 9, 10, 11]}), threads=2)
    assert [meta["status"] for meta in df["metadata"]] == ["Success", "Error", "Skipped", "Skipped", "Skipped"]
    assert [meta["input_row_id"] for meta in df["metadata"]] == [7, 8, 9, 10, 11]
    assert [meta["query_index"] for meta in df["metadata"]] == [1, 2, 3, 4, 5]
    assert len(ai_mode_provider[1]) == 2


def test_all_blanks_and_empty_input_need_no_credentials(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    assert wrangles.search.ai_mode("")["ai_mode_metadata"]["status"] == "Skipped"
    assert wrangles.search.ai_mode([]) == []
    assert run_ai_mode(pd.DataFrame({"query": [], "ID": []})).empty


@pytest.mark.parametrize("output", ["answer", ["answer"]])
def test_one_output_is_markdown(ai_mode_provider, output):
    assert isinstance(run_ai_mode(output=output).iloc[0]["answer"], str)


@pytest.mark.parametrize("output", [[], ["a", "a"], ["a", "b", "c"], [""], 42])
def test_invalid_output_fails_before_search(ai_mode_provider, output):
    with pytest.raises(ValueError):
        run_ai_mode(output=output)
    assert not ai_mode_provider[1]


@pytest.mark.parametrize("query", [["a", "b"], 123, True, {}])
def test_non_string_query_cells_fail_before_search(ai_mode_provider, query):
    with pytest.raises(TypeError):
        run_ai_mode(pd.DataFrame({"query": [query], "ID": [1]}))
    assert not ai_mode_provider[1]


def test_locale_aliases_omissions_and_raw_option(ai_mode_provider):
    run_ai_mode(country="uk", language="en", location="London, England, United Kingdom", include_raw_response=True)
    assert ai_mode_provider[1][-1] == {"engine": "google_ai_mode", "output": "md", "q": "product",
                                     "gl": "uk", "hl": "en", "location": "London, England, United Kingdom"}
    run_ai_mode(country=None, language="", location=None)
    assert ai_mode_provider[1][-1] == {"engine": "google_ai_mode", "output": "md", "q": "product"}
    direct = wrangles.search.ai_mode("product", gl="us", hl="es")
    assert set(direct) == {"ai_mode_results", "ai_mode_metadata"}
    assert ai_mode_provider[1][-1]["gl"] == "us"


@pytest.mark.parametrize("options", [{"country": "us", "gl": "uk"}, {"language": "en", "hl": "de"},
                                     {"query_config": [{"Heading": "Instructions"}]}, {"n_results": 4},
                                     {"google_domain": "google.com"}, {"threads": 0}, {"threads": True}])
def test_unsupported_or_conflicting_options_fail_before_search(ai_mode_provider, options):
    with pytest.raises(ValueError):
        run_ai_mode(**options)
    assert not ai_mode_provider[1]


def test_schema_matches_markdown_and_metadata_contract():
    schema = yaml.safe_load(recipe_search.ai_mode.__doc__)
    jsonschema.Draft7Validator.check_schema(schema)
    valid = {"queries": "query", "id": "ID", "output": ["body", "metadata"], "country": None, "language": "en"}
    jsonschema.validate(valid, schema)
    for change in ({"output": ["a", "b", "c"]}, {"output": ["a", "a"]}, {"output": []},
                   {"query_config": [{"a": "b"}]}, {"n_results": 5}, {"queries": ["query"]}, {"threads": 0}):
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
