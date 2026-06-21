import concurrent.futures as _futures
import re
from typing import Union as _Union

# Import our new core web helpers
from .. import web as _web

_PRICING_KEYS = {
    "price",
    "pricing",
    "prices",
    "currency",
    "cost",
    "list_price",
    "unit_price",
    "availability",
    "in_stock",
    "stock",
    "lead_time",
    "minimum_order_quantity",
    "moq",
    "supplier_price",
}

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


def _safe_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    return []


def _is_empty_query(query) -> bool:
    query_str = str(query).strip().lower() if query is not None else ""
    return query is None or not query_str or query_str in ("none", "nan", "nat")


def _build_search_metadata(response: dict, query, query_index: int | None, search_type: str) -> dict:
    meta_raw = _safe_dict(response.get("search_metadata"))
    search_params = _safe_dict(response.get("search_parameters"))

    metadata = {
        "query_index": query_index,
        "query": str(query).strip() if query else None,
        "search_type": search_type,
        "search_id": meta_raw.get("id"),
        "status": meta_raw.get("status"),
        "search_date": meta_raw.get("created_at"),
        "response_time": meta_raw.get("total_time_taken"),
        "json_endpoint": meta_raw.get("json_endpoint"),
        "google_url": _web.clean_link(meta_raw.get("google_url", "")),
        "language": search_params.get("hl"),
        "country": search_params.get("gl"),
        "google_domain": search_params.get("google_domain"),
        "location": search_params.get("location_used"),
    }

    target_sites = _extract_target_sites(query)
    if target_sites:
        metadata["target_sites"] = target_sites

    return metadata


def _build_empty_classic_response(query, query_index: int | None) -> dict:
    return {
        "search_metadata": {
            "query_index": query_index,
            "query": str(query).strip() if query else None,
            "search_type": "classic",
        },
        "search_results": []
    }


def _build_empty_ai_response(query, query_index: int | None) -> dict:
    empty_meta = {
        "query_index": query_index,
        "query": str(query).strip() if query else None,
        "search_type": "ai",
    }
    return {
        "search_metadata": empty_meta,
        "product_details": {},
        "pricing": {},
        "misc": {},
        "content_like_results": [],
        "raw_response": {},
        "validation": _build_high_level_validation(empty_meta, {}, {}, []),
    }


def _build_error_classic_response(query, query_index: int | None, error: Exception) -> dict:
    return {
        "search_metadata": {
            "query_index": query_index,
            "query": str(query).strip() if query else None,
            "search_type": "classic",
            "error": str(error),
        },
        "search_results": []
    }


def _build_error_ai_response(query, query_index: int | None, error: Exception) -> dict:
    error_meta = {
        "query_index": query_index,
        "query": str(query).strip() if query else None,
        "search_type": "ai",
        "error": str(error),
    }
    return {
        "search_metadata": error_meta,
        "product_details": {},
        "pricing": {},
        "misc": {},
        "content_like_results": [],
        "raw_response": {},
        "validation": _build_high_level_validation(error_meta, {}, {}, []),
    }


def _flatten_one_level(payload: dict) -> dict:
    """Flatten nested dictionaries one level deep using parent_key_child_key naming."""
    out = {}
    for key, value in (payload or {}).items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                out[f"{key}_{sub_key}"] = sub_value
        else:
            out[key] = value
    return out


def _split_details_and_pricing(flattened: dict) -> tuple[dict, dict, dict]:
    product_details = {}
    pricing = {}
    misc = {}

    for key, value in (flattened or {}).items():
        key_l = str(key).lower()
        if key_l in _PRICING_KEYS or any(token in key_l for token in ("price", "currency", "cost", "availability", "stock", "lead_time", "moq")):
            pricing[key] = value
        elif key_l in ("sources", "citations", "references"):
            misc[key] = value
        else:
            product_details[key] = value

    return product_details, pricing, misc


