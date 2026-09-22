"""Offline Markdown-to-extract.ai trials and evidence validation."""

from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from types import ModuleType

import pandas as pd
import pytest
import requests

from tests.fixtures.search_ai_mode import run_search_ai_mode as runner
from wrangles import ai_cache
from wrangles._search_ai_content import google_product_url, markdown_urls, source_url, unlink_description
from wrangles._search_ai_extraction import validate_sources


MAKER = "https://maker.invalid/specs"
SUPPLIER = "https://supplier.invalid/item?variant=1&currency=USD"
GOOGLE_VIEWER = "https://www.google.com/search?ibp=oshop&prds=productid:123"
GOOGLE_REFERENCE = {"id": "00", "source": "Google", "url": GOOGLE_VIEWER}
QUERY_SECTIONS = (
    "Summarize information in 4 sections: "
    "Product Description (1-3 sentences, plain text with no links) | "
    "Specifications (as name value pairs) | "
    "Pricing (including the supplier name and source link) | "
    "Results Summary (count of references and count of prices found). "
    "Use the exact section labels as headings. Do not ask follow-up questions."
)


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
def markdown():
    return (Path(__file__).parent / "fixtures/search_ai_mode/response.md").read_text(encoding="utf-8")


@pytest.fixture
def extracted():
    return {
        "Product Description": "The Example P12 supplies regulated power.",
        "Match Confidence": "Uncertain",
        "Specifications": [{"name": "Voltage", "value": "12 VDC"}],
        "Pricing": [{"price": 13.15, "currency": "USD", "uom": "pack", "source": "Supplier A",
                    "reference_ids": ["02"], "price_text": "$13.15 USD per pack of 10, excluding VAT"}],
        "references": [{"id": "01", "source": "Manufacturer", "url": MAKER},
                       {"id": "02", "source": "Supplier A", "url": SUPPLIER}],
    }


def test_response_structuring_unlinks_description_and_preserves_raw_evidence():
    # User-reported wording with a shortened, synthetic viewer destination.
    label = r"Renold Gy08B duplex roller chain connecting/roller link \(GY08B2S26I\)"
    viewer_text = "Go to product viewer dialog for this item."
    url = r"https://www.google.com/search?ibp=oshop&prds=item(123)&q=product&raw=\u0026"
    price_text = (
        " typically ranges in price from $6.00 to $18.77 USD per individual link"
        " depending on the industrial supplier. [0]"
    )
    sentence = f"The [{label}{viewer_text}]({url}){price_text}"
    expected = f"The {label}{price_text}"
    protected = "\n\n".join([
        f"`{sentence}`",
        f"```\n{sentence}\n```",
        f"    {sentence}",
        "### Pricing\n" + viewer_text,
        f"[Supplier]({SUPPLIER})",
    ])
    original = sentence + "\n\n" + protected
    df = pd.DataFrame({"raw": [original, None, 42], "meta": [{}, {}, {}]})

    cleaned = runner.structure_search_response(df, input="raw", metadata="meta", output="clean")
    assert cleaned["raw"].tolist() == [original, None, 42]
    assert cleaned["clean"].tolist() == [expected + "\n\n" + protected, None, 42]
    assert cleaned.iloc[0]["meta"]["google_product_url"] == url
    repeated = runner.structure_search_response(deepcopy(cleaned), input="raw", metadata="meta", output="clean")
    assert repeated.equals(cleaned)


