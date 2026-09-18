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
        "output": ["compact", "result", "markdown"] if output is None else output,
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


def test_compact_result_contains_core_sections_and_reference_urls(ai_mode_provider, provider_response):
    row = run_ai_mode().iloc[0]
    compact = row["compact"]
    assert list(compact) == HEADINGS + ["references"]
    assert compact["Product Description"] == "The Example Power P12 supplies 12 VDC."
    assert len(compact["Technical Specifications"]) == 12
    assert compact["Technical Specifications"][2:5] == [
        "Output Voltage: 12 VDC", "Output Current: 5 A", "Output Power: 60 W",
    ]
    assert all(isinstance(value, str) for value in compact["Technical Specifications"])
    assert compact["Sources & Pricing"] == [
        {"Supplier 1": "$21.00"}, {"Supplier 2": "$22.00"}, {"Supplier 3": "$23.00"},
    ]
    assert compact["references"] == [reference["link"] for reference in provider_response["references"]]
    assert row["result"]["Product Description"][0] == provider_response["text_blocks"][1]
    assert row["markdown"] == provider_response["reconstructed_markdown"]


@pytest.mark.parametrize("detail, expected", [
    ("Available for $13.17 USD via Supplier Product Page.", "$13.17 USD"),
    ("$13.17 USD per pack of 10 (minimum order: 2 packs)", "$13.17 USD per pack of 10 (minimum order: 2 packs)"),
    ("From £9.50–£12.00 per unit", "From £9.50–£12.00 per unit"),
    ("€12,50 (approximately $13.17 USD)", "€12,50 (approximately $13.17 USD)"),
    ("$13.17 - Check availability on Supplier", "$13.17"),
    ("Contact for quote; currently out of stock", "Contact for quote; currently out of stock"),
])
def test_compact_prices_keep_currency_and_qualifiers(ai_mode_provider, provider_response, detail, expected):
    response = deepcopy(provider_response)
    response["text_blocks"][5]["list"] = [{
        "snippet": f"Supplier: {detail}",
        "snippet_links": [{"text": "Supplier Product Page", "link": "https://example.invalid/product"}],
    }]
    response["text_blocks"].append({
        "type": "paragraph", "snippet": "If you need an alternative part, let me know.",
    })
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Sources & Pricing"] == [{"Supplier": expected}]
    assert row["result"]["Sources & Pricing"] == response["text_blocks"][5:]


