import logging as _logging
import pandas as _pd
from .. import _ai_mode

# Import the combined core wrangles
from .. import search as _search_core
from .. import format as _format


def _normalize_search_kwargs(kwargs: dict) -> dict:
  params = dict(kwargs or {})

  if "country" in params and "gl" not in params:
    params["gl"] = params.pop("country")
  if "language" in params and "hl" not in params:
    params["hl"] = params.pop("language")

  if "google_domain" in params and ("gl" in params or "hl" in params):
    raise ValueError(
      "google_domain cannot be combined with country/language (or gl/hl). "
      "Use google_domain alone, or use country/language without google_domain."
    )

  # Keep existing defaults for classic locale controls unless google_domain is explicitly provided.
  if "google_domain" not in params:
    params.setdefault("gl", "us")
    params.setdefault("hl", "en")
  return params

def find_links(
    df: _pd.DataFrame,
    queries: str | list,
    id: str,
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
      - queries
      - id
      - output
    properties:
      queries:
        type:
          - string
          - array
        description: Name or list of input columns containing search queries.
      id:
        type: string
        description: Name of the column containing the row ID to append to each search result.
      output:
        type:
          - string
          - array
        description: Output column for the dictionaries. If a list of 2 is provided, outputs [dicts_column, pretty_strings_column].
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
        description: "Country code for search results (default 'us'). Alias: gl."
        default: us
      language:
        type: string
        description: "Language code for search results (default 'en'). Alias: hl."
        default: en
      google_domain:
        type: string
        description: Google domain for search results (e.g., google.com, google.co.uk).
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
    if output is None: output = queries

    client_config = {"api_key": api_key}
    kwargs = _normalize_search_kwargs(kwargs)

    if not isinstance(queries, list): queries = [queries]
    if not isinstance(output, list): output = [output]

    # --- NEW: Handle the 1 Query -> 2 Outputs scenario ---
    is_multi_output = len(queries) == 1 and len(output) == 2
    
    if not is_multi_output and len(queries) != len(output):
        raise ValueError("search.find_links must have an equal number of query and output columns, OR 1 query column and 2 output columns [dicts, strings].")

    def _to_query_list(v) -> list[str]:
        if v is None: return []
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if x is not None and str(x).strip()]
        s = str(v).strip()
        return [s] if s else []

    row_ids = df[id].tolist() if id in df.columns else [None] * len(df)

    for i, query_column in enumerate(queries):
        # Target the correct dict output column based on the mode
        dict_output_column = output[0] if is_multi_output else output[i]
        
        row_query_lists = [_to_query_list(v) for v in df[query_column].tolist()]
        flat_queries = [q for qs in row_query_lists for q in qs]

        if not flat_queries:
            df[dict_output_column] = [[] for _ in row_query_lists]
            if is_multi_output: df[output[1]] = ["" for _ in row_query_lists]
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

        out_cells, string_cells, pos, total_queries, total_results = [], [], 0, 0, 0

        for qs, current_id in zip(row_query_lists, row_ids):
            k = len(qs)
            total_queries += k
            if k == 0:
                out_cells.append([])
                string_cells.append("")
                continue

            cell = flat_responses[pos:pos + k]
            for j, resp in enumerate(cell, start=1):
                if isinstance(resp, dict):
                    if "search_metadata" in resp and isinstance(resp["search_metadata"], dict):
                        resp["search_metadata"]["query_index"] = j
                    
                    updated_results = []
                    for r in resp.get("search_results", []):
                        if isinstance(r, dict):
                            new_r = {"input_row_id": current_id}
                            new_r.update(r)
                            new_r["query_index"] = j
                            updated_results.append(new_r)
                        else:
                            updated_results.append(r)
                    
                    resp["search_results"] = updated_results
                    total_results += len(updated_results)

            out_cells.append(cell)
            
            # Generate the string version if requested
            if is_multi_output:
                string_cells.append(_format.raw_search_results_to_text(cell))
                
            pos += k

        # Write to dataframe
        df[dict_output_column] = out_cells
        if is_multi_output:
            df[output[1]] = string_cells
            
        _logging.info(f": Wrangling :: find_links summary :: {total_queries} queries >> {total_results} results")

    return df