def test_catalog_and_viewer_links_are_removed_without_losing_source_evidence():
    catalog = "https://maker.invalid/en/track-rollers,natv6-pp-a/p/399049"
    viewer = "https://www.google.com/search?ibp=oshop&prds=item(123)&q=product"
    description = (
        f"The [Schaeffler Medias Product Catalog]({catalog}) lists the "
        rf"[INA NATV6\-PP\-A]({viewer}) as a single\-row yoke\-type track roller. [1]"
    )
    rest = (f"### Pricing\n[Supplier]({SUPPLIER}): $13.15 each.\n\n"
            f"### Results Summary\n1 price. [Google product viewer]({viewer})\n")
    original = "### Product Description\n\n" + description + "\n\n" + rest
    result = unlink_description(original, "Product Description", ["Pricing", "Results Summary"])
    expected = (r"The Schaeffler Medias Product Catalog lists the INA NATV6\-PP\-A "
                r"as a single\-row yoke\-type track roller. [1]")
    assert result.startswith("### Product Description\n\n" + expected + "\n\n" + rest)
    assert f"[Schaeffler Medias Product Catalog]({catalog})" in result.split("### Links from Product Description")[1]
    assert set(markdown_urls(result)) == set(markdown_urls(original))
    assert result.count(viewer) == 1
    assert unlink_description(result, "Product Description", ["Pricing", "Results Summary"]) == result


@pytest.mark.parametrize("heading, end", [
    ("### Product Description\n", "### Specifications\n"),
    ("### Product Description ###\n", "### Specifications ###\n"),
    ("**Product Description**\n", "**Specifications**\n"),
    ("Product Description: ", "Specifications: "),
    ("- **Product Description:** ", "- **Specifications:** "),
    ("Product Description\n-------------------\n", "Specifications\n--------------\n"),
    ("", "### Specifications\n"),
])
def test_description_heading_forms_do_not_unlink_other_sections(heading, end):
    product = f"[Part]({MAKER})"
    other = end + f"[Specification sheet]({MAKER})\n"
    original = heading + f"The {product} is a pump. [1]\n\n" + other
    result = unlink_description(original, "Product Description", ["Specifications"])
    assert result == heading + "The Part is a pump. [1]\n\n" + other


@pytest.mark.parametrize("link, expected", [
    (r'[Part \(P12\)](https://maker.invalid/a_(b)?v=1 "Catalog")', r"Part \(P12\)"),
    ("[Part [P12]](https://maker.invalid/specs)", "Part [P12]"),
    ("[Part\nP12](\nhttps://maker.invalid/specs\n)", "Part\nP12"),
    ("[Part][maker]", "Part"),
    ("[maker][]", "maker"),
    ("[maker]", "maker"),
    ('<a href="https://maker.invalid/specs">Part</a>', "Part"),
    ("<https://maker.invalid/specs>", ""),
    ("https://maker.invalid/specs", ""),
    ("www.maker.invalid/specs", ""),
])
def test_description_link_formats_keep_labels_and_citations(link, expected):
    original = (f"### Product Description\n{link}. [1]\n\n### References\n"
                f"[maker]: {MAKER}\n")
    result = unlink_description(original, "Product Description", ["References"])
    assert result.startswith(f"### Product Description\n{expected}. [1]\n\n### References\n")
    assert f"[maker]: {MAKER}" in result


def test_unheaded_preamble_and_unknown_sections_remain_unchanged():
    preamble = f"Found this [catalog]({MAKER}).\n\n"
    ending = f"\n\n### Availability\n[Supplier]({SUPPLIER})\n"
    original = preamble + f"### Product Description\nThe [Part]({MAKER}) is a pump." + ending
    assert unlink_description(original, "Product Description", ["Pricing"]) == (
        preamble + "### Product Description\nThe Part is a pump." + ending
    )


def test_structuring_saves_raw_response_only_when_requested(tmp_path):
    original = f"### Product Description\nThe [Part]({MAKER}) is a pump."
    raw = "---\nsearch_metadata:\n  status: Success\n---\n" + original
    frame = pd.DataFrame({"raw": [original], "meta": [{"raw_response": raw}]})
    prefix = tmp_path / "trial"
    first = runner.structure_search_response(frame, input="raw", metadata="meta", output="clean", prefix=prefix)
    assert not list(tmp_path.iterdir())
    assert first.iloc[0]["meta"]["raw_response"] == raw
    saved = runner.structure_search_response(first, input="raw", metadata="meta", output="clean", prefix=prefix, save_raw=True)
    assert (tmp_path / "trial_row001.md").read_text(encoding="utf-8") == raw
    assert saved.iloc[0]["raw"] == original
    assert "raw_response" not in saved.iloc[0]["meta"]
    assert saved.iloc[0]["clean"].startswith("### Product Description\nThe Part is a pump.")


