import logging as _logging
import pandas as _pd

# Import the combined core wrangles
from .. import search as _search_core
from .. import format as _format

def find_links(
    df: _pd.DataFrame,
    input: str | list,
    output: str | list | None = None,
    client: str = "serpapi",
    api_key: str | None = None,
    n_results: int = 10,
    threads: int = 10,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Perform web searches to find links. Returns structured search results with titles, links, snippets, and optional pricing.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input columns containing search queries. Must map 1:1 with output columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns to write search results to.
      client:
        type: string
        description: The search provider to use.
        enum:
          - serpapi
        default: serpapi
      api_key:
        type: string
        description: API key for the search client. Can also be set as an environment variable (e.g., SERPAPI_API_KEY).
      n_results:
        type: integer
        description: Number of search results to return per query (default 10, max 100).
        default: 10
      threads:
        type: integer
        description: Number of concurrent threads for parallel processing (default 10).
        default: 10
      country:
        type: string
        description: Country code for search results (default 'us'). Alias: gl.
        default: us
      language:
        type: string
        description: Language code for search results (default 'en'). Alias: hl.
        default: en
      location:
        type: string
        description: Location for search results (e.g., 'Austin, Texas').
      device:
        type: string
        description: Device type for search results.
        enum:
          - desktop
          - mobile
          - tablet
    """
    if output is None: output = input

    client_config = {"api_key": api_key}
            
    if "country" in kwargs and "gl" not in kwargs: kwargs["gl"] = kwargs.pop("country")
    if "language" in kwargs and "hl" not in kwargs: kwargs["hl"] = kwargs.pop("language")

    kwargs.setdefault("gl", "us")
    kwargs.setdefault("hl", "en")

    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    if len(input) != len(output):
        raise ValueError("search.find_links must have an equal number of input and output columns.")

    def _to_query_list(v) -> list[str]:
        if v is None: return []
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if x is not None and str(x).strip()]
        s = str(v).strip()
        return [s] if s else []

    for input_column, output_column in zip(input, output):
        row_query_lists = [_to_query_list(v) for v in df[input_column].tolist()]
        flat_queries = [q for qs in row_query_lists for q in qs]

        if not flat_queries:
            df[output_column] = [[] for _ in row_query_lists]
            _logging.info(f": Wrangling :: find_links summary :: 0 queries >> 0 results")
            continue

        flat_responses = _search_core.find_links(
            queries=flat_queries,
            client=client,
            client_config=client_config,
            n_results=n_results,
            threads=threads,
            **kwargs
        )

        out_cells, pos, total_queries, total_results = [], 0, 0, 0

        for qs in row_query_lists:
            k = len(qs)
            total_queries += k
            if k == 0:
                out_cells.append([])
                continue

            cell = flat_responses[pos:pos + k]
            for j, resp in enumerate(cell, start=1):
                if isinstance(resp, dict):
                    if "search_metadata" in resp and isinstance(resp["search_metadata"], dict):
                        resp["search_metadata"]["query_index"] = j
                    for r in resp.get("search_results", []):
                        if isinstance(r, dict):
                            r["query_index"] = j
                    total_results += len(resp.get("search_results", []))

            out_cells.append(cell)
            pos += k

        df[output_column] = out_cells
        _logging.info(f": Wrangling :: find_links summary :: {total_queries} queries >> {total_results} results")

    return df



def retrieve_link_content(
    df: _pd.DataFrame,
    input: str | list,
    output: str | list | None = None,
    client: str = "google_url_context",
    api_key: str | None = None,
    prompt: str | None = None,
    model_id: str = "models/gemini-3-flash-preview",
    output_format: str = "json",
    threads: int = 10
) -> _pd.DataFrame:
    """
    type: object
    description: Retrieves targeted content from web pages using LLM URL extraction. Can optionally output a second column containing a clean, human-readable text summary of the retrieved data.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input columns containing URLs or Scored Search Result dictionaries.
      output:
        type:
          - string
          - array
        description: Name of the output column for the raw dictionaries. To output BOTH the raw dictionaries and the formatted text, provide a list of exactly two column names (e.g., [page_data, page_text]).
      client:
        type: string
        description: The retrieval provider to use.
        enum:
          - google_url_context
        default: google_url_context
      api_key:
        type: string
        description: API key for the provider. Can also be set as an environment variable (e.g., GOOGLE_API_KEY).
      prompt:
        type: string
        description: Optional custom system prompt to guide the extraction behavior and output format.
      model_id:
        type: string
        description: The specific model ID to use (default models/gemini-3-flash-preview).
      output_format:
        type: string
        description: The desired format for the extracted content.
        enum:
          - markdown
          - json
        default: json
      threads:
        type: integer
        description: Number of concurrent threads for parallel processing (default 10).
        default: 10
    """
    if output is None: output = input

    client_config = {"api_key": api_key}
            
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # --- Dual Output Mode Detection ---
    is_dual_output = False
    if len(input) == 1 and len(output) == 2:
        is_dual_output = True
    elif len(input) != len(output):
        raise ValueError("search.retrieve_link_content must have an equal number of input and output columns, OR exactly one input and two outputs (e.g., output: [page_data, page_text]).")

    def _extract_url(v) -> str:
        if not v: return ""
        if isinstance(v, dict):
            if "summary" in v and isinstance(v["summary"], dict):
                return v["summary"].get("link", "")
            return v.get("link", v.get("url", ""))
        return str(v).strip()

    def _to_url_list(v) -> list[str]:
        if v is None: return []
        if isinstance(v, (list, tuple)):
            return [_extract_url(x) for x in v if x is not None and _extract_url(x)]
        extracted = _extract_url(v)
        return [extracted] if extracted else []

    # --- Standard Execution ---
    for i, input_column in enumerate(input):
        row_url_lists = [_to_url_list(v) for v in df[input_column].tolist()]
        flat_urls = [u for urls in row_url_lists for u in urls]

        if not flat_urls:
            if is_dual_output:
                df[output[0]] = [[] for _ in row_url_lists]
                df[output[1]] = ["" for _ in row_url_lists]
            else:
                df[output[i]] = [[] for _ in row_url_lists]
            _logging.info(f": Wrangling :: retrieve_link_content summary :: 0 URLs >> 0 results")
            continue

        flat_responses = _search_core.retrieve_link_content(
            urls=flat_urls,
            client=client,
            client_config=client_config,
            prompt=prompt,
            model_id=model_id,
            output_format=output_format,
            threads=threads
        )

        out_cells_dict, out_cells_text = [], []
        pos, total_urls = 0, 0

        for urls in row_url_lists:
            k = len(urls)
            total_urls += k
            if k == 0:
                out_cells_dict.append([])
                out_cells_text.append("")
                continue

            cell = flat_responses[pos:pos + k]
            out_cells_dict.append(cell)
            
            # Apply the formatter if dual output is requested
            if is_dual_output:
                out_cells_text.append(_format.retrieved_content_to_text(cell))
                
            pos += k

        # Write to DataFrame
        if is_dual_output:
            df[output[0]] = out_cells_dict
            df[output[1]] = out_cells_text
        else:
            df[output[i]] = out_cells_dict
            
        _logging.info(f": Wrangling :: retrieve_link_content summary :: processed {total_urls} URLs")

    return df