def ai_mode(
    df: _pd.DataFrame,
    queries: str,
    id: str,
    output: str | list | None = None,
    client: str = "serpapi",
    api_key: str | None = None,
    threads: int = 10,
    include_raw_response: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Retrieve Google AI Mode Markdown and metadata. Use standardize.clean and extract.ai afterwards for cleanup and structuring.
    additionalProperties: false
    required:
      - queries
      - id
      - output
    properties:
      queries:
        type: string
        description: Column containing one query string per row. Explode query lists before searching.
      id:
        type: string
        description: Input row ID column, retained in metadata.input_row_id.
      output:
        oneOf:
          - type: string
            minLength: 1
          - type: array
            minItems: 1
            maxItems: 2
            uniqueItems: true
            items:
              type: string
              minLength: 1
        description: |-
          Outputs are ordered [ai_mode_results, ai_mode_metadata]. The first is
          the untouched Markdown body; the optional second is the YAML frontmatter
          as a JSON-compatible dictionary, with query, query_index, input_row_id,
          search_id, status and error. Search requests output=md. It does not parse
          headings, select references, clean the body or extract prices. Blank
          queries have status Skipped. Missing/malformed metadata, provider errors
          and empty successful answers are explicit errors; non-success rows must
          not be passed to extraction. query_config and the previous three-output
          compact/complete/Markdown contract are no longer supported.
      client:
        type: string
        enum: [serpapi]
        default: serpapi
      api_key:
        type: string
        description: Search key; defaults to SERPAPI_API_KEY.
      threads:
        type: integer
        minimum: 1
        default: 10
      include_raw_response:
        type: boolean
        default: false
        description: Retain the untouched Markdown response including frontmatter under metadata.raw_response for trial capture and replay.
      country:
        type: [string, 'null']
        description: "Optional country code. Alias: gl. Null or empty means omit."
      gl:
        type: [string, 'null']
        description: Optional country code; omitted unless supplied.
      language:
        type: [string, 'null']
        description: "Optional language code. Alias: hl. Null or empty means omit."
      hl:
        type: [string, 'null']
        description: Optional language code; omitted unless supplied.
      location:
        type: [string, 'null']
        description: Optional city or geographic location; omitted unless supplied.
      device:
        type: string
        enum: [desktop, mobile, tablet]
        description: Optional device override.
    """
    kwargs = _ai_mode.request_parameters(kwargs)
    if not isinstance(queries, str) or not queries:
        raise ValueError("search.ai_mode requires one query column.")
    if output is None:
        output = queries
    columns = [output] if isinstance(output, str) else output
    if (
        not isinstance(columns, list) or len(columns) not in (1, 2)
        or any(not isinstance(name, str) or not name for name in columns)
        or len(set(columns)) != len(columns)
    ):
        raise ValueError("search.ai_mode requires 1 or 2 distinct output columns [ai_mode_results, ai_mode_metadata].")
    row_ids = df[id].tolist()
    query_values = [
        "" if value is _pd.NA or value is _pd.NaT else _ai_mode.normalize_query(value)
        for value in df[queries].tolist()
    ]
    responses = _search_core.ai_mode(
        queries=query_values, client=client, client_config={"api_key": api_key},
        threads=threads, include_raw_response=include_raw_response, **kwargs,
    )
    if len(responses) != len(df):
        raise RuntimeError("AI Mode response count does not match the input row count.")
    for row_id, response in zip(row_ids, responses):
        response["ai_mode_metadata"]["input_row_id"] = row_id
    for column, payload in zip(columns, ("ai_mode_results", "ai_mode_metadata")):
        df[column] = [response[payload] for response in responses]
    _logging.info(f": Wrangling :: ai_mode summary :: {len(query_values)} queries processed")
    return df


def retrieve_link_content(
    df: _pd.DataFrame,
    input: str | list,
    output: str | list | None = None,
    client: str = "google_url_context",
    api_key: str | None = None,
    prompt: str | None = None,
    model_id: str = None,
    output_format: str = "json",
    threads: int = None
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
        description: The specific model ID to use. Defaults to the AI configuration.
      output_format:
        type: string
        description: The desired format for the extracted content.
        enum:
          - markdown
          - json
        default: json
      threads:
        type: integer
        description: Number of concurrent threads for parallel processing. Defaults to the AI configuration.
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
