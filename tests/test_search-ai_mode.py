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
FIXTURE_SNIPPET_URLS = [
    "https://example.invalid/product?part=P12&variant=1",
    "https://example.invalid/supplier-1",
    "https://example.invalid/supplier-2",
    "https://example.invalid/supplier-3",
]
FIXTURE_UNPRICED_SOURCES = [{f"Source {index}": ""} for index in range(6)] + [{"example.invalid": ""}]


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
        {"Output Voltage": "12 VDC"}, {"Output Current": "5 A"}, {"Output Power": "60 W"},
    ]
    assert all(isinstance(value, dict) and len(value) == 1 for value in compact["Technical Specifications"])
    assert compact["Sources & Pricing"] == FIXTURE_UNPRICED_SOURCES + [
        {"Supplier 1": "$21.00"}, {"Supplier 2": "$22.00"}, {"Supplier 3": "$23.00"},
    ]
    assert compact["references"] == [reference["link"] for reference in provider_response["references"]] + FIXTURE_SNIPPET_URLS
    assert row["result"]["Product Description"][0] == provider_response["text_blocks"][1]
    assert row["markdown"] == provider_response["reconstructed_markdown"]


def test_compact_prices_align_with_reference_order_and_keep_unpriced_sources(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    urls = {name: f"https://example.invalid/{name}" for name in ("maker", "region", "c", "a", "b")}
    response["references"] = [
        {"index": 2, "source": "Maker Ltd", "link": urls["maker"]},
        {"index": 3, "source": "Regional Supply", "link": urls["region"]},
        {"index": 4, "source": "Supplier C", "link": urls["c"]},
    ]
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "list", "list": [
            {"snippet": "Supplier A: $13.18 USD", "snippet_links": [{"link": urls["a"]}]},
            {"snippet": "Supplier B: $18.60 USD", "snippet_links": [{"link": urls["b"]}]},
            {"snippet": "Supplier C: Check site for pricing", "snippet_links": [{"link": urls["c"] + "?utm_source=google"}]},
        ]},
    ]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    compact = row["compact"]
    assert list(zip(compact["Sources & Pricing"], compact["references"], strict=True)) == [
        ({"Maker Ltd": ""}, urls["maker"]),
        ({"Regional Supply": ""}, urls["region"]),
        ({"Supplier C": "Check site for pricing"}, urls["c"]),
        ({"Supplier A": "$13.18 USD"}, urls["a"]),
        ({"Supplier B": "$18.60 USD"}, urls["b"]),
    ]
    assert row["result"]["references"] == response["references"]
    assert row["result"]["Sources & Pricing"] == response["text_blocks"][1:]
    assert row["markdown"] == response["reconstructed_markdown"]


def test_compact_prices_resolve_citation_ids_and_disambiguate_by_source(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["references"] = [
        {"index": 91, "source": "Supplier A", "link": "https://example.invalid/a"},
        {"index": 7, "source": "Supplier B", "link": "https://example.invalid/b"},
    ]
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "list", "list": [
            {"snippet": "Merchant: $20", "reference_indexes": [7]},
            {"snippet": "Supplier A: $10", "reference_indexes": [7, 91]},
            {"snippet": "Unknown: $30", "reference_indexes": [999]},
        ]},
    ]
    ai_mode_provider[0]["product"] = response
    compact = run_ai_mode().iloc[0]["compact"]
    assert list(zip(compact["Sources & Pricing"], compact["references"], strict=True)) == [
        ({"Supplier A": "$10"}, "https://example.invalid/a"),
        ({"Merchant": "$20"}, "https://example.invalid/b"),
        ({"Unknown": "$30"}, ""),
    ]


@pytest.mark.parametrize("ambiguous", [False, True])
def test_compact_prices_only_infer_unique_source_names(ai_mode_provider, provider_response, ambiguous):
    response = deepcopy(provider_response)
    urls = ["https://example.invalid/a"] + (["https://example.invalid/another-a"] if ambiguous else [])
    response["references"] = [{"index": index, "source": "Supplier A", "link": url} for index, url in enumerate(urls)]
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "paragraph", "snippet": "Supplier A: $10"},
    ]
    ai_mode_provider[0]["product"] = response
    compact = run_ai_mode().iloc[0]["compact"]
    assert compact["references"] == urls + ([""] if ambiguous else [])
    assert compact["Sources & Pricing"] == ([{"Supplier A": ""}] * len(urls) if ambiguous else []) + [{"Supplier A": "$10"}]


