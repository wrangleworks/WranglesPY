"""Offline evidence-to-extract.ai trials, independent of the search engine."""

from collections import UserDict
from copy import deepcopy
import json
import sys
from types import ModuleType

import pytest

import run_search_ai_mode as runner
from wrangles import _ai_mode, ai_cache
from wrangles._search_ai_extraction import prepare_evidence, format_product_result


LABELS = {"description": "Product Description", "specifications": "Technical Specifications", "pricing": "Pricing & Sources"}
MAKER = "https://maker.invalid/specs"
SUPPLIER = "https://supplier.invalid/item?variant=1&currency=USD"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr("wrangles.auth.get_applied_permission_group", lambda: None)

    def unexpected_network(*args, **kwargs):
        pytest.fail("These trials must not use the network")

    monkeypatch.setattr("socket.socket.connect", unexpected_network)
    ai_cache.clear()
    yield
    ai_cache.clear()


@pytest.fixture
def answer():
    return {
        "text_blocks": [
            {"type": "heading", "snippet": "Product Description"},
            {"type": "paragraph", "snippet": "A synthetic product."},
            {"type": "heading", "snippet": "Technical Specifications"},
            {"type": "list", "list": [{"snippet": r"Pitch: $1/2$ inch", "reference_indexes": [91]}]},
            {"type": "heading", "snippet": "Pricing & Sources"},
            {"type": "table", "table": [["Supplier", "Price", "Link"], ["Supplier A", "$13.15 USD", "Product Page"]],
             "detailed": [[{"snippet": "Supplier"}, {"snippet": "Price"}, {"snippet": "Link"}],
                          [{"snippet": "Supplier A"}, {"snippet": "$13.15 USD"},
                           {"snippet": "Product Page", "snippet_links": [{"link": SUPPLIER + "&srsltid=tracking"}]}]],
             "formatted": [{"supplier": "Supplier A", "price": "$13.15 USD", "link": "Product Page"}]},
            {"type": "comparison", "comparison": [{"feature": "New provider shape", "values": ["a", "b"]}]},
        ],
        "references": [{"index": 91, "source": "Manufacturer", "link": MAKER, "thumbnail": "image"}],
    }


def test_mode_and_overview_share_evidence_without_flattening(answer):
    original = deepcopy(answer)
    mode_response = {**answer, "search_metadata": {"status": "Success"}, "reconstructed_markdown": "Original Markdown"}
    complete = _ai_mode.normalize_response(mode_response, "query", list(LABELS.values()))["ai_mode_result_complete"]
    mode = prepare_evidence(complete)
    classic_response = {"organic_results": [{"link": "https://unrelated.invalid/"}], "ai_overview": answer}
    overview = prepare_evidence(classic_response["ai_overview"])
    for evidence in (mode, overview):
        assert [(source["id"], source["url"], source["reference_indexes"]) for source in evidence["sources"]] == [
            ("s1", MAKER, [91]), ("s2", SUPPLIER, []),
        ]
        assert "unrelated.invalid" not in json.dumps(evidence)
        assert "meta_data" not in evidence["content"]
    assert mode["content"]["Pricing & Sources"][0]["table"] == answer["text_blocks"][5]["table"]
    assert overview["content"]["text_blocks"][-1] == answer["text_blocks"][-1]
    assert overview["content"]["text_blocks"][5]["formatted"] == answer["text_blocks"][5]["formatted"]
    assert "/text_blocks/5/detailed/1/2/snippet_links/0/link" in overview["sources"][1]["evidence_paths"]
    assert answer == original


def test_evidence_keeps_unmatched_content_and_sources_but_not_transport_metadata(answer):
    complete = {"Product Description": [], "references": answer["references"], "raw_response": {"secret_transport": "omit"},
                "meta_data": {"query": "do not repeat", "google_ai_mode_url": "https://google.invalid/transport",
                              "unmatched_sections": [{"heading": {"snippet": "Unexpected label"},
                                                      "text_blocks": answer["text_blocks"]}],
                              "unsectioned_text_blocks": [{"snippet": "Opening facts"}]}}
    evidence = prepare_evidence(complete)
    assert evidence["content"]["unsectioned_text_blocks"] == [{"snippet": "Opening facts"}]
    assert evidence["content"]["unmatched_sections"][0]["heading"]["snippet"] == "Unexpected label"
    assert [source["url"] for source in evidence["sources"]] == [MAKER, SUPPLIER]
    assert "secret_transport" not in json.dumps(evidence) and "google.invalid" not in json.dumps(evidence)


