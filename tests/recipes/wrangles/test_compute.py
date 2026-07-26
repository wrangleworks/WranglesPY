import wrangles
import wrangles.compute as compute
import pandas as pd


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
