import pytest
import wrangles
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

class MockSerpAPIClient:
    """Mock SerpAPI Client for testing without actual API calls"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
    
    def search(self, params):
        """Mock search method that returns sample data"""
        query = params.get("q", "")
        num_results = params.get("num", 10)
        
        if "error" in query.lower():
            raise Exception("API Error: Invalid request")
        
        if "empty" in query.lower():
            return {"organic_results": []}
        
        results = []
        for i in range(min(num_results, 10)):
            result = {
                "position": i + 1,
                "title": f"Result {i + 1} for {query}",
                "link": f"https://example.com/result{i + 1}",
                "snippet": f"This is a snippet for result {i + 1} about {query}"
            }
            
            if "price" in query.lower() or "product" in query.lower():
                result["price"] = f"${(i + 1) * 10}.99"
            
            results.append(result)
        
        return {"organic_results": results}


class TestSearchWeb:
    """Test search.web functionality"""
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_single_query(self, mock_client):
        """Test basic single query search"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['wireless headphones']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 5
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert 'results' in df.columns
        assert len(df.iloc[0]['results']) == 5
        assert df.iloc[0]['results'][0]['title'] == 'Result 1 for wireless headphones'
        assert 'link' in df.iloc[0]['results'][0]
        assert 'snippet' in df.iloc[0]['results'][0]
        assert 'position' in df.iloc[0]['results'][0]
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_multiple_queries(self, mock_client):
        """Test search with multiple queries"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['python programming', 'machine learning', 'data science']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 3
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df) == 3
        assert all(len(row['results']) == 3 for _, row in df.iterrows())
        assert df.iloc[1]['results'][0]['title'] == 'Result 1 for machine learning'
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_with_n_results(self, mock_client):
        """Test search with different n_results values"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['test query']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 7
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df.iloc[0]['results']) == 7
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_multiple_input_columns(self, mock_client):
        """Test search with multiple input columns (concatenated)"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'col1': ['wireless'],
            'col2': ['headphones']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input:
                    - col1
                    - col2
                output: results
                api_key: test_api_key
                n_results: 3
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert 'results' in df.columns
        assert len(df.iloc[0]['results']) == 3
        # Query should be concatenated: "wireless headphones"
        assert 'wireless headphones' in df.iloc[0]['results'][0]['title']
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_multiple_output_columns(self, mock_client):
        """Test search with multiple input/output columns"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query1': ['python'],
            'query2': ['javascript']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input:
                    - query1
                    - query2
                output:
                    - results1
                    - results2
                api_key: test_api_key
                n_results: 3
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert 'results1' in df.columns
        assert 'results2' in df.columns
        assert 'python' in df.iloc[0]['results1'][0]['title']
        assert 'javascript' in df.iloc[0]['results2'][0]['title']
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_where_clause(self, mock_client):
        """Test search.web using where clause"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['python', 'java', 'ruby'],
            'priority': [1, 5, 3]
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 2
                where: priority > 2
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert df.iloc[0]['results'] == ""  # priority = 1, not processed
        assert len(df.iloc[1]['results']) == 2  # priority = 5, processed
        assert len(df.iloc[2]['results']) == 2  # priority = 3, processed
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_empty_input(self, mock_client):
        """Test search with empty input"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['', 'valid query', None]
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 3
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        # Empty and None queries should return empty results
        assert df.iloc[0]['results'] == []
        assert len(df.iloc[1]['results']) == 3
        assert df.iloc[2]['results'] == []
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_include_prices(self, mock_client):
        """Test search with include_prices parameter"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['product search']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 3
                include_prices: true
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert 'price' in df.iloc[0]['results'][0]
        assert df.iloc[0]['results'][0]['price'] == '$10.99'
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_with_country(self, mock_client):
        """Test search with country parameter"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['test query']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 3
                gl: uk
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df.iloc[0]['results']) == 3
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_with_language(self, mock_client):
        """Test search with language parameter"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['test query']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 3
                hl: es
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df.iloc[0]['results']) == 3
    
    def test_search_missing_api_key(self):
        """Test that missing API key raises error"""
        data = pd.DataFrame({
            'query': ['test']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                n_results: 3
        """
        
        with pytest.raises(Exception):
            wrangles.recipe.run(recipe, dataframe=data)
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_search_empty_results(self, mock_client):
        """Test handling of queries that return no results"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['empty results query']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_api_key
                n_results: 5
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert df.iloc[0]['results'] == []


class TestSearchWebDirect:
    """Test direct wrangles.search.web() function calls"""
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_direct_single_query(self, mock_client):
        """Test direct function call with single query"""
        mock_client.return_value = MockSerpAPIClient
        
        results = wrangles.search.web(
            "wireless headphones",
            api_key="test_key",
            n_results=3
        )
        
        assert isinstance(results, list)
        assert len(results) == 3
        assert results[0]['title'] == 'Result 1 for wireless headphones'
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_direct_multiple_queries(self, mock_client):
        """Test direct function call with list of queries"""
        mock_client.return_value = MockSerpAPIClient
        
        results = wrangles.search.web(
            ["python", "java", "ruby"],
            api_key="test_key",
            n_results=2
        )
        
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(len(r) == 2 for r in results)
        assert results[0][0]['title'] == 'Result 1 for python'
        assert results[1][0]['title'] == 'Result 1 for java'
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_direct_with_kwargs(self, mock_client):
        """Test direct function call with additional kwargs"""
        mock_client.return_value = MockSerpAPIClient
        
        results = wrangles.search.web(
            "test query",
            api_key="test_key",
            n_results=3,
            gl="us",
            hl="en"
        )
        
        assert len(results) == 3
    
    def test_direct_invalid_api_key(self):
        """Test that invalid/missing API key raises error"""
        with pytest.raises(ValueError, match="api_key is required"):
            wrangles.search.web("test", api_key="")
    
    def test_direct_invalid_n_results(self):
        """Test that invalid n_results raises error"""
        with pytest.raises(ValueError, match="n_results must be a positive integer"):
            wrangles.search.web("test", api_key="key", n_results=0)
        
        with pytest.raises(ValueError, match="n_results must be a positive integer"):
            wrangles.search.web("test", api_key="key", n_results=-1)
    
    def test_direct_n_results_exceeds_limit(self):
        """Test that n_results > 100 raises error"""
        with pytest.raises(ValueError, match="n_results cannot exceed 100"):
            wrangles.search.web("test", api_key="key", n_results=101)
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_direct_empty_query(self, mock_client):
        """Test direct call with empty query"""
        mock_client.return_value = MockSerpAPIClient
        
        results = wrangles.search.web(
            "",
            api_key="test_key",
            n_results=3
        )
        
        assert results == []
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_direct_error_handling(self, mock_client):
        """Test error handling in search"""
        mock_client.return_value = MockSerpAPIClient
        
        results = wrangles.search.web(
            "error query",
            api_key="test_key",
            n_results=3
        )
        
        # Error should be returned as part of results rather than raising
        assert isinstance(results, list)
        assert len(results) > 0
        assert 'error' in results[0]


class TestSearchWebEdgeCases:
    """Test edge cases and error conditions"""
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_dataframe_with_single_row(self, mock_client):
        """Test with DataFrame containing single row"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({'query': ['test']})
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_key
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 1
        assert isinstance(df.iloc[0]['results'], list)
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_dataframe_with_many_rows(self, mock_client):
        """Test with DataFrame containing many rows (tests threading)"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': [f'query {i}' for i in range(50)]
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_key
                n_results: 2
                threads: 5
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df) == 50
        assert all(len(row['results']) == 2 for _, row in df.iterrows())
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_special_characters_in_query(self, mock_client):
        """Test queries with special characters"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': ['test & query', 'query with "quotes"', 'query+with+plus']
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_key
                n_results: 2
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df) == 3
        assert all(isinstance(row['results'], list) for _, row in df.iterrows())
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_numeric_input_column(self, mock_client):
        """Test with numeric values in input column"""
        mock_client.return_value = MockSerpAPIClient
        
        data = pd.DataFrame({
            'query': [12345, 67890]
        })
        
        recipe = """
        wrangles:
            - search.web:
                input: query
                output: results
                api_key: test_key
                n_results: 2
        """
        
        df = wrangles.recipe.run(recipe, dataframe=data)
        
        assert len(df) == 2
        assert all(isinstance(row['results'], list) for _, row in df.iterrows())