def test_compact_missing_prices_use_site_names_or_hostnames(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["references"] = [
        {"index": 0, "source": "Maker & Co", "link": "https://maker.invalid/item"},
        {"index": 1, "title": "A product title is not a site name", "link": "https://www.catalog.invalid/item"},
    ]
    response["text_blocks"] = []
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Sources & Pricing"] == [{"Maker & Co": ""}, {"catalog.invalid": ""}]
    assert row["compact"]["references"] == [ref["link"] for ref in response["references"]]
    assert row["result"]["Sources & Pricing"] == []


def test_compact_price_tables_keep_row_links_and_citations(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["references"] = [
        {"index": 7, "source": "Supplier B", "link": "https://example.invalid/b"},
        {"index": 91, "source": "Supplier A", "link": "https://example.invalid/a"},
    ]
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "table", "table": [
            ["Supplier", "Price"],
            [{"snippet": "Supplier A", "snippet_links": [{"link": "https://example.invalid/a?gclid=tracking"}]}, "$10"],
            ["B Resale", {"snippet": "$20", "reference_indexes": [7]}],
        ]},
    ]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert list(zip(row["compact"]["Sources & Pricing"], row["compact"]["references"], strict=True)) == [
        ({"B Resale": "$20"}, "https://example.invalid/b"),
        ({"Supplier A": "$10"}, "https://example.invalid/a"),
    ]
    assert row["result"]["Sources & Pricing"] == response["text_blocks"][1:]


@pytest.mark.parametrize("cell_objects", [False, True])
def test_compact_price_table_omits_link_labels_and_keeps_missing_url_slot(
    ai_mode_provider, provider_response, cell_objects,
):
    response = deepcopy(provider_response)
    response["references"] = [
        {"index": 0, "source": "Google", "link": "https://www.google.com/search?ibp=oshop&prds=productid:123"},
        {"index": 2, "source": "Supplier B", "link": "https://example.invalid/b"},
        {"index": 3, "source": "Supplier C", "link": "https://example.invalid/c"},
    ]
    table = [
        ["Supplier", "Price (USD / GBP approx.)", "Link"],
        ["Supplier A", "$13.00 USD", "Supplier A Product Page"],
        ["Supplier B", "$18.50 USD (£14.50 approx)", "Supplier B Product Page"],
        ["Supplier C", "$16.00 USD (£12.50 GBP)", "Supplier C Online Page"],
    ]
    detailed = [[{"snippet": cell} for cell in cells] for cells in table]
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "table", "table": detailed if cell_objects else table, "detailed": detailed,
         "formatted": [dict(zip(("supplier", "price_usd_gbp_approx", "link"), cells)) for cells in table[1:]]},
    ]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert list(zip(row["compact"]["Sources & Pricing"], row["compact"]["references"], strict=True)) == [
        ({"Supplier B": "$18.50 USD (£14.50 approx)"}, "https://example.invalid/b"),
        ({"Supplier C": "$16.00 USD (£12.50 GBP)"}, "https://example.invalid/c"),
        ({"Supplier A": "$13.00 USD"}, ""),
    ]
    assert row["result"]["Sources & Pricing"] == response["text_blocks"][1:]
    assert row["result"]["references"] == response["references"]
    assert row["markdown"] == response["reconstructed_markdown"]


def test_compact_price_table_retains_currency_headers_and_navigation_url(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["references"] = []
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "table", "table": [
            ["Supplier", "Price (USD)", "Price (GBP)", "Product Link"],
            ["Supplier A", "$13.00", "£10.00", {"snippet": "View Product", "snippet_links": [
                {"text": "View Product", "link": "https://example.invalid/a?utm_source=google"},
            ]}],
        ]},
    ]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Sources & Pricing"] == [{"Supplier A": "Price (USD): $13.00; Price (GBP): £10.00"}]
    assert row["compact"]["references"] == ["https://example.invalid/a"]
    assert row["result"]["Sources & Pricing"] == response["text_blocks"][1:]


