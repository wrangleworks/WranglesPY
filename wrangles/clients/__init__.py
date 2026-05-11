from typing import Any

def get_client(client_name: str, config: dict = None) -> Any:
    """
    Factory function to instantiate and return a web retrieval/search client.
    
    :param client_name: The string identifier of the client (e.g., 'google_url_context', 'serpapi')
    :param config: A dictionary of configuration kwargs (like api_key) to pass to the client's __init__
    """
    if config is None:
        config = {}
        
    name = str(client_name).strip().lower()
    
    if name == "google_url_context":
        from .gemini import GeminiURLContextClient
        return GeminiURLContextClient(**config)
        
    elif name == "serpapi":
        from .serp_api import SerpApiWranglesClient
        return SerpApiWranglesClient(**config)
        
    else:
        raise ValueError(
            f"Unknown web client '{client_name}'. "
            "Available clients: 'google_url_context', 'serpapi'"
        )

__all__ = ['get_client']