def test_catalog_deduplicates_urls_and_preserves_provider_ids():
    evidence = prepare_evidence({
        "references": [{"index": 91, "link": SUPPLIER + "&utm_source=google"},
                       {"index": 7, "source": "Supplier", "link": SUPPLIER},
                       {"index": 8, "source": "Google", "link": "https://www.google.com/search?ibp=oshop&prds=123"}],
        "text_blocks": [{"formatted": [{"link": SUPPLIER.replace("&", "&amp;")}],
                         "table": [["Link"], [SUPPLIER]], "snippet": "Product Page"}],
    })
    assert len(evidence["sources"]) == 1
    assert evidence["sources"][0]["reference_indexes"] == [91, 7]
    assert evidence["sources"][0]["site"] == "Supplier"
    assert evidence["sources"][0]["url"] == SUPPLIER
    assert len(evidence["sources"][0]["evidence_paths"]) == 4


def test_offers_follow_catalog_order_keep_all_sources_and_flag_unknown_ids(answer):
    evidence = prepare_evidence(answer)
    extracted = {"description": "Product.", "specifications": [{"name": "Pitch", "value": "1/2 inch"}], "offers": [
        {"supplier": "Supplier A", "price": "$13.15 USD", "source_ids": ["s2", "s2"]},
        {"supplier": "Unknown supplier", "price": "$8", "source_ids": ["https://invented.invalid/item"]},
        {"supplier": "Supplier A", "price": "$12 USD for 10+", "source_ids": ["s2"]},
    ]}
    original = deepcopy(extracted)
    result, metadata = format_product_result(extracted, evidence, **LABELS)
    assert result["Technical Specifications"] == [{"Pitch": "1/2 inch"}]
    assert list(zip(result["Pricing & Sources"], result["references"], strict=True)) == [
        ({"Manufacturer": ""}, MAKER),
        ({"Supplier A": "$13.15 USD"}, SUPPLIER),
        ({"Supplier A": "$12 USD for 10+"}, SUPPLIER),
        ({"Unknown supplier": "$8"}, ""),
    ]
    assert any("unknown_source_id" in warning for warning in metadata["warnings"])
    assert metadata["status"] == "partial"
    assert "https://invented.invalid/item" not in result["references"]
    assert extracted == original


@pytest.mark.parametrize("extracted", [None, "Failed", []])
def test_failed_extraction_is_explicit_and_preserves_reference_slots(answer, extracted):
    result, metadata = format_product_result(extracted, prepare_evidence(answer), **LABELS)
    assert metadata["status"] == "error"
    assert result["Pricing & Sources"] == [{"Manufacturer": ""}, {"supplier.invalid": ""}]
    assert result["references"] == [MAKER, SUPPLIER]


@pytest.fixture
def trial_extraction():
    return {"description": "A synthetic product.", "specifications": [{"name": "Pitch", "value": "1/2 inch"}],
            "offers": [{"supplier": "Supplier A", "price": "$13.15 USD", "source_ids": ["s2"]}]}


@pytest.fixture
def trial(monkeypatch, tmp_path, answer, trial_extraction):
    import serpapi
    from wrangles import extract

    response = {**deepcopy(answer), "search_metadata": {"status": "Success", "id": "synthetic"},
                "search_parameters": {"gl": "us", "hl": "en"}, "reconstructed_markdown": "# Original\n\n" + "Evidence " * 5000}
    searches, extractions = [], []

    def search(client, params):
        searches.append(params)
        return UserDict(deepcopy(response))

    class Response:
        ok, status_code, headers = True, 200, {}

        def json(self):
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"search_ai_extracted": trial_extraction})}]}]}

    def post(**kwargs):
        extractions.append(kwargs["json"])
        return Response()

    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    monkeypatch.setenv("SERPAPI_API_KEY", "offline-search")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-extract")
    monkeypatch.setattr(serpapi.Client, "search", search)
    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    monkeypatch.setattr(runner, "OUTPUT_DIRECTORY", tmp_path)
    monkeypatch.setattr(runner, "WRITE_OUTPUTS", False)
    monkeypatch.setattr(runner, "EXTRACT_ENABLED", True)
    monkeypatch.setattr(runner, "EXTRACT_MODEL", None)
    monkeypatch.setattr(runner, "NROWS", 1)
    monkeypatch.setattr(runner, "REPLAY_FILE", None)
    return searches, extractions, response