def test_compact_prices_keep_multiple_offers_and_unattributed_text(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["text_blocks"][5]["list"] = [
        {"snippet": "Supplier: $13.17 each"},
        {"snippet": "Supplier: $11.00 each for 100+"},
        {"snippet": "No other prices were disclosed."},
    ]
    ai_mode_provider[0]["product"] = response
    assert run_ai_mode().iloc[0]["compact"]["Sources & Pricing"] == [
        {"Supplier": "$13.17 each"}, {"Supplier": "$11.00 each for 100+"},
        "No other prices were disclosed.",
    ]


def test_compact_text_removes_links_and_cleans_units_and_unicode(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    snippet = (
        r"The [P12Go to product viewer dialog for this item.](https://example.invalid/part(a)?q=1) "
        r"supports healthcare \u0026 ITE at $12\text{ VDC}$. "
        r"<a href=\"https://example.invalid/datasheet\">Datasheet</a>"
    )
    response["text_blocks"][1]["snippet"] = snippet
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Product Description"] == "The P12 supports healthcare & ITE at 12 VDC. Datasheet"
    assert row["result"]["Product Description"][0]["snippet"] == snippet


def test_compact_nested_lists_and_tables_are_shallow(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["text_blocks"][3] = {"type": "list", "list": [{
        "snippet": "Dimensions",
        "list": [{"snippet": "Width: 12 mm"}],
        "text_blocks": [{"type": "table", "table": [
            ["Specification", "Value"], ["Voltage", r"$12\text{ VDC}$"], ["Current", r"$5\text{ A}$"],
        ]}],
    }]}
    response["text_blocks"][5] = {"type": "table", "table": [
        ["Supplier", "Price", "Unit"], ["Supplier A", "$13.17 USD", "pack of 10"],
    ]}
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Technical Specifications"] == [
        "Dimensions", "Width: 12 mm", "Voltage: 12 VDC", "Current: 5 A",
    ]
    assert row["compact"]["Sources & Pricing"] == [{"Supplier A": "$13.17 USD; Unit: pack of 10"}]
    assert row["result"]["Technical Specifications"] == [response["text_blocks"][3]]


def test_compact_references_omit_missing_urls_and_keep_provider_order(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["references"] = [
        {"index": 4, "link": "https://example.invalid/four"},
        {"index": 1, "title": "No link"},
        {"index": 0, "link": "https://example.invalid/zero"},
        {"index": 3, "link": None},
    ]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["references"] == ["https://example.invalid/four", "https://example.invalid/zero"]
    assert row["result"]["references"] == response["references"]


@pytest.mark.parametrize("original, expected", [
    ("https://example.invalid/p?srsltid=tracking", "https://example.invalid/p"),
    ("https://example.invalid/p?srsltid=tracking&sku=A", "https://example.invalid/p?sku=A"),
    ("https://example.invalid/p?sku=A&srsltid=tracking", "https://example.invalid/p?sku=A"),
    ("https://example.invalid/p?x=a%20b&srsltid=one&blank=&x=%2B&SRSltid=two#part", "https://example.invalid/p?x=a%20b&blank=&x=%2B#part"),
    ("https://example.invalid/p?%73rsltid=tracking&utm_source=catalog&gclid=kept", "https://example.invalid/p?utm_source=catalog&gclid=kept"),
    ("https://example.invalid/p?srsltid=tracking&amp;sku=A", "https://example.invalid/p?sku=A"),
    (r"https://example.invalid/p?sku=A\&srsltid=tracking\&q=2", r"https://example.invalid/p?sku=A\&q=2"),
    ("[Source](https://example.invalid/part(a)?srsltid=tracking).", "[Source](https://example.invalid/part(a))."),
    ("https://example.invalid/p?sku=A&empty=&sku=B#srsltid=not-a-query", "https://example.invalid/p?sku=A&empty=&sku=B#srsltid=not-a-query"),
])
def test_srsltid_filter_preserves_other_url_content(original, expected):
    from wrangles._ai_mode_content import prune_noise
    assert prune_noise(original) == expected


@pytest.mark.parametrize("original, expected", [
    ("", ""),
    ("https://example.invalid/p", "example.invalid/p"),
    ("https://example.invalid/p?x=a%20b&srsltid=t&utm_source=catalog&blank=#part", "example.invalid/p?x=a+b&blank=#part"),
    ("http://example.invalid/p?x=%2B&amp;gclid=t", "example.invalid/p?x=%2B"),
])
def test_shared_link_sanitizer_defaults_remain_compatible(original, expected):
    from wrangles.web import clean_link
    assert clean_link(original) == expected


def test_complete_noise_filter_is_recursive_and_markdown_stays_raw(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    tracked = "https://example.invalid/product?sku=P12&srsltid=tracking#details"
    clean_url = "https://example.invalid/product?sku=P12#details"
    response["text_blocks"][1]["snippet_links"][0].update({
        "link": tracked, "source_icon": "data:image/png;base64,synthetic", "thumbnail": "https://example.invalid/thumb",
    })
    response["text_blocks"][3]["list"][0].update({
        "thumbnail": {"large": "https://example.invalid/large"},
        "thumbnail_width": 100,
    })
    response["references"][0].update({"link": tracked, "source_icon": "icon", "thumbnail": "thumb"})
    response["reconstructed_markdown"] = f"[Product]({tracked})"
    ai_mode_provider[0]["product"] = response
    original = deepcopy(response)
    row = run_ai_mode(include_raw_response=True).iloc[0]
    complete = row["result"]
    assert complete["Product Description"][0]["snippet_links"][0] == {
        "text": provider_response["text_blocks"][1]["snippet_links"][0]["text"], "link": clean_url,
    }
    assert complete["Technical Specifications"][0]["list"][0]["thumbnail_width"] == 100
    assert "thumbnail" not in complete["Technical Specifications"][0]["list"][0]
    assert row["compact"]["references"][0] == clean_url
    assert complete["references"][0]["link"] == clean_url
    assert complete["references"][0]["index"] == 0
    assert "source_icon" not in complete["references"][0]
    assert "thumbnail" not in complete["references"][0]
    assert "srsltid=" not in json.dumps(complete)
    assert "source_icon" not in json.dumps(complete["raw_response"])
    assert complete["raw_response"]["reconstructed_markdown"] == f"[Product]({clean_url})"
    assert row["markdown"] == original["reconstructed_markdown"]
    assert response == original


def test_public_search_namespace_and_ordered_batch(ai_mode_provider):
    assert wrangles.search.__name__ == "wrangles.search"
    assert recipe_search._search_core is wrangles.search
    scalar = wrangles.search.ai_mode(" first ", QUERY_CONFIG)
    assert scalar["ai_mode_result_complete"]["meta_data"]["query"] == "first"
    results = wrangles.search.ai_mode(["first", "second"], QUERY_CONFIG, threads=2)
    assert [r["ai_mode_result_complete"]["meta_data"]["query"] for r in results] == ["first", "second"]
    assert [r["ai_mode_result_complete"]["meta_data"]["query_index"] for r in results] == [1, 2]
    assert results[0] == scalar


@pytest.mark.parametrize("output", ["result", ["result"]])
def test_single_output_is_a_dictionary(ai_mode_provider, output):
    df = run_ai_mode(output=output)
    assert isinstance(df.iloc[0]["result"], dict)
    assert isinstance(df.iloc[0]["result"]["Product Description"], str)
    assert "meta_data" not in df.iloc[0]["result"]
    assert "markdown" not in df.columns


def test_two_outputs_are_compact_then_complete(ai_mode_provider, provider_response):
    df = run_ai_mode(output=["compact", "complete"])
    assert isinstance(df.iloc[0]["compact"]["Product Description"], str)
    assert df.iloc[0]["complete"]["Product Description"] == [provider_response["text_blocks"][1]]
    assert "markdown" not in df.columns


@pytest.mark.parametrize("output", [[], ["a", "b", "c", "d"], ["a", "a"], ["a", 1], ""])
def test_invalid_outputs_fail_before_search(ai_mode_provider, output):
    with pytest.raises(ValueError, match="1, 2 or 3 distinct output columns"):
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


@pytest.mark.parametrize("inline_description", [False, True])
def test_paragraph_section_labels_populate_all_outputs(ai_mode_provider, provider_response, inline_description):
    # Google can put the description after a colon and emit later labels as paragraphs.
    response = deepcopy(provider_response)
    for index, heading in enumerate(HEADINGS):
        response["text_blocks"][index * 2] = {"type": "paragraph", "snippet": f"{heading}:"}
    if inline_description:
        response["text_blocks"][1]["snippet"] = "Product Description: " + response["text_blocks"][1]["snippet"]
        response["text_blocks"].pop(0)
    ai_mode_provider[0]["product"] = response

    row = run_ai_mode(include_raw_response=True).iloc[0]
    result = row["result"]
    for index, heading in enumerate(HEADINGS):
        assert result[heading] == [provider_response["text_blocks"][index * 2 + 1]]
    assert row["compact"]["Product Description"] == "The Example Power P12 supplies 12 VDC."
    assert len(row["compact"]["Technical Specifications"]) == 12
    assert row["compact"]["Sources & Pricing"] == [
        {"Supplier 1": "$21.00"}, {"Supplier 2": "$22.00"}, {"Supplier 3": "$23.00"},
    ]
    assert row["compact"]["references"] == [ref["link"] for ref in response["references"]]
    assert result["references"] == response["references"]
    assert result["raw_response"] == response
    assert row["markdown"] == response["reconstructed_markdown"]
    meta = result["meta_data"]
    assert meta["missing_headings"] == meta["inferred_headings"] == []
    assert meta["unsectioned_text_blocks"] == meta["warnings"] == []
    assert meta["parse_status"] == "complete"


@pytest.mark.parametrize("block_type, label, body", [
    ("heading", " product   DESCRIPTION: ", ""),
    ("paragraph", " product   DESCRIPTION ", ""),
    ("paragraph", " product\tDESCRIPTION :\nBody text: 12 mm.", "Body text: 12 mm."),
    ("paragraph", "Product Description：Body text.", "Body text."),
    ("heading", "Product Description: Body text.", "Body text."),
])
def test_explicit_section_labels_allow_spacing_and_colons(ai_mode_provider, provider_response, block_type, label, body):
    response = deepcopy(provider_response)
    response["text_blocks"][0] = {"type": block_type, "snippet": label}
    ai_mode_provider[0]["product"] = response
    result = run_ai_mode().iloc[0]["result"]
    expected = ([{"type": "paragraph", "snippet": body}] if body else [])
    assert result["Product Description"] == expected + [provider_response["text_blocks"][1]]
    assert result["meta_data"]["parse_status"] == "complete"


def test_section_labels_preserve_attached_nested_content(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["text_blocks"][3].update(type="paragraph", snippet="Technical Specifications:")
    response["text_blocks"].pop(2)
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["result"]["Technical Specifications"] == [{**response["text_blocks"][2], "snippet": ""}]
    assert len(row["compact"]["Technical Specifications"]) == 12
    assert row["result"]["meta_data"]["parse_status"] == "complete"


def test_section_labels_do_not_match_embedded_mentions_or_nested_items(ai_mode_provider, provider_response):
    blocks = [
        {"type": "paragraph", "snippet": "See Technical Specifications: below."},
        {"type": "paragraph", "snippet": "Technical Specifications include these values."},
        {"type": "paragraph", "snippet": "Technical Specifications Summary: 12 mm."},
        {"type": "paragraph", "snippet": "Technical Specifications12 mm"},
        {"type": "list", "snippet": "Technical Specifications:", "list": [
            {"snippet": "Sources & Pricing: should stay in this list.", "text_blocks": [
                {"type": "heading", "snippet": "Sources & Pricing"},
            ]},
        ]},
    ]
    response = deepcopy(provider_response)
    response["text_blocks"][2:2] = blocks
    ai_mode_provider[0]["product"] = response
    result = run_ai_mode().iloc[0]["result"]
    assert result["Product Description"] == [provider_response["text_blocks"][1], *blocks]
    assert result["Technical Specifications"] == [provider_response["text_blocks"][3]]
    assert result["Sources & Pricing"] == [provider_response["text_blocks"][5]]
    assert result["meta_data"]["parse_status"] == "complete"


def test_custom_section_labels_with_colons_use_full_name(ai_mode_provider, provider_response):
    config = [{"Details": "Overview"}, {"Details: Dimensions": "Measurements"}]
    blocks = [
        {"type": "paragraph", "snippet": "Details: First description."},
        {"type": "paragraph", "snippet": "Details: Dimensions: Width: 12 mm."},
        {"type": "paragraph", "snippet": "Details: Second description."},
    ]
    ai_mode_provider[0]["product"] = {**provider_response, "text_blocks": blocks}
    row = run_ai_mode(query_config=config).iloc[0]
    assert row["compact"]["Details"] == "First description.\n\nSecond description."
    assert row["compact"]["Details: Dimensions"] == "Width: 12 mm."
    meta = row["result"]["meta_data"]
    assert meta["missing_headings"] == []
    assert meta["repeated_headings"] == ["Details"]
    assert meta["warnings"] == ["repeated_heading: Details"]


@pytest.mark.parametrize("first_heading", ["Product Description", "Overview"])
@pytest.mark.parametrize("heading_type", ["heading", "paragraph"])
def test_missing_first_heading_recovers_leading_paragraphs(ai_mode_provider, provider_response, first_heading, heading_type):
    # Google sometimes starts with the description and labels only later sections.
    response = deepcopy(provider_response)
    for block in response["text_blocks"]:
        if block["type"] == "heading":
            block["type"] = heading_type
    response["text_blocks"] = response["text_blocks"][1:]
    continuation = {"type": "paragraph", "snippet": "Additional product features."}
    response["text_blocks"].insert(1, continuation)
    response["references"] = []
    response["text_blocks"][0].pop("reference_indexes")
    response["text_blocks"][3].pop("reference_indexes")
    ai_mode_provider[0]["product"] = response
    config = deepcopy(QUERY_CONFIG)
    config[1] = {first_heading: "1-3 sentences including the name and key features."}

    row = run_ai_mode(query_config=config, include_raw_response=True).iloc[0]
    result = row["result"]
    assert result[first_heading] == response["text_blocks"][:2]
    assert result["Technical Specifications"] == [response["text_blocks"][3]]
    assert result["Sources & Pricing"] == [response["text_blocks"][5]]
    assert result["references"] == []
    assert row["markdown"] == response["reconstructed_markdown"]
    assert result["raw_response"] == response
    meta = result["meta_data"]
    assert meta["missing_headings"] == []
    assert meta["inferred_headings"] == [first_heading]
    assert meta["unsectioned_text_blocks"] == []
    assert meta["warnings"] == [f"inferred_heading: {first_heading}"]
    assert meta["parse_status"] == "partial"


@pytest.mark.parametrize("case", [
    "explicit-first-heading", "explicit-first-heading-late", "unknown-heading-first", "two-missing-headings",
    "no-headings", "list-preamble", "malformed-preamble", "processing-response",
])
def test_first_heading_fallback_keeps_ambiguous_preambles_in_diagnostics(ai_mode_provider, provider_response, case):
    preamble = [{"type": "paragraph", "snippet": "Opening text."}]
    remaining = deepcopy(provider_response["text_blocks"][2:])
    status = "Success"
    if case == "explicit-first-heading":
        remaining = deepcopy(provider_response["text_blocks"])
    elif case == "explicit-first-heading-late":
        remaining.extend(deepcopy(provider_response["text_blocks"][:2]))
    elif case == "unknown-heading-first":
        remaining.insert(0, {"type": "heading", "snippet": "Unrequested Heading"})
    elif case == "two-missing-headings":
        remaining = remaining[2:]
    elif case == "no-headings":
        remaining = []
    elif case == "list-preamble":
        preamble = [{"type": "list", "list": [{"snippet": "Unclassified content"}]}]
    elif case == "malformed-preamble":
        preamble.append("Malformed block")
    elif case == "processing-response":
        status = "Processing"
    response = {**provider_response, "search_metadata": {"status": status},
                "text_blocks": preamble + remaining}
    ai_mode_provider[0]["product"] = response

    result = run_ai_mode().iloc[0]["result"]
    assert result["meta_data"]["unsectioned_text_blocks"] == preamble
    assert result["meta_data"]["inferred_headings"] == []
    expected = [provider_response["text_blocks"][1]] if case.startswith("explicit-first-heading") else []
    assert result["Product Description"] == expected


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
    assert empty.empty and list(empty.columns) == ["query", "ID", "compact", "result", "markdown"]
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
    result = df.iloc[0]["ai_mode_result_complete"]
    assert result["Specification Details"] == [provider_response["text_blocks"][3]]
    assert result["meta_data"]["parse_status"] == "complete"
    assert df.iloc[0]["ai_mode_markdown"] == provider_response["reconstructed_markdown"]
    compact = df.iloc[0]["ai_mode_result"]
    assert isinstance(compact["Product Description"], str)
    assert len(compact["Specification Details"]) == 12
    assert compact["references"] == [reference["link"] for reference in provider_response["references"]]
    outputs = ["ai_mode_result", "ai_mode_result_complete", "ai_mode_markdown"]
    positions = [df.columns.get_loc(column) for column in outputs]
    assert positions == sorted(positions)
    clean = df.iloc[0]["ai_mode_markdown_clean"]
    assert "Go to product viewer dialog" not in clean
    assert "[Example Power P12](https://example.invalid/product?part=P12&variant=1)" in clean
    assert "12 VDC" in clean and "Healthcare & ITE" in clean
    assert "\\text" in result["Product Description"][0]["snippet"]


def test_ai_mode_schema_matches_three_output_contract():
    schema = yaml.safe_load(recipe_search.ai_mode.__doc__)
    jsonschema.Draft7Validator.check_schema(schema)
    valid = {"queries": "query", "id": "ID", "query_config": QUERY_CONFIG,
             "output": ["compact", "complete", "markdown"], "include_raw_response": True}
    jsonschema.validate(valid, schema)
    for change in ({"output": ["a", "b", "c", "d"]}, {"query_config": [{"a": "x", "b": "y"}]},
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
