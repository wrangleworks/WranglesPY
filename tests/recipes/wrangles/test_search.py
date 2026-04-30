import wrangles
import pandas as pd


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


class TestRetrieveLinkContent:
    """
    Test the functionality of the retrieve_link_content wrangle
    """
    ##### Need api key to set up tests for this #####

    # def test_link_content(self):
    #     """
    #     Test with numeric values in input column
    #     """
        
    #     data = pd.DataFrame({
    #         'query': ['Some sort of search data']
    #     })
        
    #     recipe = """
    #     wrangles:
    #           - search.retrieve_link_content:
    #               input: summary
    #               output: 
    #                 - retrieved_data
    #                 - Retrieved Content
    #               output_format: json
    #               api_key: ${GOOGLE_API_KEY}
    #               threads: 10
    #     """
        
    #     df = wrangles.recipe.run(recipe, dataframe=data)
        
    #     assert len(df) == 2
    #     assert all(isinstance(row['results'][0]['search_results'], list) for _, row in df.iterrows())


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