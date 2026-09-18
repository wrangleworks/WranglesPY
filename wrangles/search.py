import concurrent.futures as _futures

# Import our client factory
from .clients import get_client as _get_client
from . import _ai_mode


def find_links(
    queries: str | list,
    client: str = "serpapi",
    client_config: dict | None = None,
    n_results: int = 10,
    threads: int = 10,
    **kwargs
) -> dict | list:
    """
    Perform web searches using a specified client (default: SerpAPI) to find links.
    """
    if client_config is None: client_config = {}
        
    search_client = _get_client(client, client_config)
    
    return search_client.search_batch(
        queries, 
        n_results=n_results, 
        threads=threads, 
        **kwargs
    )


def ai_mode(
    queries: str | list,
    query_config: list,
    client: str = "serpapi",
    client_config: dict | None = None,
    threads: int = 10,
    include_raw_response: bool = False,
    **kwargs
) -> dict | list:
    """
    Search Google AI Mode using a shared list of single-entry query dictionaries.

    Each response contains ai_mode_result (compact section content),
    ai_mode_result_complete (section blocks, references and meta_data with
    srsltid URL parameters and image fields removed),
    and ai_mode_markdown (the provider's original Markdown string).
    Compact pricing lists align with references by position. Unpriced references
    have site-name keys with empty values. Multiple offers repeat their URL;
    prices without an identifiable source URL pair with an empty reference.
    A string query returns one response; a list returns responses in input order.
    Blank queries return a Skipped response without calling the provider.
    """
    if client_config is None:
        client_config = {}

    headings = _ai_mode.query_headings(query_config)
    kwargs = _ai_mode.request_parameters(kwargs)
    if not isinstance(threads, int) or isinstance(threads, bool) or threads < 1:
        raise ValueError("threads must be a positive integer.")
    scalar = not isinstance(queries, list)
    normalized = [_ai_mode.normalize_query(q) for q in ([queries] if scalar else queries)]
    if not any(normalized):
        responses = [
            _ai_mode.normalize_response({}, q, headings, i, status="Skipped",
                                        include_raw_response=include_raw_response)
            for i, q in enumerate(normalized, 1)
        ]
        return responses[0] if scalar else responses

    search_client = _get_client(client, client_config)

    return search_client.search_batch(
        normalized[0] if scalar else normalized,
        threads=threads,
        search_mode="ai",
        query_config=query_config,
        include_raw_response=include_raw_response,
        **kwargs
    )


def retrieve_link_content(
    urls: str | list,
    client: str = "google_url_context",
    client_config: dict | None = None,
    prompt: str | None = None,
    model_id: str = "models/gemini-3-flash-preview",
    output_format: str = "json",
    threads: int = 10
) -> dict | list:
    """
    Retrieve formatted content from web URLs using a specified client.
    """
    if client_config is None: client_config = {}
        
    retriever = _get_client(client, client_config)
    
    is_scalar = False
    if not isinstance(urls, list):
        is_scalar = True
        urls = [urls]

    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = list(executor.map(
            lambda u: retriever.retrieve(
                url=u, 
                prompt=prompt, 
                model_id=model_id,
                output_format=output_format
            ),
            urls
        ))

    if is_scalar:
        return results[0]

    return results