def test_trial_uses_real_extract_ai_schema_and_preserves_search_outputs(trial):
    searches, extractions, response = trial
    df = runner.main()
    expected_query = """Provide the following product information:

- Product Description: 1-3 sentences including the product name and key features.
- Technical Specifications: List confirmed technical specifications.
- Pricing & Sources: List suppliers and available pricing with source links.

for this product:

> INA NATV6-PP-A YOKE TYPE TRACK ROLLERS NATV..-PP FULL COMPLEMENT NEEDL
> Mfr: INA
> MPN: NATV6-PP-A

Use the exact information labels as headings. Include only the requested sections; no follow-up questions."""
    assert searches[0]["q"] == expected_query
    assert len(extractions) == 1
    request = extractions[0]
    assert request["text"]["format"]["strict"] is True
    assert "tools" not in request  # No second web search.
    assert "detailed" in json.dumps(request["input"])
    assert "search_metadata" not in json.dumps(request["input"])
    assert df.iloc[0]["ai_mode_result_structured"]["references"] == [MAKER, SUPPLIER]
    assert df.iloc[0]["ai_mode_structured_meta"]["status"] == "complete"
    assert df.iloc[0]["ai_mode_markdown"] == response["reconstructed_markdown"]
    assert df.iloc[0]["ai_mode_result_complete"]["Pricing & Sources"][0]["formatted"] == response["text_blocks"][5]["formatted"]
    assert all(column in df for column in ("ai_mode_result", "ai_mode_result_complete", "ai_mode_markdown"))


def test_json_snapshot_replays_without_search_or_excel_truncation(trial, monkeypatch, tmp_path):
    searches, extractions, response = trial
    monkeypatch.setattr(runner, "WRITE_OUTPUTS", True)
    first = runner.main()
    snapshot, = tmp_path.glob("*.json")
    saved = json.loads(snapshot.read_text(encoding="utf-8"))
    assert saved[0]["ai_mode_markdown"] == response["reconstructed_markdown"]
    assert len(saved[0]["ai_mode_markdown"]) > 32767
    assert len(list(tmp_path.glob("*.xlsx"))) == 1
    ai_cache.clear()
    monkeypatch.setattr(runner, "REPLAY_FILE", snapshot)
    monkeypatch.delenv("SERPAPI_API_KEY")
    second = runner.main()
    assert len(searches) == 1 and len(extractions) == 2
    assert len(list(tmp_path.glob("*.json"))) == 2
    assert first.iloc[0]["ai_mode_result_structured"] == second.iloc[0]["ai_mode_result_structured"]
    assert first.iloc[0]["search_query"] == second.iloc[0]["search_query"]


