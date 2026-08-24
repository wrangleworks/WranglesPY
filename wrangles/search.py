import concurrent.futures as _futures

# Import our client factory
from .clients import get_client as _get_client
from .clients.serp_api import ai_mode_payload
from . import utils as _utils


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
    api_key: str | None = None,
    prompt: str | None = None,
    threads: int = 10,
    country: str = "us",
    language: str = "en",
    location: str | None = None,
    no_cache: bool = False,
    include_raw_response: bool = False,
    **kwargs,
) -> dict | list:
    """Search and synthesize cited content with SerpAPI Google AI Mode."""
    if not isinstance(threads, int) or isinstance(threads, bool) or threads < 1:
        raise ValueError("threads must be at least 1")

    is_scalar = not isinstance(queries, list)
    query_list = [queries] if is_scalar else queries
    if all(_utils.is_blank(query) for query in query_list):
        empty_results = [
            ai_mode_payload(
                query,
                index,
                metadata={
                    "language": language,
                    "country": country,
                    "location": location,
                },
            )
            for index, query in enumerate(query_list, start=1)
        ]
        return empty_results[0] if is_scalar else empty_results

    search_client = _get_client(
        client_name=client,
        config={"api_key": api_key},
    )
    return search_client.ai_mode_batch(
        queries,
        prompt=prompt,
        threads=threads,
        country=country,
        language=language,
        location=location,
        no_cache=no_cache,
        include_raw_response=include_raw_response,
        **kwargs,
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