def test_compact_multiple_price_sections_and_offers_share_reference_positions(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["references"] = [
        {"index": 0, "source": "Supplier A", "link": "https://example.invalid/a"},
        {"index": 1, "source": "Supplier B", "link": "https://example.invalid/b"},
    ]
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Retail Pricing"},
        {"type": "list", "list": [
            {"snippet": "Supplier A: $10 each", "reference_indexes": [0]},
            {"snippet": "Supplier A: $9 each for 100+", "reference_indexes": [0]},
            {"snippet": "Unlinked: $30"},
        ]},
        {"type": "heading", "snippet": "Bulk Prices"},
        {"type": "paragraph", "snippet": "Supplier B: $20 per pack", "reference_indexes": [1]},
    ]
    ai_mode_provider[0]["product"] = response
    compact = run_ai_mode(query_config=[{"Retail Pricing": "Retail"}, {"Bulk Prices": "Bulk"}]).iloc[0]["compact"]
    assert compact["references"] == ["https://example.invalid/a", "https://example.invalid/a", "https://example.invalid/b", ""]
    assert compact["Retail Pricing"] == [{"Supplier A": "$10 each"}, {"Supplier A": "$9 each for 100+"}, {"Supplier B": ""}, {"Unlinked": "$30"}]
    assert compact["Bulk Prices"] == [{"Supplier A": ""}, {"Supplier A": ""}, {"Supplier B": "$20 per pack"}, {"Unlinked": ""}]


@pytest.mark.parametrize("detail, expected", [
    ("Available for $13.17 USD via Supplier Product Page.", "$13.17 USD"),
    ("$13.17 USD per pack of 10 (minimum order: 2 packs)", "$13.17 USD per pack of 10 (minimum order: 2 packs)"),
    ("From £9.50–£12.00 per unit", "From £9.50–£12.00 per unit"),
    ("€12,50 (approximately $13.17 USD)", "€12,50 (approximately $13.17 USD)"),
    ("$13.17 - Check availability on Supplier", "$13.17"),
    ("Contact for quote; currently out of stock", "Contact for quote; currently out of stock"),
])
@pytest.mark.parametrize("separator", [": ", "： ", " – ", " — "])
def test_compact_prices_keep_currency_and_qualifiers(ai_mode_provider, provider_response, detail, expected, separator):
    response = deepcopy(provider_response)
    response["text_blocks"][5]["list"] = [{
        "snippet": f"Supplier{separator}{detail}",
        "snippet_links": [{"text": "Supplier Product Page", "link": "https://example.invalid/product"}],
    }]
    response["text_blocks"].append({
        "type": "paragraph", "snippet": "If you need an alternative part, let me know.",
    })
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Sources & Pricing"] == FIXTURE_UNPRICED_SOURCES + [{"Supplier": expected}]
    assert len(row["compact"]["Sources & Pricing"]) == len(row["compact"]["references"])
    assert row["result"]["Sources & Pricing"] == response["text_blocks"][5:]


@pytest.mark.parametrize("snippet, label, expected", [
    ("Available at Supplier for $18.57 USD", "Supplier", {"Supplier": "$18.57 USD"}),
    ("Available from Supplier for $10 per pack (minimum order: 2 packs)", "Supplier", {"Supplier": "$10 per pack (minimum order: 2 packs)"}),
    ("Sold by Supplier for £9.50 – £12.00 per unit", "Supplier", {"Supplier": "£9.50 – £12.00 per unit"}),
    ("Offered at Supplier at $1,200.50 USD", "Supplier", {"Supplier": "$1,200.50 USD"}),
    ("Available at Centre for Industrial Parts for $12 USD", "Centre for Industrial Parts", {"Centre for Industrial Parts": "$12 USD"}),
    ("Available at Supplier for Contact for quote", "Supplier", {"Supplier": "Contact for quote"}),
    ("Available at Supplier for $10", None, {"Supplier": "$10"}),
    ("Available from several sources, pricing was not disclosed.", None, {"text": "Available from several sources, pricing was not disclosed."}),
])
def test_compact_prices_parse_supplier_sentences(ai_mode_provider, provider_response, snippet, label, expected):
    response = deepcopy(provider_response)
    response["references"] = []
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "list", "list": [{"snippet": snippet, "snippet_links": [
            {"text": label, "link": "https://example.invalid/supplier"},
        ]}]},
    ]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Sources & Pricing"] == [expected]
    assert row["compact"]["references"] == ["https://example.invalid/supplier"]
    assert row["result"]["Sources & Pricing"] == response["text_blocks"][1:]


