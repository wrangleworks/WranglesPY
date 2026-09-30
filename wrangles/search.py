import concurrent.futures as _futures
import math as _math

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
    threads: int = None,
    thinking_level: str | None = None,
    request_timeout_seconds: float | None = None,
    **kwargs,
) -> dict | list:
    """
    Retrieve formatted content from web URLs using a specified client.
    Omitted model, thinking, concurrency, and deadline settings use AI configuration.
    The prompt is shared literally across URLs; column templates are recipe-only.
    Additional keyword arguments are Gemini GenerateContentConfig options.
    """
    is_scalar = not isinstance(urls, list)
    urls = [urls] if is_scalar else urls
    results = _retrieve_link_content(
        [(url, prompt) for url in urls], client=client, client_config=client_config,
        model_id=model_id, output_format=output_format, threads=threads,
        thinking_level=thinking_level, request_timeout_seconds=request_timeout_seconds,
        **kwargs,
    )
    return results[0] if is_scalar else results


def _retrieve_link_content(
    requests: list[tuple[str, str | None]],
    client: str = "google_url_context",
    client_config: dict | None = None,
    model_id: str = None,
    output_format: str = "json",
    threads: int = None,
    thinking_level: str | None = None,
    request_timeout_seconds: float | None = None,
    **kwargs,
) -> list:
    """Retrieve ordered URL/prompt pairs with one policy and bounded worker pool."""
    if thinking_level is not None and thinking_level not in ("minimal", "low", "medium", "high"):
        raise ValueError("thinking_level must be minimal, low, medium, or high.")
    if request_timeout_seconds is not None and (
        isinstance(request_timeout_seconds, bool)
        or not isinstance(request_timeout_seconds, (int, float))
        or not _math.isfinite(request_timeout_seconds)
        or request_timeout_seconds <= 0
    ):
        raise ValueError("request_timeout_seconds must be a positive finite number.")
    policy = _ai_config.resolve("search.retrieve_link_content", model=model_id)
    overrides = {
        key: value for key, value in (
            ("thinking_level", thinking_level),
            ("request_timeout_seconds", request_timeout_seconds),
        ) if value is not None
    }
    policy.update(overrides)
    if policy["provider"] != "google":
        raise ValueError("URL content retrieval currently supports only the 'google' provider.")
    if policy["protocol"] != "generate_content":
        raise ValueError("Google URL content retrieval requires the 'generate_content' protocol.")
    model_id = policy["model"]
    _ai_config.warn_if_deprecated(model_id, policy["provider"])
    threads = policy["default_concurrency"] if threads is None else threads
    if client_config is None: client_config = {}
        
    retriever = _get_client(client, client_config)
    
    def retrieve(request):
        url, prompt = request
        if isinstance(retriever, _GeminiURLContextClient):
            return retriever._retrieve(url, prompt, output_format, policy, **kwargs)
        return retriever.retrieve(
            url=url, prompt=prompt, model_id=model_id, output_format=output_format,
            **overrides, **kwargs,
        )

    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        return list(executor.map(retrieve, requests))
