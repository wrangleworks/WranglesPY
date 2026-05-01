import concurrent.futures as _futures

# Import our client factory
from .clients import get_client as _get_client


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


def retrieve_link_content(
    urls: str | list,
    client: str = "google_url_context",
    client_config: dict | None = None,
    prompt: str | None = None,
    model_id: str = "models/gemini-3-flash-preview",
    output_format: str = "markdown",
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