"""
Functions to perform web searches using various search engines.
"""
from typing import Union as _Union
import concurrent.futures as _futures


def _get_serpapi_client():
    try:
        from serpapi import Client as SerpApiClient
        return SerpApiClient
    except ImportError:
        raise ImportError(
            "The serpapi package is required for search functionality. "
            "Install it with: pip install serpapi"
        )


def _search_single_query(
    query: str,
    api_key: str,
    n_results: int,
    include_prices: bool,
    **kwargs
) -> list:
    """
    Perform a single web search using SerpAPI.
    
    :param query: Search query string
    :param api_key: SerpAPI API key
    :param n_results: Number of results to return
    :param include_prices: Include price information if available
    :param kwargs: Additional SerpAPI parameters (gl, hl, num, etc.)
    :return: List of search results
    """
    if not query or not str(query).strip():
        return []
    
    try:
        SerpApiClient = _get_serpapi_client()
        client = SerpApiClient(api_key=api_key)
        
        params = {
            "q": str(query).strip(),
            "num": min(n_results, 100),  
            **kwargs
        }
        
        results = client.search(params)

        organic_results = results.get("organic_results", [])
        
        formatted_results = []
        for idx, result in enumerate(organic_results[:n_results]):
            result_dict = {
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "position": result.get("position", idx + 1)
            }
            
            if include_prices and "price" in result:
                result_dict["price"] = result.get("price")
            
            formatted_results.append(result_dict)
        
        return formatted_results
    
    except Exception as e:
        return [{"error": str(e), "query": query}]


def web(
    input: _Union[str, list],
    api_key: str,
    n_results: int = 10,
    include_prices: bool = False,
    threads: int = 10,
    **kwargs
) -> _Union[list, list]:
    """
    Perform web searches using SerpAPI.
    
    >>> wrangles.search.web(
    >>>     "best python libraries 2024",
    >>>     api_key="your_api_key",
    >>>     n_results=5
    >>> )
    [
        {
            "title": "...",
            "link": "https://...",
            "snippet": "...",
            "position": 1
        },
        ...
    ]
    
    :param input: Search query or list of queries
    :param api_key: SerpAPI API key
    :param n_results: Number of results to return per query (default 10, max 100)
    :param include_prices: Include price information if available (default False)
    :param threads: Number of concurrent threads for parallel processing (default 10)
    :param kwargs: Additional SerpAPI parameters:
        - gl: Country code (e.g., 'us', 'uk')
        - hl: Language code (e.g., 'en', 'es')
        - location: Location for search results
        - device: Device type ('desktop', 'mobile', 'tablet')
    :return: List of search results for each query. If input was a string, returns a single list.
             If input was a list, returns a list of lists.
    """
    if not api_key:
        raise ValueError("api_key is required for search functionality")
    
    if not isinstance(n_results, int) or n_results < 1:
        raise ValueError("n_results must be a positive integer")
    
    if n_results > 100:
        raise ValueError("n_results cannot exceed 100 (SerpAPI limit)")

    input_was_scalar = False
    if not isinstance(input, list):
        input_was_scalar = True
        input = [input]
    
    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = list(executor.map(
            _search_single_query,
            input,
            [api_key] * len(input),
            [n_results] * len(input),
            [include_prices] * len(input),
            [kwargs] * len(input)
        ))
    
    if input_was_scalar:
        return results[0]
    
    return results