def _extract_content_like_results(response: dict) -> list:
    """Collect response blocks that contain source/content-like material and normalize to dicts."""
    results = []
    candidates = [
        "organic_results",
        "sources",
        "citations",
        "references",
        "related_questions",
    ]

    for key in candidates:
        value = response.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    results.append(_flatten_one_level(item))
                elif item is not None:
                    results.append({"value": item, "source_type": key})
        elif isinstance(value, dict):
            results.append(_flatten_one_level(value))

    if not results:
        answer_box = _safe_dict(response.get("answer_box"))
        if answer_box:
            results.append(_flatten_one_level(answer_box))

    return results


def _build_high_level_validation(search_metadata: dict, product_details: dict, pricing: dict, content_like_results: list) -> dict:
    warnings = []
    if not product_details:
        warnings.append("missing_product_details")
    if not pricing:
        warnings.append("missing_pricing")
    if not content_like_results:
        warnings.append("missing_content_like_results")

    return {
        "is_valid": len(warnings) == 0,
        "warnings": warnings,
        "counts": {
            "product_detail_fields": len(product_details),
            "pricing_fields": len(pricing),
            "content_like_results": len(content_like_results),
        },
        "has_error": bool(search_metadata.get("error")),
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
        if _is_empty_query(query):
            return _build_empty_classic_response(query, query_index)

        if kwargs is None: kwargs = {}

        try:
            client = self.client_class(api_key=self.api_key)
            params = {
                "q": str(query).strip(),
                "num": min(n_results, 100),
                **kwargs,
            }
            response = client.search(params)

            search_metadata = _build_search_metadata(
                response=response,
                query=query,
                query_index=query_index,
                search_type="classic",
            )

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
            return _build_error_classic_response(query, query_index, e)

    def ai_mode_single(self, query: str, n_results: int = 5, kwargs: dict = None, query_index: int | None = None) -> dict:
        """Perform a single Google AI Mode search using SerpAPI and return a hybrid payload."""
        if _is_empty_query(query):
            return _build_empty_ai_response(query, query_index)

        if kwargs is None:
            kwargs = {}

        try:
            client = self.client_class(api_key=self.api_key)
            params = {
                "engine": "google_ai_mode",
                "q": str(query).strip(),
                "num": min(n_results, 100),
                **kwargs,
            }
            response = client.search(params)

            search_metadata = _build_search_metadata(
                response=response,
                query=query,
                query_index=query_index,
                search_type="ai",
            )

            flattened = _flatten_one_level(response)
            product_details, pricing, misc = _split_details_and_pricing(flattened)
            content_like_results = _extract_content_like_results(response)[:n_results]

            validation = _build_high_level_validation(
                search_metadata=search_metadata,
                product_details=product_details,
                pricing=pricing,
                content_like_results=content_like_results,
            )

            return {
                "search_metadata": search_metadata,
                "product_details": product_details,
                "pricing": pricing,
                "misc": misc,
                "content_like_results": content_like_results,
                "raw_response": response,
                "validation": validation,
            }

        except Exception as e:
            return _build_error_ai_response(query, query_index, e)

    def search_batch(
        self,
        input_data: _Union[str, list],
        n_results: int = 10,
        threads: int = 10,
        search_mode: str = "classic",
        **kwargs
    ) -> _Union[dict, list]:
        """
        Perform parallel web searches using threads.
        search_mode supports: classic, ai.
        """
        input_was_scalar = False
        if not isinstance(input_data, list):
            input_was_scalar = True
            input_data = [input_data]

        mode = str(search_mode or "classic").strip().lower()
        if mode in ("classic", "google", "web"):
            single_search_fn = self.search_single
        elif mode in ("ai", "ai_mode", "google_ai_mode"):
            single_search_fn = self.ai_mode_single
        else:
            raise ValueError("search_mode must be one of: classic, ai")

        indexed = list(enumerate(input_data, start=1))

        with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
            results = list(executor.map(
                lambda t: single_search_fn(
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