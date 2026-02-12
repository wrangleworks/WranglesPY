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
        # Include query in URL to avoid deduplication issues in tests
        query_slug = query.replace(" ", "-").lower()
        for i in range(min(num_results, 10)):
            result = {
                "position": i + 1,
                "title": f"Result {i + 1} for {query}",
                "link": f"https://example.com/{query_slug}/result{i + 1}",
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


class TestNewSerpAPIFunctions:
    """Test new serpapi_client functions"""
    
    def test_ensure_list_with_string(self):
        """Test _ensure_list with a string input"""
        from wrangles.clients.serp_api import _ensure_list
        
        result = _ensure_list("test query")
        assert result == ["test query"]
        
        result = _ensure_list("")
        assert result == []
        
        result = _ensure_list("  ")
        assert result == []
    
    def test_ensure_list_with_list(self):
        """Test _ensure_list with a list input"""
        from wrangles.clients.serp_api import _ensure_list
        
        result = _ensure_list(["query1", "query2"])
        assert result == ["query1", "query2"]
        
        result = _ensure_list(["query1", "", "query2", None])
        assert result == ["query1", "query2"]
    
    def test_ensure_list_with_none(self):
        """Test _ensure_list with None input"""
        from wrangles.clients.serp_api import _ensure_list
        
        result = _ensure_list(None)
        assert result == []
    
    def test_clean_link(self):
        """Test _clean_link function"""
        from wrangles.clients.serp_api import _clean_link
        
        # Test with srsltid parameter
        url = "https://example.com/page?srsltid=123456&other=param"
        result = _clean_link(url)
        assert result == "https://example.com/page"
        
        # Test with trailing ? and &
        url = "https://example.com/page?"
        result = _clean_link(url)
        assert result == "https://example.com/page"
        
        # Test with HTML entities
        url = "https://example.com/page&amp;param=1"
        result = _clean_link(url)
        assert "amp;" not in result
        
        # Test with empty string
        assert _clean_link("") == ""
        assert _clean_link(None) == ""
    
    def test_normalize_site(self):
        """Test _normalize_site function for deduplication"""
        from wrangles.clients.serp_api import _normalize_site
        
        # Test protocol removal
        assert _normalize_site("https://example.com") == _normalize_site("http://example.com")
        
        # Test www removal
        assert _normalize_site("https://www.example.com") == _normalize_site("https://example.com")
        
        # Test trailing slash removal
        assert _normalize_site("https://example.com/page") == _normalize_site("https://example.com/page/")
        
        # Test query parameter removal
        assert _normalize_site("https://example.com/page?param=1") == _normalize_site("https://example.com/page")
        
        # Test case insensitivity
        assert _normalize_site("https://EXAMPLE.COM") == _normalize_site("https://example.com")
        
        # Test comprehensive example
        url1 = "https://www.Example.com/page/?param=1"
        url2 = "http://example.com/page"
        assert _normalize_site(url1) == _normalize_site(url2)
    
    def test_format_card_price(self):
        """Test _format_card_price function"""
        from wrangles.clients.serp_api import _format_card_price
        
        # Test with just price
        item = {"price": "$19.99"}
        assert _format_card_price(item) == "$19.99"
        
        # Test with original price
        item = {"price": "$15.99", "original_price": "$19.99"}
        result = _format_card_price(item)
        assert "15.99" in result
        assert "Was: $19.99" in result
        
        # Test with tag
        item = {"price": "$15.99", "original_price": "$19.99", "tag": "20% off"}
        result = _format_card_price(item)
        assert "15.99" in result
        assert "Was: $19.99" in result
        assert "20% off" in result
    
    def test_convert_to_eastern(self):
        """Test convert_to_eastern function"""
        from wrangles.clients.serp_api import convert_to_eastern
        import pytz
        
        # Test with valid ISO timestamp
        timestamp = "2024-01-15T10:30:00Z"
        result = convert_to_eastern(timestamp)
        # Check that the result has Eastern timezone (don't compare tzinfo objects directly)
        assert str(result.tzinfo) in ['EST', 'EDT', 'US/Eastern']
        
        # Test with empty string
        result = convert_to_eastern("")
        assert str(result.tzinfo) in ['EST', 'EDT', 'US/Eastern']
        
        # Test with invalid timestamp
        result = convert_to_eastern("invalid")
        assert str(result.tzinfo) in ['EST', 'EDT', 'US/Eastern']
    
    def test_parse_snippet_extensions_with_price(self):
        """Test _parse_snippet_extensions with price data"""
        from wrangles.clients.serp_api import _parse_snippet_extensions
        
        # Test with detected price
        rich_snippet = {
            "bottom": {
                "detected_extensions": {
                    "price": "19.99",
                    "currency": "USD"
                }
            }
        }
        price, currency, availability = _parse_snippet_extensions(rich_snippet, "$")
        assert price == 19.99
        assert currency == "USD"
        assert availability == ""
    
    def test_parse_snippet_extensions_with_range(self):
        """Test _parse_snippet_extensions with price range"""
        from wrangles.clients.serp_api import _parse_snippet_extensions
        
        # Test with price range
        rich_snippet = {
            "bottom": {
                "detected_extensions": {
                    "price": "$19.99 to $29.99"
                }
            }
        }
        price, currency, availability = _parse_snippet_extensions(rich_snippet, "$")
        assert price == 19.99  # Should take lower bound
        assert currency == "$"
    
    def test_parse_snippet_extensions_with_availability(self):
        """Test _parse_snippet_extensions with availability"""
        from wrangles.clients.serp_api import _parse_snippet_extensions
        
        # Test with availability in extensions
        rich_snippet = {
            "bottom": {
                "extensions": ["In stock", "$19.99"]
            }
        }
        price, currency, availability = _parse_snippet_extensions(rich_snippet, "$")
        assert availability == "In stock"
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_google_search(self, mock_client):
        """Test google_search function"""
        mock_client.return_value = MockSerpAPIClient
        from wrangles.clients.serp_api import google_search
        
        result = google_search("test query", "test_api_key")
        
        assert "organic_results" in result
        assert isinstance(result["organic_results"], list)
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_fetch_serp_results_single_query(self, mock_client):
        """Test fetch_serp_results with single query"""
        mock_client.return_value = MockSerpAPIClient
        from wrangles.clients.serp_api import fetch_serp_results
        
        search_content, pricing_content, organic_results = fetch_serp_results(
            "test query",
            "test_api_key",
            n_results=3
        )
        
        assert isinstance(search_content, list)
        assert isinstance(pricing_content, list)
        assert isinstance(organic_results, list)
        assert len(search_content) <= 3
        assert len(organic_results) <= 3
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_fetch_serp_results_multiple_queries(self, mock_client):
        """Test fetch_serp_results with multiple queries"""
        mock_client.return_value = MockSerpAPIClient
        from wrangles.clients.serp_api import fetch_serp_results
        
        search_content, pricing_content, organic_results = fetch_serp_results(
            ["query1", "query2"],
            "test_api_key",
            n_results=2
        )
        
        assert isinstance(search_content, list)
        assert isinstance(organic_results, list)
        # Should have results from both queries
        assert len(search_content) > 0
        assert any(item.get("query_index") == 1 for item in search_content)
        assert any(item.get("query_index") == 2 for item in search_content)
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_fetch_serp_results_deduplication(self, mock_client):
        """Test that fetch_serp_results deduplicates results"""
        mock_client.return_value = MockSerpAPIClient
        from wrangles.clients.serp_api import fetch_serp_results
        
        # Test with same query twice - should deduplicate
        search_content, pricing_content, organic_results = fetch_serp_results(
            ["test query", "test query"],
            "test_api_key",
            n_results=5
        )
        
        # Extract all links
        links = [item.get("link") for item in search_content]
        
        # Check that we don't have exact duplicates
        # (Note: MockSerpAPIClient generates unique URLs per result, so this tests the mechanism)
        assert len(links) == len(set(links))
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_fetch_serp_results_metadata_injection(self, mock_client):
        """Test that fetch_serp_results properly injects metadata"""
        mock_client.return_value = MockSerpAPIClient
        from wrangles.clients.serp_api import fetch_serp_results
        
        search_content, pricing_content, organic_results = fetch_serp_results(
            "test query",
            "test_api_key",
            n_results=2
        )
        
        # Check search_content has required metadata
        if search_content:
            first_result = search_content[0]
            assert "query" in first_result
            assert "query_index" in first_result
            assert "item_index" in first_result
            assert "position" in first_result
            assert "title" in first_result
            assert "link" in first_result
            assert "snippet" in first_result
        
        # Check organic_results has metadata
        if organic_results:
            first_organic = organic_results[0]
            assert "query" in first_organic
            assert "query_index" in first_organic
            assert "date_time" in first_organic
    
    @patch('wrangles.clients.serp_api._get_serpapi_client')
    def test_fetch_serp_results_with_config(self, mock_client):
        """Test fetch_serp_results with custom config"""
        mock_client.return_value = MockSerpAPIClient
        from wrangles.clients.serp_api import fetch_serp_results
        
        config = {
            "language": "es",
            "country": "es",
            "location": "Madrid, Spain"
        }
        
        search_content, pricing_content, organic_results = fetch_serp_results(
            "test query",
            "test_api_key",
            n_results=2,
            config=config
        )
        
        assert isinstance(search_content, list)
        assert isinstance(organic_results, list)