@pytest.mark.parametrize("link", [
    f"[Part]({GOOGLE_VIEWER}&srsltid=tracking)",
    f'[Part](<{GOOGLE_VIEWER}&amp;srsltid=tracking> "Product viewer")',
    f"[Part](\n{GOOGLE_VIEWER}\n)",
    f'<a href="{GOOGLE_VIEWER}">Part</a>',
    f"<{GOOGLE_VIEWER}>",
    GOOGLE_VIEWER,
    "[Part][product]",
])
def test_structuring_captures_viewer_from_description_link_formats(link):
    raw = (f"### Product Description\n{link} is the product.\n\n"
           "### Results Summary\nOne price.\n\n"
           f"[product]: {GOOGLE_VIEWER}\n")
    frame = pd.DataFrame({"raw": [raw], "meta": [{"status": "Success"}]})
    result = runner.structure_search_response(frame, input="raw", metadata="meta", output="clean").iloc[0]
    assert result["raw"] == raw
    assert result["meta"]["google_product_url"] == GOOGLE_VIEWER
    assert "http" not in result["clean"].split("### Results Summary")[0]
    assert "[Part]" not in result["clean"].split("### Results Summary")[0]
    assert GOOGLE_VIEWER in markdown_urls(result["clean"], include_google_products=True)


@pytest.mark.parametrize("raw", [
    "### Product Description\nA pump.\n\n### Results Summary\n" + f"[Viewer]({GOOGLE_VIEWER})",
    "### Product Description\n\n    " + f"[Viewer]({GOOGLE_VIEWER})",
    "### Product Description\n" + f"![Thumbnail]({GOOGLE_VIEWER})",
    "### Product Description\n[Part](https://www.google.com.invalid/search?ibp=oshop&prds=123)",
    "### Product Description\n[Part](https://www.google.com/search?q=pump)",
    f"### Product Description\n[Part]({SUPPLIER})",
    None,
])
def test_structuring_does_not_invent_or_reuse_stale_google_references(raw):
    frame = pd.DataFrame({"raw": [raw], "meta": [{"google_product_url": GOOGLE_VIEWER}]})
    result = runner.structure_search_response(frame, input="raw", metadata="meta", output="clean").iloc[0]
    assert "google_product_url" not in result["meta"]


def test_first_description_viewer_is_reserved_and_additional_links_stay_in_evidence():
    second = "https://www.google.co.uk/shopping/product/456"
    raw = f"### Product Description\n[First]({GOOGLE_VIEWER}) and [Second]({second})."
    frame = pd.DataFrame({"raw": [raw], "meta": [{}]})
    result = runner.structure_search_response(frame, input="raw", metadata="meta", output="clean").iloc[0]
    assert result["meta"]["google_product_url"] == GOOGLE_VIEWER
    assert {GOOGLE_VIEWER, second} <= set(markdown_urls(result["clean"], include_google_products=True))
    assert google_product_url(second + "?srsltid=tracking") == second


def test_google_reference_is_added_without_renumbering_or_requiring_model_references(markdown, extracted):
    references, offers, meta = validate_sources(
        extracted["references"], extracted["Pricing"], markdown, google_product=GOOGLE_VIEWER,
    )
    assert references == [GOOGLE_REFERENCE, *extracted["references"]]
    assert offers == extracted["Pricing"] and meta["status"] == "complete"
    assert validate_sources([], [], markdown, google_product=GOOGLE_VIEWER)[0] == [GOOGLE_REFERENCE]
    assert validate_sources(None, None, markdown, google_product=GOOGLE_VIEWER)[0] == [GOOGLE_REFERENCE]