def test_nested_section_labels_reach_extraction_and_displayed_columns(trial, trial_extraction, monkeypatch, tmp_path):
    import pandas as pd

    searches, extractions, response = trial
    response["references"] = []
    response["text_blocks"] = [{"type": "list", "list": [
        {"snippet": "Product Description: A synthetic product."},
        {"snippet": "Technical Specifications:", "list": [{"snippet": r"Pitch: $1/2$ inch"}]},
        {"snippet": "Pricing & Sources:", "list": [{"snippet": "Supplier A: £8.22 (excluding VAT)",
                                                   "snippet_links": [{"text": "Supplier A", "link": SUPPLIER}]}]},
    ]}]
    trial_extraction["offers"] = [{"supplier": "Supplier A", "price": "£8.22 (excluding VAT)", "source_ids": ["s1"]}]
    monkeypatch.setattr(runner, "WRITE_OUTPUTS", True)

    df = runner.main()
    row = df.iloc[0]
    assert len(searches) == len(extractions) == 1
    assert row["ai_mode_result"]["Product Description"] == ""
    assert row["ai_mode_result_complete"]["meta_data"]["missing_headings"] == list(LABELS.values())
    assert row["search_ai_evidence"]["content"]["unsectioned_text_blocks"] == response["text_blocks"]
    assert "unsectioned_text_blocks" in json.dumps(extractions[0]["input"])
    assert row["ai_mode_structured_meta"]["status"] == "complete"
    for heading in (*LABELS.values(), "references"):
        assert row[heading] == row["ai_mode_result_structured"][heading]
    assert row["Product Description"] == "A synthetic product."
    assert row["Technical Specifications"] == [{"Pitch": "1/2 inch"}]
    assert list(zip(row["Pricing & Sources"], row["references"], strict=True)) == [
        ({"Supplier A": "£8.22 (excluding VAT)"}, SUPPLIER),
    ]
    workbook, = tmp_path.glob("*.xlsx")
    exported = pd.read_excel(workbook).iloc[0]
    assert exported["Product Description"] == row["Product Description"]
    assert "1/2 inch" in exported["Technical Specifications"]
    assert "£8.22 (excluding VAT)" in exported["Pricing & Sources"]
    assert SUPPLIER in exported["references"]
    assert "ai_mode_result" in exported.index


@pytest.mark.parametrize("state", ["error", "disabled", "blank", "processing"])
def test_trial_skips_extraction_without_successful_search(trial, monkeypatch, state):
    searches, extractions, response = trial
    if state == "error":
        response["error"] = "Synthetic provider error"
    elif state == "disabled":
        monkeypatch.setattr(runner, "EXTRACT_ENABLED", False)
        monkeypatch.delenv("OPENAI_API_KEY")
    elif state == "processing":
        response["search_metadata"]["status"] = "Processing"
    else:
        response["text_blocks"] = []
        response["references"] = []
        response["reconstructed_markdown"] = ""
    df = runner.main()
    assert extractions == []
    assert df.iloc[0]["ai_mode_structured_meta"]["status"] == "skipped"
    assert df.iloc[0]["ai_mode_result_structured"] == {
        "Product Description": "", "Technical Specifications": [], "Pricing & Sources": [], "references": [],
    }
    if state == "disabled":
        for heading in (*LABELS.values(), "references"):
            assert df.iloc[0][heading] == df.iloc[0]["ai_mode_result"][heading]
    else:
        assert not any(df.iloc[0][heading] for heading in (*LABELS.values(), "references"))


def test_trial_keeps_mixed_success_and_failure_on_their_input_rows(trial, monkeypatch):
    import serpapi

    searches, extractions, response = trial
    original_search = serpapi.Client.search

    def search(client, params):
        result = original_search(client, params)
        if "MPN: FAILED-2" in params["q"]:
            result["error"] = "Synthetic second-row failure"
        return result

    monkeypatch.setattr(serpapi.Client, "search", search)
    # Keep this two-row regression independent of user-editable trial samples.
    monkeypatch.setattr(runner, "INPUT_ROWS", [
        {"ID": 14, "Description": "Synthetic successful product", "Mfr": "Example", "MPN": "OK-1", "part_codes": ["OK-1"]},
        {"ID": 27, "Description": "Synthetic failed product", "Mfr": "Example", "MPN": "FAILED-2", "part_codes": ["FAILED-2"]},
    ])
    monkeypatch.setattr(runner, "NROWS", None)
    df = runner.main()
    assert len(searches) == 2 and len(extractions) == 1
    assert df["ID"].tolist() == [14, 27]
    assert df.iloc[0]["ai_mode_result_structured"]["references"] == [MAKER, SUPPLIER]
    assert not any(df.iloc[1]["ai_mode_result_structured"].values())
    assert not any(df.iloc[1][heading] for heading in (*LABELS.values(), "references"))
    assert df.iloc[1]["ai_mode_result_complete"]["meta_data"]["error"] == "Synthetic second-row failure"
    assert df.iloc[1]["ai_mode_structured_meta"]["status"] == "skipped"