def test_compact_fractions_and_supplier_sentences_from_same_response(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    description = {"type": "paragraph", "snippet": "A connecting link for $1/2$-inch chains.", "snippet_latex": ["1/2"]}
    specifications = {"type": "list", "list": [{"snippet": r"Pitch: $1/2$ inch ( $12.7\text{ mm}$)", "snippet_latex": ["1/2", r"12.7\text{ mm}"]}]}
    offers = [("Supplier A", "18.57"), ("Supplier B", "13.16"), ("Supplier C", "12.87")]
    pricing = {"type": "list", "list": [
        {"snippet": rf"Available at {name} for ${amount}\text{{ USD}}$",
         "snippet_links": [{"text": name, "link": f"https://example.invalid/supplier-{index}"}],
         "snippet_latex": [rf"{amount}\text{{ USD}}"]}
        for index, (name, amount) in enumerate(offers)
    ]}
    response["text_blocks"][1], response["text_blocks"][3], response["text_blocks"][5] = description, specifications, pricing
    response["references"] = [{"index": 2, "source": "Supplier A", "link": "https://example.invalid/supplier-0"}]
    response["reconstructed_markdown"] = description["snippet"]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Product Description"] == "A connecting link for 1/2-inch chains."
    assert row["compact"]["Technical Specifications"] == [{"Pitch": "1/2 inch ( 12.7 mm)"}]
    assert row["compact"]["Sources & Pricing"] == [{name: amount + " USD"} for name, amount in offers]
    assert row["compact"]["references"] == [f"https://example.invalid/supplier-{index}" for index in range(3)]
    for heading, block in zip(HEADINGS, (description, specifications, pricing)):
        assert row["result"][heading] == [block]
    assert row["markdown"] == response["reconstructed_markdown"]
    assert wrangles.standardize.clean(row["markdown"], latex_to_text=True) == "A connecting link for 1/2-inch chains."


def test_compact_prices_parse_dashed_supplier_entries(ai_mode_provider, provider_response):
    snippets = [
        "Acorn Industrial Services – $13.18 USD",
        "Klium – $18.60 USD",
        "HVH Industrial Solutions – $6.32 USD",
        "RS Components – Check site for regional pricing",
        "RS - America: $55.98 (bulk tier discounts down to $50.39)",
        "MSC-Direct — Contact for quote",
    ]
    response = deepcopy(provider_response)
    response["text_blocks"][5]["list"] = [{"snippet": snippet} for snippet in snippets]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Sources & Pricing"] == FIXTURE_UNPRICED_SOURCES + [
        {"Acorn Industrial Services": "$13.18 USD"},
        {"Klium": "$18.60 USD"},
        {"HVH Industrial Solutions": "$6.32 USD"},
        {"RS Components": "Check site for regional pricing"},
        {"RS - America": "$55.98 (bulk tier discounts down to $50.39)"},
        {"MSC-Direct": "Contact for quote"},
    ]
    assert row["compact"]["references"] == [ref["link"] for ref in response["references"]] + FIXTURE_SNIPPET_URLS[:1] + [""] * len(snippets)
    assert row["result"]["Sources & Pricing"] == [response["text_blocks"][5]]
    assert row["markdown"] == response["reconstructed_markdown"]


