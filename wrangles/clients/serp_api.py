import concurrent.futures as _futures
import re
from typing import Union as _Union

# Import our new core web helpers
from .. import web as _web

def _extract_target_sites(query: str) -> list[str]:
    """Extract site:domain filters from query using simple token parsing."""
    if not query:
        return []

    return [
        token.split("site:", 1)[1].lower().rstrip(".,")
        for token in str(query).split()
        if token.lower().startswith("site:")
        and len(token.split("site:", 1)) > 1
    ]

def _extract_availability(extensions) -> str | None:
    """Infer availability from rich_snippet extensions text."""
    if not extensions:
        return None

    for item in extensions:
        if not item: continue
        s = str(item).strip().lower()

        if "in stock" in s: return "in stock"
        if "out of stock" in s: return "out of stock"
        if "backorder" in s or "back order" in s: return "backorder"
        if "preorder" in s or "pre-order" in s: return "preorder"
        if "available" in s: return "available"

    return None

def _extract_pricing_from_result(result: dict) -> dict:
    """
    Extract pricing info from a single organic result.
    Prefer rich_snippet.bottom.detected_extensions for structured fields.
    Falls back to regex parsing on the snippet if structured price is missing.
    """
    rich = result.get("rich_snippet") or {}
    bottom = rich.get("bottom") or {}
    detected = bottom.get("detected_extensions") or {}
    extensions = bottom.get("extensions") or []

    price = detected.get("price")
    currency = detected.get("currency")
    availability = _extract_availability(extensions)

    if price is None:
        snippet = result.get("snippet", "")
        currency_symbol = None
        raw_price = None

        prefix_match = re.search(r"([$£€]|C\$|CA\$|\bCAD\b|\bMXN\b|Mex\$|\bEUR\b)\s*(\d+(?:[.,]\d+)*)", snippet, re.IGNORECASE)
        if prefix_match:
            currency_symbol = prefix_match.group(1)
            raw_price = prefix_match.group(2)
        else:
            suffix_match = re.search(r"(\d+(?:[.,]\d+)*)\s*([$£€]|\bCAD\b|\bMXN\b|\bEUR\b)", snippet, re.IGNORECASE)
            if suffix_match:
                raw_price = suffix_match.group(1)
                currency_symbol = suffix_match.group(2)
                
        if currency_symbol and raw_price:
            if ',' in raw_price and '.' in raw_price:
                if raw_price.rfind(',') > raw_price.rfind('.'):
                    price_str = raw_price.replace('.', '').replace(',', '.')
                else:
                    price_str = raw_price.replace(',', '')
            elif ',' in raw_price:
                if re.search(r',\d{2}$', raw_price):
                    price_str = raw_price.replace(',', '.')
                else:
                    price_str = raw_price.replace(',', '')
            else:
                price_str = raw_price
            
            try:
                price = float(price_str)
                currency = currency_symbol.upper()
            except ValueError:
                pass

    if price is None and not currency and not availability:
        return {}

    return {
        "price": price,
        "currency": currency,
        "availability": availability,
    }


class SerpApiWranglesClient:
    def __init__(self, api_key: str = None):
        if not api_key or str(api_key).strip().lower() in ("", "none", "null"):
            import os
            self.api_key = os.environ.get("SERPAPI_API_KEY")
        else:
            self.api_key = api_key
            
        if not self.api_key:
            raise ValueError(
                "Search client requires a valid API key. "
                "Provide it in config or set the SERPAPI_API_KEY environment variable."
            )

        try:
            from serpapi import Client as SerpApiClient
            self.client_class = SerpApiClient
        except ImportError:
            raise ImportError(
                "The serpapi package is required for search functionality. "
                "Install it with: pip install serpapi"
            )

    def search_single(self, query: str, n_results: int = 5, kwargs: dict = None, query_index: int | None = None) -> dict:
        """Perform a single web search using SerpAPI."""
        query_str = str(query).strip().lower()
        if query is None or not query_str or query_str in ("none", "nan", "nat"):
            return {
                "search_metadata": {
                    "query_index": query_index,
                    "query": str(query).strip() if query else None,
                },
                "search_results": []
            }

        if kwargs is None: kwargs = {}

        try:
            client = self.client_class(api_key=self.api_key)
            params = {
                "q": str(query).strip(),
                "num": min(n_results, 100),
                **kwargs,
            }
            response = client.search(params)

            meta_raw = response.get("search_metadata", {}) or {}
            search_params = response.get("search_parameters", {}) or {}

            search_metadata = {
                "query_index": query_index,
                "query": str(query).strip(),
                "search_id": meta_raw.get("id"),
                "status": meta_raw.get("status"),
                "search_date": meta_raw.get("created_at"),
                "response_time": meta_raw.get("total_time_taken"),
                "json_endpoint": meta_raw.get("json_endpoint"),
                "google_url": _web.clean_link(meta_raw.get("google_url", "")), # Using new web helper
                "language": search_params.get("hl"),
                "country": search_params.get("gl"),
                "location": search_params.get("location_used"),
            }

            target_sites = _extract_target_sites(query)
            if target_sites:
                search_metadata["target_sites"] = target_sites

            organic_results = response.get("organic_results", []) or []
            search_results = []

            for result in organic_results[:n_results]:
                raw_snippet = result.get("snippet", "")

                result_dict = {
                    "google_rank": result.get("position", 0),
                    "title": result.get("title", ""),
                    "link": _web.clean_link(result.get("link", "")),       # Using new web helper
                    "source": result.get("source", ""),
                    "snippet": _web.clean_snippet(raw_snippet),            # Using new web helper
                    "highlighted_words": result.get("snippet_highlighted_words", []),
                    "missing_words": result.get("missing", []),
                    "pricing": _extract_pricing_from_result(result),
                    "query_index": query_index
                }
                search_results.append(result_dict)

            return {
                "search_metadata": search_metadata,
                "search_results": search_results,
            }

        except Exception as e:
            return {
                "search_metadata": {
                    "query_index": query_index,
                    "query": str(query).strip() if query else None,
                    "error": str(e),
                },
                "search_results": []
            }

    def search_batch(self, input_data: _Union[str, list], n_results: int = 10, threads: int = 10, **kwargs) -> _Union[dict, list]:
        """
        Perform parallel web searches using threads.
        """
        input_was_scalar = False
        if not isinstance(input_data, list):
            input_was_scalar = True
            input_data = [input_data]

        indexed = list(enumerate(input_data, start=1))

        with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
            results = list(executor.map(
                lambda t: self.search_single(
                    query=t[1],
                    n_results=n_results,
                    kwargs=kwargs,
                    query_index=t[0],
                ),
                indexed
            ))

        if input_was_scalar:
            return results[0]

        return results