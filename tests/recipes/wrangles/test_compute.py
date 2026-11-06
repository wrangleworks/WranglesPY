import inspect
import json
from pathlib import Path
import re

import jsonschema
import wrangles
import wrangles.compute as compute
import pandas as pd
import pytest
import yaml


class TestCaseWhen:
    """  
    Test case_when wrangle  
    """

    def test_case_when_basic(self):
        """  
        Test basic case_when functionality with simple conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Match  
                  default: Weak  
                  cases:  
                    - condition: (Score > 0.84) & (Type == 'Code')  
                      value: Strong  
                    - condition: (Score > 0.60) & (Type == 'Code')  
                      value: Moderate  
            """,
            dataframe=pd.DataFrame({
                'Score': [0.9, 0.7, 0.5, 0.85],
                'Type': ['Code', 'Code', 'Code', 'Text']
            })
        )
        assert (
            df['Match'][0] == 'Strong' and
            df['Match'][1] == 'Moderate' and
            df['Match'][2] == 'Weak' and
            df['Match'][3] == 'Weak'
        )

    def test_case_when_where(self):
        """  
        Test case_when with where clause  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: Default  
                  cases:  
                    - condition: col1 > 5  
                      value: High  
                    - condition: col1 > 2  
                      value: Medium  
                  where: col2 == 'A'  
            """,
            dataframe=pd.DataFrame({
                'col1': [1, 6, 3, 8],
                'col2': ['A', 'A', 'B', 'A']
            })
        )
        assert (
            df['Result'][0] == 'Default' and
            df['Result'][1] == 'High' and
            df['Result'][2] == '' and
            df['Result'][3] == 'High'
        )

    def test_case_when_numeric_output(self):
        """  
        Test case_when with numeric output values  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Score  
                  default: 0  
                  cases:  
                    - condition: Grade == 'A'  
                      value: 100  
                    - condition: Grade == 'B'  
                      value: 80  
                    - condition: Grade == 'C'  
                      value: 60  
            """,
            dataframe=pd.DataFrame({
                'Grade': ['A', 'B', 'C', 'D']
            })
        )
        assert (
            df['Score'][0] == 100 and
            df['Score'][1] == 80 and
            df['Score'][2] == 60 and
            df['Score'][3] == 0
        )

    def test_case_when_multiple_conditions(self):
        """  
        Test case_when with complex multiple conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Category  
                  default: Other  
                  cases:  
                    - condition: (Price > 100) & (Stock > 50)  
                      value: Premium High Stock  
                    - condition: (Price > 100) & (Stock <= 50)  
                      value: Premium Low Stock  
                    - condition: (Price <= 100) & (Stock > 50)  
                      value: Budget High Stock  
            """,
            dataframe=pd.DataFrame({
                'Price': [150, 150, 50, 50],
                'Stock': [60, 30, 60, 30]
            })
        )
        assert (
            df['Category'][0] == 'Premium High Stock' and
            df['Category'][1] == 'Premium Low Stock' and
            df['Category'][2] == 'Budget High Stock' and
            df['Category'][3] == 'Other'
        )

    def test_case_when_if_condition(self):
        """  
        Test case_when with if statement  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: 'No'
                  cases:  
                    - condition: value > 5  
                      value: 'Yes'
                  if: ${run_wrangle}  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            }),
            variables={'run_wrangle': True}
        )
        assert df['Result'][0] == 'No' and df['Result'][1] == 'Yes'

    def test_case_when_if_false(self):
        """  
        Test case_when skipped when if condition is false  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: No  
                  cases:  
                    - condition: value > 5  
                      value: Yes  
                  if: ${run_wrangle}  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            }),
            variables={'run_wrangle': False}
        )
        assert 'Result' not in df.columns

    def test_case_when_empty_dataframe(self):
        """  
        Test case_when with empty dataframe  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: Default  
                  cases:  
                    - condition: col1 > 5  
                      value: High  
            """,
            dataframe=pd.DataFrame({'col1': []})
        )
        assert df.empty and 'Result' in df.columns

    def test_case_when_string_conditions(self):
        """  
        Test case_when with string comparison conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Status  
                  default: Unknown  
                  cases:  
                    - condition: Name == 'Alice'  
                      value: Admin  
                    - condition: Name == 'Bob'  
                      value: User  
            """,
            dataframe=pd.DataFrame({
                'Name': ['Alice', 'Bob', 'Charlie']
            })
        )
        assert (
            df['Status'][0] == 'Admin' and
            df['Status'][1] == 'User' and
            df['Status'][2] == 'Unknown'
        )

    def test_case_when_no_default(self):
        """  
        Test case_when without default value (should use None)  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  cases:  
                    - condition: value > 5  
                      value: High  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            })
        )

        assert (
            df['Result'][0] == '' and
            df['Result'][1] == 'High' and
            df['Result'][2] == ''
        )

    def test_case_when_order_matters(self):
        """  
        Test that case_when evaluates conditions in order (first match wins)  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Category  
                  default: Low  
                  cases:  
                    - condition: value > 8  
                      value: Very High  
                    - condition: value > 5  
                      value: High  
                    - condition: value > 2  
                      value: Medium  
            """,
            dataframe=pd.DataFrame({
                'value': [1, 3, 6, 9]
            })
        )
        assert (
            df['Category'][0] == 'Low' and
            df['Category'][1] == 'Medium' and
            df['Category'][2] == 'High' and
            df['Category'][3] == 'Very High'
        )

    def test_case_when_with_variables(self):
        """  
        Test case_when with template variables in conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: Low  
                  cases:  
                    - condition: value > ${threshold}  
                      value: High  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            }),
            variables={'threshold': 5}
        )
        assert df['Result'][0] == 'Low' and df['Result'][1] == 'High'

    def test_case_when_column_with_space(self):
        """
        Test case_when with template variables in conditions 
        where a column name includes a space
            """
        df = pd.DataFrame({
            "My Column": [1, 2, 3],
            "Other Column": [4, 5, 6]
        })
        recipe = """
        wrangles:
            - compute.case_when:
                output: Result
                cases:
                    - condition: My_Column == 1
                      value: "One"
                    - condition: My_Column == 2
                      value: "Two"
                    - condition: My_Column == 3
                      value: "Three"
            """
        result = wrangles.recipe.run(recipe, dataframe=df)

        assert result["Result"].tolist() == ["One", "Two", "Three"]