def test_compact_prices_keep_multiple_offers_and_unattributed_text(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    response["text_blocks"][5]["list"] = [
        {"snippet": "Supplier: $13.17 each"},
        {"snippet": "Supplier: $11.00 each for 100+"},
        {"snippet": "No other prices were disclosed."},
        {"snippet": "Supplier:"},
        {"snippet": ": $12.00"},
    ]
    ai_mode_provider[0]["product"] = response
    compact = run_ai_mode().iloc[0]["compact"]
    assert compact["Sources & Pricing"] == FIXTURE_UNPRICED_SOURCES + [
        {"Supplier": "$13.17 each"}, {"Supplier": "$11.00 each for 100+"},
        {"text": "No other prices were disclosed."},
        {"text": "Supplier:"},
        {"text": ": $12.00"},
    ]
    assert compact["references"][-5:] == [""] * 5
    assert len(compact["Sources & Pricing"]) == len(compact["references"])


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


def test_latex_measurements_and_prices_remain_distinct(ai_mode_provider, provider_response):
    response = deepcopy(provider_response)
    specifications = [
        ("Inner Bore Diameter", r"\$6\text{ mm}", "6 mm"),
        ("Outer Diameter", r"\$19\text{ mm}", "19 mm"),
        ("Width / Overall Width", r"\$12\text{ mm}", "12 mm"),
        ("Dynamic Load Rating", r"\$5400\text{ N}", "5400 N"),
        ("Static Load Rating", r"\$8000\text{ N}", "8000 N"),
        ("Custom Quantity", r"\$2\text{ custom units}", "2 custom units"),
        ("Compact Unit", r"\$6\text{mm}", "6mm"),
    ]
    offers = [
        ("Supplier A", r"\$80.98", "$80.98"),
        ("Supplier B", r"\$20.60\text{ USD}", "$20.60 USD"),
        ("Supplier C", r"\$6\text{ per mm}", "$6 per mm"),
    ]
    for index, entries in ((3, specifications), (5, offers)):
        response["text_blocks"][index] = {"type": "list", "list": [
            {"snippet": f"{label}: ${latex}$", "snippet_latex": [latex]}
            for label, latex, _ in entries
        ]}
    response["reconstructed_markdown"] = "\n\n".join(
        f"### {heading}\n\n" + "\n".join(f"- {label}: ${latex}$" for label, latex, _ in entries)
        for heading, entries in zip(HEADINGS[1:], (specifications, offers))
    )
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Technical Specifications"] == [{label: value} for label, _, value in specifications]
    assert row["compact"]["Sources & Pricing"] == FIXTURE_UNPRICED_SOURCES + [{label: value} for label, _, value in offers]
    assert row["result"]["Technical Specifications"] == [response["text_blocks"][3]]
    assert row["result"]["Sources & Pricing"] == [response["text_blocks"][5]]
    assert row["markdown"] == response["reconstructed_markdown"]
    cleaned = wrangles.recipe.run({"wrangles": [{"standardize.clean": {
        "input": "markdown", "output": "clean", "latex_to_text": True,
        "collapse_whitespace": False, "trim": False,
    }}]}, dataframe=pd.DataFrame({"markdown": [row["markdown"]]}))
    assert cleaned.iloc[0]["clean"] == "\n\n".join(
        f"### {heading}\n\n" + "\n".join(f"- {label}: {value}" for label, _, value in entries)
        for heading, entries in zip(HEADINGS[1:], (specifications, offers))
    )


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
        {"text": "Dimensions"}, {"Width": "12 mm"}, {"Voltage": "12 VDC"}, {"Current": "5 A"},
    ]
    assert row["compact"]["Sources & Pricing"] == FIXTURE_UNPRICED_SOURCES + [{"Supplier A": "$13.17 USD; Unit: pack of 10"}]
    assert row["result"]["Technical Specifications"] == [response["text_blocks"][3]]