def test_reserved_google_id_cannot_be_replaced_or_used_as_a_supplier_reference(markdown, extracted):
    extracted["references"].append({"id": "00", "source": "Supplier A", "url": SUPPLIER})
    extracted["Pricing"][0]["reference_ids"] = ["00", "02"]
    references, offers, meta = validate_sources(
        extracted["references"], extracted["Pricing"], markdown, google_product=GOOGLE_VIEWER,
    )
    assert references == [GOOGLE_REFERENCE, *extracted["references"][:2]]
    assert offers[0]["reference_ids"] == ["02"]
    assert meta["rejected_references"][0]["reason"] == "reserved_reference_id"
    assert validate_sources(extracted["references"], [], markdown)[0] == extracted["references"][:2]


@pytest.mark.parametrize("url", [SUPPLIER, GOOGLE_VIEWER + "456", "https://google.com.invalid/search?ibp=oshop"])
def test_google_reference_requires_an_actual_viewer_url_in_the_evidence(markdown, url):
    references, _, meta = validate_sources([], [], markdown, google_product=url)
    assert references == []
    assert meta["warnings"] == ["google_product_url_not_in_evidence"]


def test_selected_references_and_offers_are_independent(markdown, extracted):
    original = deepcopy(extracted)
    references, offers, meta = validate_sources(extracted["references"], extracted["Pricing"], markdown)
    assert meta["status"] == "complete"
    assert len(references) == 2 and len(offers) == 1
    assert offers == extracted["Pricing"]
    assert references == extracted["references"]
    assert "https://dictionary.invalid/product" in meta["unselected_source_urls"]
    assert extracted == original


def test_multiple_prices_and_uncertain_associations_are_preserved(markdown, extracted):
    extracted["Pricing"].extend([
        {**extracted["Pricing"][0], "price": 12, "price_text": "$12 per pack for 5+ packs"},
        {"price": None, "currency": None, "uom": None, "source": "Unknown", "reference_ids": [], "price_text": "Call for quote"},
    ])
    references, offers, meta = validate_sources(extracted["references"], extracted["Pricing"], markdown)
    assert len(offers) == 3 and len(references) == 2
    assert offers[2] == extracted["Pricing"][2]
    assert meta["status"] == "complete"


def test_invented_urls_and_unknown_ids_are_rejected_without_guessing(markdown, extracted):
    extracted["references"].append({"id": "03", "source": "Supplier A", "url": "https://supplier.invalid/invented"})
    extracted["Pricing"][0]["reference_ids"] = ["03", "99"]
    references, offers, meta = validate_sources(extracted["references"], extracted["Pricing"], markdown)
    assert [reference["id"] for reference in references] == ["01", "02"]
    assert offers[0]["reference_ids"] == []
    assert offers[0]["price"] == 13.15
    assert meta["status"] == "partial" and len(meta["rejected_references"]) == 1


def test_duplicate_reference_ids_do_not_establish_a_match(markdown, extracted):
    extracted["references"][0]["id"] = "02"
    references, offers, meta = validate_sources(extracted["references"], extracted["Pricing"], markdown)
    assert references == [] and offers[0]["reference_ids"] == []
    assert len(meta["rejected_references"]) == 2


@pytest.mark.parametrize("price", [True, "$13.15", -2, float("inf"), float("nan")])
def test_invalid_numeric_prices_are_not_coerced(markdown, extracted, price):
    extracted["Pricing"][0]["price"] = price
    _, offers, meta = validate_sources(extracted["references"], extracted["Pricing"], markdown)
    assert offers[0]["price"] is None
    assert offers[0]["price_text"] == extracted["Pricing"][0]["price_text"]
    assert meta["status"] == "partial"


def test_currency_and_uom_are_never_inferred(markdown, extracted):
    extracted["Pricing"][0].update(currency="$", uom=None)
    _, offers, meta = validate_sources(extracted["references"], extracted["Pricing"], markdown)
    assert offers[0]["currency"] is None and offers[0]["uom"] is None
    assert meta["status"] == "partial"


@pytest.mark.parametrize("value", [None, "not JSON", {}])
def test_failed_extraction_does_not_create_placeholder_prices(markdown, value):
    references, offers, meta = validate_sources(value, value, markdown)
    assert meta["status"] == "error"
    assert references == [] and offers == []


