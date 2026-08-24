import wrangles
import pandas as pd
import pytest


class TestFindLinks:
    """
    Test search.find_links functionality
    """

    def test_search_single_query(self):
        """
        Test basic single query search
        """
        
        data = pd.DataFrame({
            'query': ['wireless headphones'],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                id: ID
                output: results
                api_key: ${SERPAPI_API_KEY}
                n_results: 5
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert 'results' in df.columns
        assert len(df.iloc[0]['results'][0]['search_results']) == 5
        assert 'link' in df.iloc[0]['results'][0]['search_results'][0]
        assert 'snippet' in df.iloc[0]['results'][0]['search_results'][0]
        assert 'google_rank' in df.iloc[0]['results'][0]['search_results'][0]
    
    def test_search_multiple_queries(self):
        """
        Test search with a list of queries
        """
        
        data = pd.DataFrame({
            'query': [['wireless headphones', 'phone charger', 'bluetooth speaker']],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                id: ID
                output: results
                api_key: ${SERPAPI_API_KEY}
                n_results: 3
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df['results'][0][0]['search_results']) == 3 # This check should be updated once results for each query are returned. Possibly add more checks too
    
    def test_search_with_n_results(self):
        """
        Test search with different n_results values
        """
        
        data = pd.DataFrame({
            'query': ['wireless headphones'],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 7
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df['results'][0][0]['search_results']) == 7
    
    ##### This currently does not work, must have the same number of inputs and outputs. #####
    ##### Does the function need to be updated to allow multiple in to single out? #####
    # def test_search_multiple_input_columns(self):
    #     """
    #     Test search with multiple input columns (concatenated)
    #     """
        
    #     data = pd.DataFrame({
    #         'col1': ['wireless headphones'],
    #         'col2': ['phone charger'],
    #         'ID': [1]
    #     })
        
    #     recipe = """
    #     wrangles:
    #         - search.find_links:
    #             queries:
    #                 - col1
    #                 - col2
    #             output: results
    #             id: ID
    #             api_key: ${SERPAPI_API_KEY}
    #             n_results: 3
    #     """
        
    #     df = wrangles.recipe.run(recipe, dataframe=data)
        
    #     assert 'results1' in df.columns and 'results2' in df.columns
    #     assert len(df['results1'][0][0]['search_results']) == 3
    #     assert len(df['results2'][0][0]['search_results']) == 3
    
    def test_search_multiple_output_columns(self):
        """
        Test search with multiple input/output columns
        """
        data = pd.DataFrame({
            'col1': ['wireless headphones'],
            'col2': ['phone charger'],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries:
                    - col1
                    - col2
                output:
                    - results1
                    - results2
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 3
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert 'results1' in df.columns and 'results2' in df.columns
        assert len(df['results1'][0][0]['search_results']) == 3
        assert len(df['results2'][0][0]['search_results']) == 3
    
    def test_search_where_clause(self):
        """
        Test search.find_links using where clause
        """
        
        data = pd.DataFrame({
            'query': ['wireless headphones', 'phone charger', 'bluetooth speaker'],
            'priority': [1, 5, 3],
            'ID': [1, 2, 3]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 2
                where: priority > 2
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert df.iloc[0]['results'] == ""  # priority = 1, not processed
        assert len(df.iloc[1]['results'][0]['search_results']) == 2  # priority = 5, processed
        assert len(df.iloc[2]['results'][0]['search_results']) == 2  # priority = 3, processed
    
    def test_search_empty_input(self):
        """
        Test search with empty input
        """
        
        data = pd.DataFrame({
            'query': ['', 'wireless headphones', None],
            'ID': [1, 2, 3]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 3
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        ##### This is the current output which will soon be updated to output empty dicts #####
        # Empty and None queries should return empty results
        assert df.iloc[0]['results'] == []
        assert len(df.iloc[1]['results'][0]['search_results']) == 3
        assert df.iloc[2]['results'] == []
    
    ##### This parameter doesn't actually do anything #####
    def test_search_include_prices(self):
        """
        Test search with include_prices parameter
        """
        
        data = pd.DataFrame({
            'query': ['wireless headphones'],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 3
                include_prices: true
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert 'pricing' in df.iloc[0]['results'][0]['search_results'][0]

    def test_search_with_country(self):
        """
        Test search with country parameter
        """
        
        data = pd.DataFrame({
            'query': ['wireless headphones'],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 3
                country: uk
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df.iloc[0]['results'][0]['search_results']) == 3

    def test_search_with_language(self):
        """
        Test search with language parameter
        """
        
        data = pd.DataFrame({
            'query': ['wireless headphones'],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 3
                language: es
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df.iloc[0]['results'][0]['search_results']) == 3
    
    ##### api_key is not actually required at the moment and is read in in serp_api.py #####
    # def test_search_missing_api_key(self):
    #     """
    #     Test that missing API key raises error
    #     """
    #     data = pd.DataFrame({
    #         'query': ['wireless headphones'],
    #         'ID': [1]
    #     })
        
    #     recipe = """
    #     wrangles:
    #         - search.find_links:
    #             queries: query
    #             output: results
    #             id: ID
    #             n_results: 3
    #     """
        
    #     with pytest.raises(Exception) as info:
    #         df = wrangles.recipe.run(recipe, dataframe=data)

    def test_search_empty_results(self):
        """
        Test handling of queries that return no results
        """
        
        data = pd.DataFrame({
            'query': [''],
            'ID': [1]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 5
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert df.iloc[0]['results'] == []

    def test_dataframe_with_many_rows(self):
        """
        Test with DataFrame containing many rows (tests threading)
        """
        
        data = pd.DataFrame({
            'query': [f'wireless headphones' for i in range(50)],
            'ID': [i for i in range(50)]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 2
                threads: 5
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df) == 50
        assert all(len(row['results'][0]['search_results']) == 2 for _, row in df.iterrows())

    def test_special_characters_in_query(self):
        """
        Test queries with special characters
        """
        
        data = pd.DataFrame({
            'query': ['test & query', 'query with "quotes"', 'query+with+plus'],
            'ID': [1, 2, 3]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: ID
                api_key: ${SERPAPI_API_KEY}
                n_results: 2
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df) == 3
        assert all(isinstance(row['results'][0]['search_results'], list) for _, row in df.iterrows())
    
    def test_numeric_input_column(self):
        """
        Test with numeric values in input column
        """
        
        data = pd.DataFrame({
            'query': [12345, 67890]
        })
        
        recipe = """
        wrangles:
            - search.find_links:
                queries: query
                output: results
                id: query
                api_key: ${SERPAPI_API_KEY}
                n_results: 2
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df) == 2
        assert all(isinstance(row['results'][0]['search_results'], list) for _, row in df.iterrows())


class TestAiMode:
    """Test search.ai_mode recipe usage, parameters, input shapes, and errors."""

    query = "SKF 6205-2RS deep groove ball bearing specifications"

    def test_search_single_query(self):
        """Test the smallest recipe: one string query column and one output column."""
        data = pd.DataFrame({
            "query": [self.query],
        })
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        result = df.iloc[0]["results"][0]
        assert result["status"] == "Success", result["error"]
        assert result["search_metadata"]["query"] == self.query
        assert result["search_metadata"]["country"] == "us"
        assert result["search_metadata"]["language"] == "en"
        assert isinstance(result["search_results"], list)
        assert (
            result["extracted_content"]["answer_markdown"]
            or result["extracted_content"]["text_blocks"]
        )

    def test_queries_parameter_accepts_a_list_in_each_cell(self):
        """Test queries with a cell containing a list; each item returns one ordered result."""
        queries = [
            "What is the capital of Texas?",
            "What is the capital of Oklahoma?",
        ]
        data = pd.DataFrame({
            "query": [queries],
            "recipe_id": ["bearing"],
        })
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        results = df.iloc[0]["results"]
        assert len(results) == 2
        assert [result["search_metadata"]["query"] for result in results] == queries
        assert all(result["status"] == "Success" for result in results)
        assert df.iloc[0]["recipe_id"] == "bearing"
        assert all(
            "input_row_id" not in source
            for result in results
            for source in result["search_results"]
        )

    def test_queries_parameter_accepts_multiple_columns(self):
        """Test a list of query columns paired with the same number of output columns."""
        data = pd.DataFrame({
            "state_query": ["What is the capital of Texas?"],
            "country_query": ["What is the capital of Canada?"],
        })
        recipe = """
        wrangles:
          - search.ai_mode:
              queries:
                - state_query
                - country_query
              output:
                - state_result
                - country_result
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["state_result"][0]["search_metadata"]["query"] == data.iloc[0]["state_query"]
        assert df.iloc[0]["country_result"][0]["search_metadata"]["query"] == data.iloc[0]["country_query"]

    def test_output_parameter_accepts_structured_and_text_columns(self):
        """Test two outputs for one query: normalized dictionaries followed by readable text."""
        data = pd.DataFrame({
            "query": [self.query],
        })
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output:
                - results
                - result_text
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["status"] == "Success"
        assert "Query 1:" in df.iloc[0]["result_text"]
        assert self.query in df.iloc[0]["result_text"]

    def test_client_parameter_accepts_serpapi(self):
        """Test selecting the supported serpapi client explicitly in a recipe."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              client: serpapi
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["status"] == "Success"

    def test_api_key_parameter_accepts_an_explicit_key(self):
        """Test supplying the SerpAPI credential through the recipe api_key parameter."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["status"] == "Success"

    def test_api_key_parameter_defaults_to_the_environment(self):
        """Test omitting api_key when SERPAPI_API_KEY is available in the environment."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["status"] == "Success"

    def test_prompt_parameter_is_prepended_to_the_query(self):
        """Test a custom prompt and verify the exact combined query sent to SerpAPI."""
        prompt = "Answer in one sentence."
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              prompt: Answer in one sentence.
              api_key: ${SERPAPI_API_KEY}
              include_raw_response: true
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        result = df.iloc[0]["results"][0]
        assert result["status"] == "Success", result["error"]
        assert result["raw_response"]["search_parameters"]["q"] == f"{prompt}\n\n{self.query}"

    def test_prompt_parameter_defaults_to_none(self):
        """Test omitting prompt and verify SerpAPI receives only the unmodified query."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              include_raw_response: true
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        result = df.iloc[0]["results"][0]
        assert result["status"] == "Success", result["error"]
        assert result["raw_response"]["search_parameters"]["q"] == self.query

    def test_prompt_parameter_ignores_blank_text(self):
        """Test a whitespace-only prompt; it behaves like no prompt and sends only the query."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              prompt: "   "
              api_key: ${SERPAPI_API_KEY}
              include_raw_response: true
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        result = df.iloc[0]["results"][0]
        assert result["status"] == "Success", result["error"]
        assert result["raw_response"]["search_parameters"]["q"] == self.query

    def test_threads_parameter_processes_queries_in_order(self):
        """Test concurrent searches with threads while preserving input row order."""
        queries = [
            "What is the capital of Texas?",
            "What is the capital of Oklahoma?",
            "What is the capital of Canada?",
        ]
        data = pd.DataFrame({"query": queries})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              threads: 3
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        returned_queries = [cell[0]["search_metadata"]["query"] for cell in df["results"]]
        assert returned_queries == queries

    def test_country_parameter_sets_google_country(self):
        """Test country as the friendly recipe alias for SerpAPI's gl parameter."""
        data = pd.DataFrame({"query": ["What is the capital of Canada?"]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              country: ca
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["search_metadata"]["country"] == "ca"

    def test_language_parameter_sets_google_language(self):
        """Test language as the friendly recipe alias for SerpAPI's hl parameter."""
        data = pd.DataFrame({"query": ["What is the capital of Texas?"]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              language: es
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["search_metadata"]["language"] == "es"

    def test_location_parameter_sets_search_location(self):
        """Test a human-readable location and verify it is retained in result metadata."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              location: Austin, Texas, United States
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        location = df.iloc[0]["results"][0]["search_metadata"]["location"]
        assert "Austin" in location

    def test_no_cache_parameter_requests_a_fresh_response(self):
        """Test no_cache true, which asks SerpAPI to bypass its cached response."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              no_cache: true
              include_raw_response: true
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        result = df.iloc[0]["results"][0]
        assert result["status"] == "Success", result["error"]
        assert isinstance(result["raw_response"], dict)

    def test_include_raw_response_parameter_adds_provider_payload(self):
        """Test opting into the original JSON-safe SerpAPI response."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              include_raw_response: true
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert isinstance(df.iloc[0]["results"][0]["raw_response"], dict)

    def test_include_raw_response_defaults_to_false(self):
        """Test the default compact payload, which does not retain the provider response."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert "raw_response" not in df.iloc[0]["results"][0]

    def test_where_parameter_searches_only_matching_rows(self):
        """Test the common where parameter; unmatched rows are left unprocessed."""
        data = pd.DataFrame({
            "query": [self.query, "What is the capital of Oklahoma?"],
            "search": [False, True],
        })
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
              where: search == True
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"] == ""
        assert df.iloc[1]["results"][0]["status"] == "Success"

    def test_multiple_dataframe_rows_remain_aligned(self):
        """Test a tall dataframe; each row receives only the result for its own query."""
        queries = [
            "What is the capital of Texas?",
            "What is the capital of Oklahoma?",
            "What is the capital of Canada?",
        ]
        data = pd.DataFrame({"query": queries, "recipe_id": [10, 20, 30]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df["recipe_id"].tolist() == [10, 20, 30]
        assert [cell[0]["search_metadata"]["query"] for cell in df["results"]] == queries

    def test_integer_query_values_are_converted_to_strings(self):
        """Test an integer query column; numeric values are searched as their string form."""
        data = pd.DataFrame({"query": [2026]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["search_metadata"]["query"] == "2026"

    def test_datetime_query_values_are_converted_to_strings(self):
        """Test a datetime query column; timestamps are searched as their string form."""
        timestamp = pd.Timestamp("2026-08-21")
        data = pd.DataFrame({"query": [timestamp]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.iloc[0]["results"][0]["search_metadata"]["query"] == str(timestamp)

    def test_blank_and_null_queries_return_empty_aligned_results(self):
        """Test empty string, whitespace, None, NaN, and pd.NA without provider requests."""
        data = pd.DataFrame({
            "query": ["", "   ", None, float("nan"), pd.NA],
        })
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df["results"].tolist() == [[], [], [], [], []]

    def test_literal_nan_query_is_searchable(self):
        """Test that the literal text 'nan' reaches SerpAPI instead of being discarded."""
        data = pd.DataFrame({"query": ["nan"]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        result = df.iloc[0]["results"][0]
        assert result["status"] == "Success", result["error"]
        assert result["search_metadata"]["query"] == "nan"

    def test_list_queries_discard_blank_and_null_items(self):
        """Test mixed list cells; blank items are skipped without shifting valid results."""
        queries = ["What is the capital of Texas?", "", None, pd.NA]
        data = pd.DataFrame({"query": [queries]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: ${SERPAPI_API_KEY}
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        results = df.iloc[0]["results"]
        assert len(results) == 1
        assert results[0]["search_metadata"]["query"] == queries[0]

    def test_empty_dataframe_returns_an_empty_output_column(self):
        """Test a zero-row dataframe; the output column is created without a request."""
        data = pd.DataFrame({"query": pd.Series(dtype="object")})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.empty
        assert "results" in df.columns

    def test_non_default_dataframe_index_is_preserved(self):
        """Test empty inputs with string index labels; result rows keep the original index."""
        data = pd.DataFrame({"query": ["", None]}, index=["first", "second"])
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df.index.tolist() == ["first", "second"]
        assert df["results"].tolist() == [[], []]

    def test_error_when_query_and_output_counts_differ(self):
        """Test that two query columns cannot be mapped to one output column."""
        data = pd.DataFrame({"first": ["Texas"], "second": ["Oklahoma"]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries:
                - first
                - second
              output: results
        """

        with pytest.raises(ValueError, match="equal number of query and output columns"):
            wrangles.recipe.run(recipe, dataframe=data)

    def test_error_when_one_query_has_more_than_two_outputs(self):
        """Test that one query supports at most the structured/readable output pair."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output:
                - first
                - second
                - third
        """

        with pytest.raises(ValueError, match="equal number of query and output columns"):
            wrangles.recipe.run(recipe, dataframe=data)

    def test_error_when_query_column_does_not_exist(self):
        """Test a misspelled query column and surface the missing dataframe label."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: missing_query
              output: results
        """

        with pytest.raises(KeyError, match="missing_query"):
            wrangles.recipe.run(recipe, dataframe=data)

    def test_error_when_queries_parameter_is_missing(self):
        """Test omitting the required queries parameter from the recipe."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              output: results
        """

        with pytest.raises(ValueError, match="requires arguments.*queries"):
            wrangles.recipe.run(recipe, dataframe=data)

    def test_invalid_api_key_returns_a_failure_payload(self):
        """Test a rejected provider credential; query failures return data instead of shifting rows."""
        data = pd.DataFrame({"query": [self.query]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              api_key: invalid-key
        """

        df = wrangles.recipe.run(recipe, dataframe=data)

        result = df.iloc[0]["results"][0]
        assert result["status"] == "Failure"
        assert result["error"]
        assert result["search_results"] == []

    def test_error_when_removed_id_parameter_is_used(self):
        """Test that the removed id option is rejected instead of affecting source records."""
        data = pd.DataFrame({"query": [self.query], "ID": [1]})
        recipe = """
        wrangles:
          - search.ai_mode:
              queries: query
              output: results
              id: ID
        """

        with pytest.raises(TypeError, match="unexpected keyword argument 'id'"):
            wrangles.recipe.run(recipe, dataframe=data)


class TestRetrieveLinkContent:
    """
    Test the functionality of the retrieve_link_content wrangle
    """
    
    retrieve_link_data = wrangles.recipe.run("""
        read:
          - file:
              name: tests/temp/retrieve_link_content_test_data.json
        """).head(3)

    def test_link_content(self):
        """
        Test with numeric values in input column
        """
        
        recipe = """
        wrangles:
          - search.retrieve_link_content:
              input: summary
              output:
                - retrieved_data
                - Retrieved Content
              output_format: json
              api_key: ${GEMINI_API_KEY}
              threads: 10
        """
        
        df = wrangles.recipe.run(recipe, dataframe=self.retrieve_link_data.head(1))
        
        assert 'retrieved_data' in df.columns and 'Retrieved Content' in df.columns
        assert isinstance(df.iloc[0]['retrieved_data'], list) and isinstance(df.iloc[0]['retrieved_data'][0], dict)
        assert isinstance(df.iloc[0]['Retrieved Content'], str)


##### This should be moved to test_wrangles.py #####
##### These also do not work, so putting off for now. #####
# class TestSearchWebDirect:
#     """Test direct wrangles.search.find_links() function calls"""

#     api_key = os.environ.get("SERPAPI_API_KEY")

#     def test_direct_single_query(self):
#         """
#         Test direct function call with single query
#         """
        
#         results = wrangles.search.SerpApiWranglesClient.search_single(
#             self,
#         # results = wrangles.search.find_links(
#             "wireless headphones",
#             # api_key=self.api_key, # Function does not allow api_key to be passed
#             n_results=3
#         )
        
#         assert isinstance(results, list)
#         assert len(results) == 3
#         assert results[0]['title'] == 'Result 1 for wireless headphones'
    
#     @patch('wrangles.clients.serp_api._get_serpapi_client')
#     def test_direct_multiple_queries(self, mock_client):
#         """Test direct function call with list of queries"""
#         mock_client.return_value = MockSerpAPIClient
        
#         results = wrangles.search.find_links(
#             ["python", "java", "ruby"],
#             api_key="test_key",
#             n_results=2
#         )
        
#         assert isinstance(results, list)
#         assert len(results) == 3
#         assert all(len(r) == 2 for r in results)
#         assert results[0][0]['title'] == 'Result 1 for python'
#         assert results[1][0]['title'] == 'Result 1 for java'
    
#     @patch('wrangles.clients.serp_api._get_serpapi_client')
#     def test_direct_with_kwargs(self, mock_client):
#         """Test direct function call with additional kwargs"""
#         mock_client.return_value = MockSerpAPIClient
        
#         results = wrangles.search.find_links(
#             "test query",
#             api_key="test_key",
#             n_results=3,
#             gl="us",
#             hl="en"
#         )
        
#         assert len(results) == 3
    
#     def test_direct_invalid_api_key(self):
#         """Test that invalid/missing API key raises error"""
#         with pytest.raises(ValueError, match="api_key is required"):
#             wrangles.search.find_links("test", api_key="")
    
#     def test_direct_invalid_n_results(self):
#         """Test that invalid n_results raises error"""
#         with pytest.raises(ValueError, match="n_results must be a positive integer"):
#             wrangles.search.find_links("test", api_key="key", n_results=0)
        
#         with pytest.raises(ValueError, match="n_results must be a positive integer"):
#             wrangles.search.find_links("test", api_key="key", n_results=-1)
    
#     def test_direct_n_results_exceeds_limit(self):
#         """Test that n_results > 100 raises error"""
#         with pytest.raises(ValueError, match="n_results cannot exceed 100"):
#             wrangles.search.find_links("test", api_key="key", n_results=101)
    
#     @patch('wrangles.clients.serp_api._get_serpapi_client')
#     def test_direct_empty_query(self, mock_client):
#         """Test direct call with empty query"""
#         mock_client.return_value = MockSerpAPIClient
        
#         results = wrangles.search.find_links(
#             "",
#             api_key="test_key",
#             n_results=3
#         )
        
#         assert results == []
    
#     @patch('wrangles.clients.serp_api._get_serpapi_client')
#     def test_direct_error_handling(self, mock_client):
#         """Test error handling in search"""
#         mock_client.return_value = MockSerpAPIClient
        
#         results = wrangles.search.find_links(
#             "error query",
#             api_key="test_key",
#             n_results=3
#         )
        
#         # Error should be returned as part of results rather than raising
#         assert isinstance(results, list)
#         assert len(results) > 0
#         assert 'error' in results[0]