@pytest.mark.parametrize("text, expected", [
    ("Inner Bore Diameter: 6 mm", {"Inner Bore Diameter": "6 mm"}),
    ("Width：11 mm to 12 mm", {"Width": "11 mm to 12 mm"}),
    ("Bearing Type – Full complement needle roller", {"Bearing Type": "Full complement needle roller"}),
    ("Seal — PP style: three-stage sealing", {"Seal": "PP style: three-stage sealing"}),
    ("Duty cycle: 1:2", {"Duty cycle": "1:2"}),
    ("Part No.: NATV6-PP-A", {"Part No.": "NATV6-PP-A"}),
    ("No confirmed specifications available.", {"text": "No confirmed specifications available."}),
    ("Unspecified:", {"text": "Unspecified:"}),
])
def test_compact_specifications_are_name_value_dictionaries(ai_mode_provider, provider_response, text, expected):
    response = deepcopy(provider_response)
    response["text_blocks"][3] = {"type": "list", "list": [{"snippet": text}, {"snippet": text}]}
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["Technical Specifications"] == [expected, expected]
    assert row["result"]["Technical Specifications"] == [response["text_blocks"][3]]
    assert row["markdown"] == response["reconstructed_markdown"]


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
    assert row["compact"]["references"] == ["https://example.invalid/four", "https://example.invalid/zero"] + FIXTURE_SNIPPET_URLS
    assert row["result"]["references"] == response["references"]


@pytest.mark.parametrize("separator", ["&", "&amp;", "&#38;", "&#x26;", r"\&"])
def test_compact_reference_html_decoding_preserves_query_parameter_names(ai_mode_provider, provider_response, separator):
    response = deepcopy(provider_response)
    url = "https://example.invalid/product?sku=A%20B" + separator + (separator.join([
        "currency=USD", "copy_id=10", "notable=yes", "utm_source=google",
    ]))
    expected = "https://example.invalid/product?sku=A%20B&currency=USD&copy_id=10&notable=yes"
    response["references"] = [{"index": 2, "source": "Supplier", "link": url}]
    response["text_blocks"] = [
        {"type": "heading", "snippet": "Sources & Pricing"},
        {"type": "paragraph", "snippet": "Supplier: $41.00", "snippet_links": [{"text": "Supplier", "link": expected}]},
    ]
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["references"] == [expected]
    assert row["compact"]["Sources & Pricing"] == [{"Supplier": "$41.00"}]
    assert row["result"]["references"] == response["references"]


@pytest.mark.parametrize("provider_references", [False, True])
def test_compact_references_recover_sources_from_inline_links(ai_mode_provider, provider_response, provider_references):
    # The provider may omit references or cite its product viewer, while supplier
    # URLs still appear in snippet_links. Do not invent a viewer-to-merchant match.
    response = deepcopy(provider_response)
    viewer = "https://www.google.com/search?q=product&prds=pvt:hg,productid:123,catalogid:456&ibp=oshop"
    response["text_blocks"][1]["snippet_links"][0]["link"] = viewer
    response["references"] = ([
        {"index": 1, "link": viewer},
        {"index": 4, "link": "https://example.invalid/reference-4"},
    ] if provider_references else [])
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    expected = (["https://example.invalid/reference-4"] if provider_references else [])
    assert row["compact"]["references"] == expected + FIXTURE_SNIPPET_URLS[1:]
    assert row["result"]["references"] == response["references"]
    assert row["result"]["Product Description"][0]["snippet_links"][0]["link"] == viewer
    assert row["markdown"] == response["reconstructed_markdown"]


def test_compact_references_clean_deduplicate_and_visit_nested_sources(ai_mode_provider, provider_response):
    clean_url = "https://example.invalid/p?sku=A%20B&blank=&sku=%2B#details"
    tracked_url = clean_url.replace("#details", "&utm_source=google&srsltid=tracking#details")
    blocks = [
        {"type": "heading", "snippet": "Details"},
        {"type": "list", "list": [{"snippet": "Product", "snippet_links": [{"link": tracked_url}],
            "text_blocks": [{"type": "paragraph", "snippet": "Nested", "snippet_links": [
                {"link": "https://example.invalid/nested?x=1&amp;y=2&gclid=tracking"},
            ]}],
        }]},
        {"type": "table", "table": [["Source", "Details"], [
            {"snippet": "Supplier", "snippet_links": [{"link": r"https://example.invalid/table?sku=A\&fbclid=tracking"}]},
            "Available",
        ]]},
    ]
    response = {**provider_response, "text_blocks": blocks, "references": [
        {"index": 4, "link": tracked_url}, {"index": 1, "link": clean_url},
        {"index": 2, "link": "123456789"}, {"index": 3, "link": None},
    ], "unrelated": {"snippet_links": [{"link": "https://example.invalid/not-a-source"}]}}
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode(query_config=[{"Details": "Details"}], include_raw_response=True).iloc[0]
    assert row["compact"]["references"] == [
        clean_url, "https://example.invalid/nested?x=1&y=2", "https://example.invalid/table?sku=A",
    ]
    assert len(row["result"]["references"]) == 4
    assert [ref["index"] for ref in row["result"]["references"]] == [4, 1, 2, 3]
    assert "utm_source=google" in row["result"]["references"][0]["link"]
    assert row["result"]["raw_response"]["unrelated"] == response["unrelated"]


