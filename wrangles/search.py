import concurrent.futures as _futures

# Import our client factory
from .clients import get_client as _get_client
from .clients.gemini import GeminiURLContextClient as _GeminiURLContextClient
from . import _ai_mode
from . import ai_config as _ai_config


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
    client: str = "serpapi",
    client_config: dict | None = None,
    threads: int = 10,
    include_raw_response: bool = False,
    **kwargs
) -> dict | list:
    """Return ai_mode_results (Markdown body) and ai_mode_metadata (dictionary).

    Search uses output=md. Cleanup and semantic extraction belong in subsequent
    wrangles. Locale overrides are omitted unless supplied. A string query
    returns one response; a list returns responses in input order. Blank queries
    return Skipped without requiring a credential or calling the provider.
    """
    kwargs = _ai_mode.request_parameters(kwargs)
    if not isinstance(threads, int) or isinstance(threads, bool) or threads < 1:
        raise ValueError("threads must be a positive integer.")
    scalar = not isinstance(queries, list)
    normalized = [_ai_mode.normalize_query(q) for q in ([queries] if scalar else queries)]
    if not any(normalized):
        responses = [
            _ai_mode.normalize_response("", q, i, status="Skipped",
                                        include_raw_response=include_raw_response)
            for i, q in enumerate(normalized, 1)
        ]
        return responses[0] if scalar else responses
    search_client = _get_client(client, client_config or {})
    return search_client.search_batch(
        normalized[0] if scalar else normalized,
        threads=threads, search_mode="ai", include_raw_response=include_raw_response,
        **kwargs,
    )


def retrieve_link_content(
    urls: str | list,
    client: str = "google_url_context",
    client_config: dict | None = None,
    prompt: str | None = None,
    model_id: str = None,
    output_format: str = "json",
    threads: int = None
) -> dict | list:
    """
    Retrieve formatted content from web URLs using a specified client.
    Omitted model and concurrency settings are resolved from the AI configuration.
    """
    policy = _ai_config.resolve("search.retrieve_link_content", model=model_id)
    if policy["provider"] != "google":
        raise ValueError("URL content retrieval currently supports only the 'google' provider.")
    if policy["protocol"] != "generate_content":
        raise ValueError("Google URL content retrieval requires the 'generate_content' protocol.")
    model_id = policy["model"]
    _ai_config.warn_if_deprecated(model_id, policy["provider"])
    threads = policy["default_concurrency"] if threads is None else threads
    if client_config is None: client_config = {}
        
    retriever = _get_client(client, client_config)
    
    is_scalar = False
    if not isinstance(urls, list):
        is_scalar = True
        urls = [urls]

    def retrieve(url):
        if isinstance(retriever, _GeminiURLContextClient):
            return retriever._retrieve(url, prompt, output_format, policy)
        return retriever.retrieve(url=url, prompt=prompt, model_id=model_id, output_format=output_format)

    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = list(executor.map(retrieve, urls))

    if is_scalar:
        return results[0]

    return results