def test_url_collection_preserves_functional_parameters_and_nested_destinations():
    markdown = r'''[Product](https://shop.invalid/a_(b)?variant=1&currency=USD&srsltid=x "Product title")
[Other](<https://other.invalid/a_(b)> "Title")
[ref]: https://ref.invalid/specs
Bare (https://bare.invalid/a_(b)).
Bare escaped \(https://bare-escaped.invalid/a\-b\).
[Escaped](https://escaped.invalid/a\(b\)?a=1\&amp;b=2)
![Icon](https://image.invalid/icon.png)
[Viewer](https://www.google.com/search?ibp=oshop&prds=productid:123)
[Opaque](https://www.google.com/goto?url=opaque)
'''
    assert set(markdown_urls(markdown)) == {
        "https://shop.invalid/a_(b)?variant=1&currency=USD", "https://other.invalid/a_(b)",
        "https://ref.invalid/specs", "https://bare.invalid/a_(b)", "https://bare-escaped.invalid/a-b", "https://escaped.invalid/a(b)?a=1&b=2",
    }
    assert source_url("https://x.invalid/?x=1&currency=USD") == "https://x.invalid/?x=1&currency=USD"


@pytest.fixture
def trial(monkeypatch, tmp_path, markdown, extracted):
    from wrangles import extract
    responses, searches, extractions = {}, [], []

    def search(session, method, url, params, **kwargs):
        assert method == "GET" and url == "https://serpapi.com/search"
        searches.append({key: value for key, value in params.items() if key != "api_key"})
        response = responses.get(params["q"], responses.get("default", markdown))
        http = requests.Response()
        http.status_code, http.encoding = 200, "utf-8"
        http.headers["Content-Type"] = "text/markdown" if isinstance(response, str) else "application/json"
        http._content = (response if isinstance(response, str) else json.dumps(response)).encode("utf-8")
        return http

    class Response:
        ok, status_code, headers = True, 200, {}
        def json(self):
            # The shared compiler maps API-safe property names back to recipe columns.
            payload = {key.replace(" ", "_"): value for key, value in extracted.items()}
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(payload)}]}]}

    def post(**kwargs):
        extractions.append(kwargs["json"])
        if error := responses.get("extract_error"):
            raise error
        return Response()

    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    monkeypatch.setenv("SERPAPI_API_KEY", "offline-search")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-extract")
    monkeypatch.setattr(requests.Session, "request", search)
    monkeypatch.setattr(extract._openai_responses._requests, "post", post)
    for name, value in {"OUTPUT_DIRECTORY": tmp_path, "WRITE_OUTPUTS": False, "EXTRACT_ENABLED": True,
                        "EXTRACT_MODEL": None, "NROWS": 1, "REPLAY_FILE": None,
                        "LOCATION": None, "COUNTRY": None, "LANGUAGE": None}.items():
        monkeypatch.setattr(runner, name, value)
    return searches, extractions, responses