@pytest.mark.parametrize("url, expected", [
    ("https://www.google.com/search?ibp=oshop&prds=productid:123", []),
    ("https://www.google.co.uk/search?prds=productid:123", []),
    ("https://www.google.de/shopping/product/123", []),
    ("https://support.google.com/example", ["https://support.google.com/example"]),
    ("https://example.invalid/search?prds=123", ["https://example.invalid/search?prds=123"]),
    ("https://google.com.example.invalid/search?prds=123", ["https://google.com.example.invalid/search?prds=123"]),
    ("opaque-product-id", []), ("https://[invalid", []), ("javascript:alert(1)", []),
])
def test_compact_references_omit_viewer_only_or_invalid_links(ai_mode_provider, provider_response, url, expected):
    response = {**provider_response, "text_blocks": [], "references": [{"index": 0, "link": url}]}
    ai_mode_provider[0]["product"] = response
    row = run_ai_mode().iloc[0]
    assert row["compact"]["references"] == expected
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
    from wrangles._search_ai_content import prune_noise
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
    assert row["compact"]["Sources & Pricing"] == FIXTURE_UNPRICED_SOURCES + [
        {"Supplier 1": "$21.00"}, {"Supplier 2": "$22.00"}, {"Supplier 3": "$23.00"},
    ]
    assert row["compact"]["references"] == [ref["link"] for ref in response["references"]] + FIXTURE_SNIPPET_URLS
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


def test_runner_uses_shared_configuration_and_separate_cleanup(monkeypatch, tmp_path, ai_mode_provider, provider_response):
    import run_search_ai_mode as runner

    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    monkeypatch.setattr(runner, "EXTRACT_ENABLED", False)
    monkeypatch.setattr(runner, "WRITE_OUTPUTS", False)
    # Local trial exports can select fixed headings. Test configurable headings
    # independently of those selections, and never write to the trial workbook.
    recipe = yaml.safe_load(runner.RECIPE_FILE.read_text(encoding="utf-8"))
    recipe.pop("write", None)
    recipe_file = tmp_path / "search_ai_mode_test.recipe"
    recipe_file.write_text(yaml.safe_dump(recipe, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(runner, "RECIPE_FILE", recipe_file)
    config = deepcopy(runner.AI_MODE_QUERY)
    config[2] = {"Specification Details": 'Keep literal {{ sample }} and "quoted" instructions.'}
    monkeypatch.setattr(runner, "AI_MODE_QUERY", config)
    monkeypatch.setattr(runner, "NROWS", 1)
    provider_response["text_blocks"][2]["snippet"] = "Specification Details"
    provider_response["text_blocks"][4]["snippet"] = "Pricing & Sources"
    df = runner.main()
    assert len(df) == 1
    assert "__ai_mode_query_config" not in df.columns
    query = ai_mode_provider[1][0]["q"]
    assert query.startswith(config[0]["base_query"])
    assert 'Specification Details: Keep literal {{ sample }} and "quoted" instructions.' in query
    assert "- Product Description:" in query and "- Pricing & Sources:" in query
    assert "for this product:" in query and "> Mfr: INA" in query
    assert "part_codes:" not in query and "query:" not in query
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
    assert compact["Specification Details"][2] == {"Output Voltage": "12 VDC"}
    assert compact["references"] == [reference["link"] for reference in provider_response["references"]] + FIXTURE_SNIPPET_URLS
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
