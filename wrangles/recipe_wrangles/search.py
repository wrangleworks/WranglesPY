"""
Functions to run search wrangles as part of a recipe.
"""
from typing import Union as _Union
import pandas as _pd
from ..clients import serp_api as _search


def web(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list],
    api_key: str,
    n_results: int = 10,
    include_prices: bool = False,
    threads: int = 10,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Perform web searches using SerpAPI. Returns structured search results with titles, links, and snippets.
    additionalProperties: false
    required:
      - input
      - output
      - api_key
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns containing search queries. Multiple columns will be concatenated.
      output:
        type:
          - string
          - array
        description: Name or list of output columns to write search results to.
      api_key:
        type: string
        description: SerpAPI API key. Can be set as environment variable SERPAPI_KEY.
      n_results:
        type: integer
        description: Number of search results to return per query (default 10, max 100)
      include_prices:
        type: boolean
        description: Include price information in results if available (default false)
      threads:
        type: integer
        description: Number of concurrent threads for parallel processing (default 10)
      gl:
        type: string
        description: Country code for search results (e.g., 'us', 'uk', 'de')
      hl:
        type: string
        description: Language code for search results (e.g., 'en', 'es', 'fr')
      location:
        type: string
        description: Location for search results (e.g., 'Austin, Texas')
      device:
        type: string
        description: Device type for search results
        enum:
          - desktop
          - mobile
          - tablet
    """

    if output is None:
        output = input
    
    if not api_key:
        raise ValueError("api_key is required for search.web")
    

    if not isinstance(input, list):
        input = [input]
    if not isinstance(output, list):
        output = [output]
    
    if len(input) != len(output) and len(output) > 1:
        raise ValueError(
            'search.web must output to a single column or equal amount of columns as input.'
        )
    
    if len(output) == 1 and len(input) > 1:
        queries = df[input].astype(str).aggregate(' '.join, axis=1).tolist()
        
        # Perform searches
        results = _search.web(
            queries,
            api_key=api_key,
            n_results=n_results,
            include_prices=include_prices,
            threads=threads,
            **kwargs
        )
        
        df[output[0]] = results
    else:
        for input_column, output_column in zip(input, output):
            queries = df[input_column].astype(str).tolist()
            results = _search.web(
                queries,
                api_key=api_key,
                n_results=n_results,
                include_prices=include_prices,
                threads=threads,
                **kwargs
            )
            
            df[output_column] = results
    
    return df
