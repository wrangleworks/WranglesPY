"""Live API coverage for search-result part-code scoring."""

import pandas as pd
import pytest
import wrangles
import wrangles.compute as compute


@pytest.mark.parametrize(
    "url,matched_code",
    [
        (
            "https://www.familyhardware.com/product/stanley-tradecut-15-in-l-blade-9-ppi-bi-material-hand-saw-stht20348/386294",
            "stht20348",
        ),
        (
            "https://WWW.FAMILYHARDWARE.COM/PRODUCT/STANLEY-TRADECUT-15-IN-L-BLADE-9-PPI-BI-MATERIAL-HAND-SAW-STHT20348/386294",
            "STHT20348",
        ),
    ],
    ids=["lowercase-url", "uppercase-url"],
)
def test_extracts_mpn_from_lowercase_and_uppercase_product_urls(url, matched_code):
    """Find STHT20348 in either URL casing and preserve the original result."""
    title = "Stanley Tradecut hand saw"
    snippet = "15-inch blade with a 9 PPI tooth pattern."
    payloads = [{
        "search_metadata": {"query_index": 1},
        "search_results": [{
            "title": title,
            "snippet": snippet,
            "link": url,
            "google_rank": 1,
        }],
    }]

    result = compute.score_search_results(payloads, mpns=["STHT20348"])[0]

    assert result["summary"]["part_code_found"] == "mpn_exact"
    assert result["summary"]["filtered"] is False
    assert result["summary"]["title"] == title
    assert result["summary"]["snippet"] == snippet
    assert result["summary"]["link"] == url
    assert result["part_code_matches"] == [{
        "match_type": "MPN",
        "match_level": "exact",
        "match_source": "url",
        "matched_code": matched_code,
        "input_code": "STHT20348",
    }]


@pytest.mark.parametrize(
    "field,candidate,match_level",
    [
        ("title", "STHT20348", "exact"),
        ("snippet", "stht-20348", "stripped"),
        ("url", "STHT2034", "partial"),
    ],
    ids=["title-exact", "snippet-normalized", "url-partial"],
)
def test_scores_codes_extracted_from_each_result_field(field, candidate, match_level):
    """Match a real saw part number in title, snippet, or URL evidence."""
    title = "Stanley Tradecut hand saw"
    snippet = "Replacement part information."
    url = "https://example.com/products/stanley-tradecut-hand-saw"
    code = "STHT20348"
    if field == "title":
        title = f"{title} {code}"
    elif field == "snippet":
        snippet = f"{snippet} Model {code}."
    else:
        url = f"{url}-{code.lower()}"
    payloads = [{
        "search_metadata": {"query_index": 1},
        "search_results": [{
            "title": title, "snippet": snippet, "link": url, "google_rank": 1,
        }],
    }]

    result = compute.score_search_results(payloads, mpns=[candidate])[0]

    assert result["summary"]["part_code_found"] == "mpn_exact"
    assert result["summary"]["filtered"] is False
    matched_code = code.lower() if field == "url" else code
    assert result["part_code_matches"] == [{
        "match_type": "MPN",
        "match_level": match_level,
        "match_source": field,
        "matched_code": matched_code,
        "input_code": candidate,
    }]


@pytest.mark.parametrize("candidate_column", ["mpns", "part_codes"])
def test_does_not_match_blank_in_product_prose(candidate_column):
    """Prose containing blank is context, not extracted part-code evidence."""
    payloads = [{
        "search_metadata": {"query_index": 1},
        "search_results": [{
            "title": "Product details",
            "snippet": "The product information is blank while the listing is updated.",
            "link": "https://example.com/products/current-stock",
            "google_rank": 1,
        }],
    }]

    result = compute.score_search_results(
        payloads, **{candidate_column: ["blank"]}
    )[0]

    assert result["summary"]["part_code_found"] == "none"
    assert result["summary"]["filtered"] is True
    assert result["scoring_details"]["part_match_score"] == 0
    assert "blank" in result["summary"]["matches"]
    assert result["part_code_matches"] == []
    assert result["part_code_match_count"] == 0


def test_recipe_reports_reduced_evidence_and_filters_by_extracted_codes():
    """Run the scoring recipe on search results and inspect its output columns."""
    url = (
        "https://www.familyhardware.com/product/stanley-tradecut-15-in-l-"
        "blade-9-ppi-bi-material-hand-saw-stht20348/386294"
    )
    payloads = [{
        "search_metadata": {"query_index": 1, "query": "Stanley STHT20348"},
        "search_results": [{
            "title": "Stanley Tradecut hand saw STHT20348",
            "snippet": "Replacement model STHT20348.",
            "link": url,
            "google_rank": 1,
        }],
    }]
    dataframe = pd.DataFrame([{
        "results": payloads,
        "suppliers": ["Stanley"],
        "part_codes": ["STHT20348"],
        "MPN": "STHT20348",
        "Description": "Stanley Tradecut hand saw",
    }])
    recipe = """
    wrangles:
      - compute.score_search_results:
          input: [results, suppliers, part_codes, MPN, Description]
          output: [scored, formatted]
          must_match_part_code: true
    """

    result = wrangles.recipe.run(recipe, dataframe=dataframe).iloc[0]
    scored = result["scored"][0]

    assert result["formatted"]
    assert scored["summary"]["part_match_type"] == "mpn_exact"
    assert scored["summary"]["part_code_found"] is True
    assert scored["summary"]["filtered"] is False
    assert scored["part_code_match_count"] == 6
    assert scored["part_code_matches"] == [{
        "match_type": "MPN",
        "match_level": "exact",
        "match_source": "title",
        "matched_code": "STHT20348",
        "input_code": "STHT20348",
    }]