class TestScoreSearchResults:
    """
    Test the search_score_results wrangle
    """

    score_data = wrangles.recipe.run("""
        read:
          - file:
              name: tests/temp/pra_score_test_data.json
        """)

    @pytest.fixture(autouse=True)
    def mock_code_extraction(self, monkeypatch):
        codes = [
            "085-196-225 M100", "085-196-225 M10", "085-196-225",
            "NATV6-X-PP-A", "NATV6-PP-A", "LBBR 14-2LS", "LBBR-14-2LS",
            "AB-123", "AB123X", "AB123", "ZX900", "6202-2RS",
        ]

        def extract(texts, *args, **kwargs):
            results = []
            for text in texts:
                found = []
                remaining = text.casefold()
                for code in codes:
                    if code.casefold() in remaining:
                        start = remaining.index(code.casefold())
                        found.append(text[start:start + len(code)])
                        remaining = remaining[:start] + " " * len(code) + remaining[start + len(code):]
                results.append(found)
            return results

        monkeypatch.setattr(wrangles.extract, "codes", extract)

    @pytest.mark.parametrize("candidate_column", ["mpns", "part_codes"])
    def test_prose_is_not_code_evidence(self, candidate_column, monkeypatch):
        monkeypatch.setattr(wrangles.extract, "codes", lambda texts, *args, **kwargs: [[] for _ in texts])
        payloads = [{"search_results": [{
            "title": "Brand blank replacement", "snippet": "blank",
            "link": "https://brand.com/products/blank",
        }]}]
        result = compute.score_search_results(
            payloads, suppliers=["Brand"], **{candidate_column: ["blank"]}
        )[0]
        assert result["summary"]["part_code_found"] == "none"
        assert result["summary"]["filtered"] is True
        assert result["part_code_matches"] == []
        assert result["part_code_match_count"] == 0
        assert result["scoring_details"]["part_match_score"] == 0
        assert result["summary"]["brand_found"] is True
        assert "blank" in result["summary"]["matches"]

    @pytest.mark.parametrize("field,original,input_code,level", [
        ("title", "AB-123", "AB-123", "exact"),
        ("snippet", "AB-123", "ab123", "stripped"),
        ("link", "AB-123X", "AB-123", "partial"),
        ("title", "Üß-123", "uss123", "stripped"),
    ])
    @pytest.mark.parametrize("candidate_column,match_type,category", [
        ("mpns", "MPN", "mpn_exact"),
        ("part_codes", "Codes", "other_code_exact"),
    ])
    def test_extracted_evidence_controls_scores(self, field, original, input_code, level,
                                               candidate_column, match_type, category, monkeypatch):
        item = {"title": "Unrelated", "snippet": "", "link": "https://example.com/product"}
        item[field] = f"https://example.com/{original}" if field == "link" else f"Result {original}"
        monkeypatch.setattr(
            wrangles.extract, "codes",
            lambda texts, *args, **kwargs: [[original] if original in text else [] for text in texts],
        )
        result = compute.score_search_results(
            [{"search_results": [item]}], **{candidate_column: [input_code]}
        )[0]
        assert result["summary"]["part_code_found"] == category
        assert result["summary"]["filtered"] is False
        assert result["part_code_match_count"] == 1
        assert result["part_code_matches"] == [{
            "match_type": match_type, "match_level": level,
            "match_source": "url" if field == "link" else field,
            "matched_code": original, "input_code": input_code,
        }]

    def test_extraction_batches_unique_fields_and_retains_field_provenance(self, monkeypatch):
        calls = []

        def extract(texts, *args, **kwargs):
            calls.append(texts)
            return [["AB-123", "AB-123"] if text == "AB-123" else [] for text in texts]

        monkeypatch.setattr(wrangles.extract, "codes", extract)
        payloads = [{"search_results": [
            {"title": "AB-123", "snippet": "AB-123", "link": "https://one.com/item"},
            {"title": "AB-123", "snippet": "AB-123", "link": "https://two.com/item"},
            {"title": "discarded", "link": "https://one.com/item"},
        ]}]
        results = compute.score_search_results(payloads, part_codes=["AB123"])
        assert len(calls) == 1
        assert calls[0].count("AB-123") == 1
        assert "discarded" not in calls[0]
        assert len(results) == 2
        assert all(result["part_code_match_count"] == 2 for result in results)
        assert all(result["part_code_matches"][0]["match_source"] == "title" for result in results)

    def test_extraction_error_propagates(self, monkeypatch):
        def fail(*args, **kwargs):
            raise RuntimeError("extraction unavailable")

        monkeypatch.setattr(wrangles.extract, "codes", fail)
        with pytest.raises(RuntimeError, match="extraction unavailable"):
            compute.score_search_results(
                [{"search_results": [{"title": "AB123", "link": "https://example.com/item"}]}],
                mpns=["AB123"],
            )

    def test_separate_extracted_codes_cannot_form_one_match(self, monkeypatch):
        monkeypatch.setattr(
            wrangles.extract, "codes",
            lambda texts, *args, **kwargs: [["AB12", "CD34"] if text == "AB12 CD34" else [] for text in texts],
        )
        result = compute.score_search_results(
            [{"search_results": [{"title": "AB12 CD34", "link": "https://example.com/item"}]}],
            mpns=["AB12CD34"],
        )[0]
        assert result["summary"]["part_code_found"] == "none"
        assert result["part_code_match_count"] == 0
        assert result["scoring_details"]["part_match_score"] == 0

    def test_no_candidates_skips_extraction(self, monkeypatch):
        def fail(*args, **kwargs):
            pytest.fail("Extraction is unnecessary without candidates")

        monkeypatch.setattr(wrangles.extract, "codes", fail)
        result = compute.score_search_results(
            [{"search_results": [{"title": "Brand blank", "link": "https://brand.com/item"}]}],
            suppliers=["Brand"], must_match_part_code=False,
        )[0]
        assert result["summary"]["brand_found"] is True
        assert result["part_code_match_count"] == 0

    def test_recipe_filter_uses_extracted_evidence(self, monkeypatch):
        monkeypatch.setattr(wrangles.extract, "codes", lambda texts, *args, **kwargs: [[] for _ in texts])
        result = wrangles.recipe._recipe_wrangles.compute.score_search_results(
            pd.DataFrame([{
                "results": [{"search_results": [{"title": "blank", "snippet": "", "link": "https://example.com/blank"}]}],
                "suppliers": [], "codes": ["blank"],
            }]),
            input=["results", "suppliers", "codes"], output=["scored", "formatted"],
        ).iloc[0]
        scored = result["scored"][0]
        assert scored["summary"]["part_match_type"] == "none"
        assert scored["summary"]["part_code_found"] is False
        assert scored["summary"]["filtered"] is True
        assert scored["part_code_matches"] == []
        assert len(result["formatted"]) == 1

    def test_search_score(self):
        """
        Test score_search_results
        """
        recipe = """
        wrangles:
          - compute.score_search_results:
              input:
                - results          
                - suppliers       
                - part_codes
                - MPN
                - Description      
              output: 
                - scored_results
                - Score Summary
              blacklist_keywords: 
                - ebay
              must_match_part_code: false
              mpn_exact_score: 8.0
              part_code_exact_score: 6.0
            """
        df = wrangles.recipe.run(recipe, dataframe=self.score_data)

        assert 'scored_results' in df.columns and 'Score Summary' in df.columns
        assert isinstance(df.iloc[0]['scored_results'], list) and isinstance(df.iloc[0]['scored_results'][0], dict)
        assert isinstance(df.iloc[0]['Score Summary'], list) and isinstance(df.iloc[0]['Score Summary'][0], str)
        assert len(df.iloc[0]['scored_results']) == 4 and len(df.iloc[0]['Score Summary']) == 4
        assert isinstance(df.iloc[0]['scored_results'][0]['part_code_matches'], list)

    def test_part_code_matches_preserve_match_details(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "Genuine AB-123 replacement",
                "snippet": "Compatible code ZX900",
                "link": "https://example.com/products/AB123X",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["AB-123"],
            part_codes=["AB-123", "ZX-900"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [
            {
                "match_type": "MPN",
                "match_level": "exact",
                "match_source": "title",
                "matched_code": "AB-123",
                "input_code": "AB-123",
            },
            {
                "match_type": "Codes",
                "match_level": "stripped",
                "match_source": "snippet",
                "matched_code": "ZX900",
                "input_code": "ZX-900",
            },
        ]

    def test_part_code_matches_remove_redundant_less_specific_matches(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "INA NATV6-PP-A track roller",
                "snippet": "",
                "link": "https://example.com/product",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["NATV6-PP-A"],
            part_codes=["NATV6-PP-A", "NATV6"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "MPN",
            "match_level": "exact",
            "match_source": "title",
            "matched_code": "NATV6-PP-A",
            "input_code": "NATV6-PP-A",
        }]
        assert result["part_code_match_count"] == 3

    def test_part_code_match_inside_larger_code_is_partial(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "INA NATV6-PP-A track roller",
                "snippet": "",
                "link": "https://example.com/product",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            part_codes=["NATV6"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "Codes",
            "match_level": "partial",
            "match_source": "title",
            "matched_code": "NATV6-PP-A",
            "input_code": "NATV6",
        }]

    def test_part_code_matches_prefer_mpn_over_duplicate_code_evidence(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "Genuine AB123 replacement with ZX900",
                "snippet": "",
                "link": "https://example.com/product",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["AB-12"],
            part_codes=["AB123", "ZX900"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [
            {
                "match_type": "MPN",
                "match_level": "partial",
                "match_source": "title",
                "matched_code": "AB123",
                "input_code": "AB-12",
            },
            {
                "match_type": "Codes",
                "match_level": "exact",
                "match_source": "title",
                "matched_code": "ZX900",
                "input_code": "ZX900",
            },
        ]

    def test_part_code_matches_url_case_difference_is_exact(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "INA track roller",
                "snippet": "",
                "link": "https://example.com/products/natv6-pp-a",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["NATV6-PP-A"],
            part_codes=["NATV6-PP-A"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "MPN",
            "match_level": "exact",
            "match_source": "url",
            "matched_code": "natv6-pp-a",
            "input_code": "NATV6-PP-A",
        }]
        assert list(result["part_code_matches"][0]) == [
            "match_type",
            "match_level",
            "match_source",
            "matched_code",
            "input_code",
        ]

    def test_part_code_match_fallback_reclassifies_identical_token_as_exact(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "Product details",
                "snippet": "Olympic Part Code: 085-196-225.",
                "link": "https://example.com/product",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            part_codes=["085-196-225"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "Codes",
            "match_level": "exact",
            "match_source": "snippet",
            "matched_code": "085-196-225",
            "input_code": "085-196-225",
        }]

    @pytest.mark.parametrize("input_code,source_codes,expected_level", [
        ("085-196-225 M10", ["085-196-225 M100"], "partial"),
        ("ABCD", ["XYZAB", "CD1"], None),
        ("ABC", ["ABC"], "exact"),
        ("ABC", ["LMABC123"], None),
    ])
    def test_part_code_match_fallback_respects_complete_code_boundaries(
        self, input_code, source_codes, expected_level
    ):
        matches = compute._find_part_code_matches(
            [input_code], {"Snippet": [(code, compute._compare.normalize_alphanum(code)) for code in source_codes]}, "Codes"
        )

        if expected_level is None:
            assert matches == []
        else:
            assert len(matches) == 1
            assert matches[0]["match_level"] == expected_level
            assert matches[0]["matched_code"] == source_codes[0]

    def test_part_code_matches_keep_only_one_best_mpn(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "NATV6-PP-A track roller",
                "snippet": "Replacement NATV6-PP-A",
                "link": "https://example.com/products/natv6-pp-a",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["NATV6-PP-A"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "MPN",
            "match_level": "exact",
            "match_source": "title",
            "matched_code": "NATV6-PP-A",
            "input_code": "NATV6-PP-A",
        }]

    def test_sentence_punctuation_does_not_hide_stronger_exact_evidence(self):
        matches = compute._find_part_code_matches(
            ["AB-123"], {"Snippet": [("AB-123", "ab123"), ("AB123", "ab123")]}, "Codes"
        )

        assert matches[0]["match_level"] == "exact"
        assert matches[0]["matched_code"] == "AB-123"

    def test_part_code_matches_deduplicate_codes_across_sources(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "NATV6-X-PP-A track roller",
                "snippet": "Replacement NATV6-X-PP-A",
                "link": "https://example.com/products/NATV6-X-PP-A",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            part_codes=["NATV6"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "Codes",
            "match_level": "partial",
            "match_source": "title",
            "matched_code": "NATV6-X-PP-A",
            "input_code": "NATV6",
        }]

    def test_part_code_matches_remove_codes_contained_within_mpn_match(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "Product details",
                "snippet": "Part number 085-196-225 M10",
                "link": "https://example.com/product",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["085-196-225 M10"],
            part_codes=["085-196-225 M10", "225 M10", "085-196-225"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "MPN",
            "match_level": "exact",
            "match_source": "snippet",
            "matched_code": "085-196-225 M10",
            "input_code": "085-196-225 M10",
        }]

    def test_part_code_matches_remove_code_input_contained_within_mpn(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "LBBR 14-2LS linear ball bearing",
                "snippet": "",
                "link": (
                    "https://example.com/lbbr-14-2ls-hv6-ewellix-"
                    "stainless-steel-linear-ball-bearing"
                ),
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["LBBR14-2LS"],
            part_codes=["LBBR14-2LS", "LBBR14"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == [{
            "match_type": "MPN",
            "match_level": "stripped",
            "match_source": "title",
            "matched_code": "LBBR 14-2LS",
            "input_code": "LBBR14-2LS",
        }]
        assert result["part_code_match_count"] == 6

    def test_part_code_matches_is_empty_when_no_code_matches(self):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [{
                "title": "Unrelated product",
                "snippet": "No matching identifiers",
                "link": "https://example.com/products/unrelated",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["AB-123"],
            part_codes=["AB-123"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_matches"] == []
        assert result["part_code_match_count"] == 0

    def test_part_code_match_count_ignores_duplicate_candidates_and_occurrences(self):
        payloads = [{
            "search_results": [{
                "title": "AB-123 replacement for AB-123",
                "link": "https://example.com/product",
            }],
        }]

        result = compute.score_search_results(
            payloads=payloads,
            mpns=["AB-123"],
            part_codes=["AB-123", "AB-123"],
            must_match_part_code=False,
        )[0]

        assert result["part_code_match_count"] == 2
        assert len(result["part_code_matches"]) == 1
        assert result["part_code_matches"][0]["match_type"] == "MPN"

    def test_part_code_matches_are_nested_in_single_recipe_output(self):
        result = wrangles.recipe.run(
            """
            wrangles:
              - compute.score_search_results:
                  input: [results, suppliers, part_codes, MPN, Description]
                  output: scored_results
                  must_match_part_code: false
            """,
            dataframe=self.score_data,
        )

        assert "part_code_matches" not in result.columns
        assert "part_code_match_count" not in result.columns
        assert isinstance(result.iloc[0]["scored_results"][0]["part_code_matches"], list)
        assert isinstance(result.iloc[0]["scored_results"][0]["part_code_match_count"], int)

    @pytest.mark.parametrize("must_match_part_code", [True, False])
    def test_part_code_evidence_controls_scoring_and_filtering(
        self, monkeypatch, must_match_part_code
    ):
        payloads = [{
            "search_metadata": {"query_index": 1},
            "search_results": [
                {
                    "title": "Brand AB-123 bearing",
                    "link": "https://example.com/products/AB-123",
                    "google_rank": 2,
                },
                {
                    "title": "Brand unrelated bearing",
                    "link": "https://example.com/products/other",
                    "google_rank": 1,
                },
            ],
        }]
        kwargs = {
            "suppliers": ["Brand"],
            "mpns": ["AB-123"],
            "part_codes": ["AB-123", "AB12"],
            "must_match_part_code": must_match_part_code,
        }
        with_evidence = compute.score_search_results(payloads, **kwargs)
        assert with_evidence[0]["part_code_match_count"] > 0

        monkeypatch.setattr(compute, "_find_part_code_matches", lambda *args: [])
        without_evidence = compute.score_search_results(payloads, **kwargs)

        assert all(result["scoring_details"]["part_match_score"] == 0 for result in without_evidence)
        assert all(result["summary"]["filtered"] == must_match_part_code for result in without_evidence)

    def test_scoring_schema_documents_every_argument_and_default(self):
        function = wrangles.recipe._recipe_wrangles.compute.score_search_results
        schema = yaml.safe_load(function.__doc__)
        jsonschema.Draft7Validator.check_schema(schema)
        parameters = inspect.signature(function).parameters

        assert set(schema["properties"]) == set(parameters) - {"df"}
        for name, parameter in parameters.items():
            if name == "df":
                continue
            assert schema["properties"][name]["description"]
            if parameter.default is inspect.Parameter.empty:
                assert name in schema["required"]
            else:
                assert schema["properties"][name]["default"] == parameter.default

    def test_scoring_schema_matches_supported_input_and_output_shapes(self):
        schema = yaml.safe_load(
            wrangles.recipe._recipe_wrangles.compute.score_search_results.__doc__
        )
        validator = jsonschema.Draft7Validator(schema)
        inputs = ["results", "suppliers", "part_codes", "MPN", "Description"]

        for count in (3, 4, 5):
            for output in ("scored_results", ["scored_results"], ["scored_results", "Score Summary"]):
                validator.validate({"input": inputs[:count], "output": output})

        invalid_configurations = [
            {"input": inputs[:2], "output": "scored_results"},
            {"input": inputs + ["extra"], "output": "scored_results"},
            {"input": inputs, "output": []},
            {"input": inputs, "output": ["scored_results", "Score Summary", "extra"]},
        ]
        for configuration in invalid_configurations:
            with pytest.raises(jsonschema.ValidationError):
                validator.validate(configuration)

    def test_documented_scoring_example_matches_actual_outputs(self):
        guide = (
            Path(__file__).resolve().parents[3] / "docs" / "search_result_scoring.md"
        ).read_text(encoding="utf-8")
        json_examples = re.findall(r"```json\n(.*?)\n```", guide, re.DOTALL)
        recipe = re.findall(r"```yaml\n(.*?)\n```", guide, re.DOTALL)[0]
        payloads = json.loads(json_examples[0])
        expected_excerpt = json.loads(json_examples[1])
        expected_summary = re.findall(r"```text\n(.*?)\n```", guide, re.DOTALL)[-1]

        configuration = yaml.safe_load(recipe)["wrangles"][0]["compute.score_search_results"]
        schema = yaml.safe_load(
            wrangles.recipe._recipe_wrangles.compute.score_search_results.__doc__
        )
        jsonschema.Draft7Validator(schema).validate(configuration)

        result = wrangles.recipe.run(recipe, dataframe=pd.DataFrame([{
            "results": payloads,
            "suppliers": ["INA"],
            "part_codes": ["NATV6-PP-A", "NATV6"],
            "MPN": "NATV6-PP-A",
            "Description": "NATV6 track roller",
        }]))

        scored = result.iloc[0]["scored_results"][0]
        for field, expected in expected_excerpt.items():
            if isinstance(expected, dict):
                for key, value in expected.items():
                    assert scored[field][key] == value
            else:
                assert scored[field] == expected
        assert result.iloc[0]["Score Summary"][0] == expected_summary