def test_trial_uses_direct_outputs_and_separate_input_identity(trial, extracted, caplog):
    searches, extractions, _ = trial
    row = runner.main().iloc[0]
    assert "mapped nullable: true" not in caplog.text
    expected = (
        "Search for INA NATV6-PP-A INA NATV6-PP-A YOKE TYPE TRACK ROLLERS NATV..-PP FULL COMPLEMENT NEEDL. "
        + QUERY_SECTIONS
    )
    assert searches == [{"engine": "google_ai_mode", "q": expected, "output": "md"}]
    assert len(extractions) == 1
    request = extractions[0]
    assert request["text"]["format"]["strict"] is True and "tools" not in request
    assert request["reasoning"] == {"effort": "low"}
    assert "Build references BEFORE offers" in request["instructions"]
    assert 'ID "00" is reserved' in request["instructions"]
    assert "Example P101 specifications" in request["instructions"]
    schema = request["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert list(properties) == ["Product_Description", "Match_Confidence", "Specifications", "references", "Pricing"]
    assert properties["Match_Confidence"]["enum"] == ["Certain", "Likely", "Uncertain"]
    assert "verbatim" in properties["Product_Description"]["description"]
    assert "no hyperlinks" in properties["Product_Description"]["description"]
    evidence = json.dumps(request["input"], ensure_ascii=False)
    assert "12 VDC" in evidence and "\u03bc" in evidence
    assert "Go to product viewer dialog for this item." not in evidence
    assert "### Results Summary" in row["ai_mode_results_clean"]
    assert GOOGLE_VIEWER not in row["ai_mode_results"].split("### Results Summary")[1]
    assert GOOGLE_VIEWER in row["ai_mode_results_clean"].split("### Links from Product Description")[1]
    assert "search_metadata" not in evidence
    identity = {field: runner.INPUT_ROWS[0][field] for field in ("Mfr", "MPN", "Description")}
    assert row["Input Product Information"] == identity
    model_input = json.loads(request["input"][0]["content"].removeprefix("DATA:\n"))
    assert model_input == {"Input Product Information": identity, "ai_mode_results_clean": row["ai_mode_results_clean"]}
    example_inputs = [json.loads(value) for value in re.findall(r"<input>(.*?)</input>", request["instructions"])]
    assert len(example_inputs) == 2
    for example_input in example_inputs:
        assert example_input.keys() == model_input.keys()
        assert example_input["Input Product Information"].keys() == identity.keys()
    # Unsupported formulas stay intact for semantic extraction.
    assert r"$\frac{1}{2}\text{ in}$" in row["ai_mode_results_clean"]
    assert "$13.15 USD per pack of 10, excluding VAT" in row["ai_mode_results_clean"]
    assert r"$12\text{ VDC}$" in row["ai_mode_results"]
    assert "Example P12Go to product viewer dialog for this item." in row["ai_mode_results"]
    assert row["references"] == [GOOGLE_REFERENCE, *extracted["references"]]
    assert row["Pricing"][0]["reference_ids"] == ["02"]
    assert row["Product Description"] == extracted["Product Description"]
    assert row["Product Description"] in row["ai_mode_results_clean"]
    assert row["Specifications"] == extracted["Specifications"]
    assert "search_ai_extracted" not in row and "ai_mode_result_structured" not in row
    assert row["ai_mode_structured_meta"]["status"] == "complete"
    schema_text = json.dumps(request["text"]["format"]["schema"])
    assert '"number"' in schema_text and '"null"' in schema_text
    assert all(field in schema_text for field in ("currency", "uom", "price_text", "reference_ids", "references"))


def test_trial_does_not_retry_extraction_after_a_transient_failure(trial):
    trial[2]["extract_error"] = requests.exceptions.Timeout("Synthetic extraction timeout")
    row = runner.main().iloc[0]
    assert len(trial[0]) == 1 and len(trial[1]) == 1
    assert row["references"] == [GOOGLE_REFERENCE]
    assert row["Pricing"] == []
    assert row["ai_mode_structured_meta"]["status"] == "error"


def test_trial_without_a_google_viewer_keeps_only_model_references(trial, markdown, extracted):
    trial[2]["default"] = markdown.replace(
        f"[Example P12Go to product viewer dialog for this item.]({GOOGLE_VIEWER})", "Example P12"
    )
    row = runner.main().iloc[0]
    assert row["references"] == extracted["references"]
    assert "google_product_url" not in row["ai_mode_metadata"]


@pytest.mark.parametrize("confidence", ["Certain", "Likely", "Uncertain"])
def test_confidence_is_returned_unchanged_in_its_own_column(trial, extracted, confidence):
    extracted["Match Confidence"] = confidence
    row = runner.main().iloc[0]
    assert row["Match Confidence"] == confidence
    assert row["Product Description"] == extracted["Product Description"]


def test_blank_identity_fields_remain_in_input_dictionary(trial, monkeypatch):
    monkeypatch.setattr(runner, "INPUT_ROWS", [{"ID": 1, "Mfr": "", "MPN": "P12", "Description": ""}])
    row = runner.main().iloc[0]
    assert row["Input Product Information"] == {"Mfr": "", "MPN": "P12", "Description": ""}


def test_trial_exposes_locale_controls(trial, monkeypatch):
    monkeypatch.setattr(runner, "LOCATION", "London, England, United Kingdom")
    monkeypatch.setattr(runner, "COUNTRY", "uk")
    monkeypatch.setattr(runner, "LANGUAGE", "en")
    runner.main()
    assert {key: trial[0][0][key] for key in ("location", "gl", "hl")} == {
        "location": "London, England, United Kingdom", "gl": "uk", "hl": "en",
    }


def test_snapshot_replays_without_search_and_raw_markdown_stays_outside_excel(trial, monkeypatch, tmp_path, markdown):
    monkeypatch.setattr(runner, "WRITE_OUTPUTS", True)
    first = runner.main()
    snapshot, = tmp_path.glob("*.json")
    raw, = tmp_path.glob("*.md")
    assert raw.read_text(encoding="utf-8") == markdown
    assert "raw_response" not in first.iloc[0]["ai_mode_metadata"]
    workbook, = tmp_path.glob("*.xlsx")
    exported = pd.read_excel(workbook).iloc[0]
    assert "reference_ids" in exported["Pricing"] and "12 VDC" in exported["Specifications"]
    monkeypatch.setattr(runner, "REPLAY_FILE", snapshot)
    # The transport metadata can recover a missing display-only query column.
    records = json.loads(snapshot.read_text(encoding="utf-8"))
    records[0].pop("search_query")
    records[0]["search_ai_extracted"] = {"description": "obsolete extraction"}
    records[0]["ai_mode_result_structured"] = {"Product Description": "obsolete display"}
    snapshot.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.delenv("SERPAPI_API_KEY")
    ai_cache.clear()
    second = runner.main()
    assert len(trial[0]) == 1 and len(trial[1]) == 2
    assert first.iloc[0]["ai_mode_results"] == second.iloc[0]["ai_mode_results"]
    assert first.iloc[0]["ai_mode_results_clean"] == second.iloc[0]["ai_mode_results_clean"]
    assert first.iloc[0]["search_query"] == second.iloc[0]["search_query"]
    for column in ("Product Description", "Match Confidence", "Specifications", "Pricing", "references"):
        assert first.iloc[0][column] == second.iloc[0][column]
    assert "search_ai_extracted" not in second and "ai_mode_result_structured" not in second


@pytest.mark.parametrize("state", ["error", "disabled", "blank", "processing"])
def test_trial_skips_unusable_answers(trial, monkeypatch, markdown, state):
    if state == "disabled":
        monkeypatch.setattr(runner, "EXTRACT_ENABLED", False)
        monkeypatch.delenv("OPENAI_API_KEY")
    else:
        response = {"error": "Synthetic failure"} if state == "error" else (
            "---\nsearch_metadata:\n  status: Success\n---\n" if state == "blank" else markdown.replace("status: Success", "status: Processing")
        )
        trial[2]["default"] = response
    row = runner.main().iloc[0]
    assert not trial[1]
    assert row["ai_mode_structured_meta"]["status"] == "skipped"
    assert row["Pricing"] == []
    assert row["references"] == ([GOOGLE_REFERENCE] if state == "disabled" else [])
    assert row["Product Description"] == "" and row["Match Confidence"] == "Uncertain"


def test_mixed_success_and_failure_keep_their_rows(trial, monkeypatch, markdown):
    trial[2]["Search for Example FAILED-2 Failed product. " + QUERY_SECTIONS] = {"error": "Synthetic failure"}
    monkeypatch.setattr(runner, "INPUT_ROWS", [
        {"ID": 14, "Description": "Working product", "Mfr": "Example", "MPN": "OK-1"},
        {"ID": 27, "Description": "Failed product", "Mfr": "Example", "MPN": "FAILED-2"},
    ])
    monkeypatch.setattr(runner, "NROWS", None)
    df = runner.main()
    assert df["ID"].tolist() == [14, 27]
    assert len(trial[1]) == 1
    assert df.iloc[0]["Pricing"][0]["price"] == 13.15
    assert df.iloc[1]["Pricing"] == [] and df.iloc[1]["ai_mode_metadata"]["status"] == "Error"
