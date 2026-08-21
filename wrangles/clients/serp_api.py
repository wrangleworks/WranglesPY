import concurrent.futures as _futures
import json as _json
import math as _math
import re
from collections.abc import Mapping as _Mapping
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


def _is_blank_query(query) -> bool:
    if query is None:
        return True
    if isinstance(query, float) and _math.isnan(query):
        return True
    return str(query).strip().lower() in ("", "none", "nan", "nat")


def _json_safe(value):
    return _json.loads(_json.dumps(value, default=str))


def _ai_mode_payload(
    query,
    query_index: int | None,
    *,
    status: str = "Success",
    error: str | None = None,
    metadata: dict | None = None,
    search_results: list | None = None,
    answer_markdown=None,
    text_blocks: list | None = None,
) -> dict:
    metadata = metadata or {}
    return {
        "search_metadata": {
            "query_index": query_index,
            "query": None if query is None else str(query).strip(),
            "search_type": "ai_mode",
            "search_id": metadata.get("search_id"),
            "status": status,
            "search_date": metadata.get("search_date"),
            "response_time": metadata.get("response_time"),
            "json_endpoint": metadata.get("json_endpoint"),
            "google_url": metadata.get("google_url"),
            "language": metadata.get("language"),
            "country": metadata.get("country"),
            "location": metadata.get("location"),
        },
        "status": status,
        "error": error,
        "search_results": search_results or [],
        "extracted_content": {
            "answer_markdown": answer_markdown,
            "text_blocks": text_blocks or [],
        },
    }


def _result_items(section) -> list[dict]:
    if isinstance(section, list):
        return [item for item in section if isinstance(item, dict)]
    if not isinstance(section, dict):
        return []
    for key in ("results", "items", "products"):
        if isinstance(section.get(key), list):
            return [item for item in section[key] if isinstance(item, dict)]
    if any(key in section for key in ("link", "product_link", "title")):
        return [section]
    return []


def _coerce_price(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"\d+(?:[.,]\d+)*", value)
    if not match:
        return None
    number = match.group(0)
    if "," in number and "." in number:
        number = number.replace(",", "")
    elif "," in number:
        number = number.replace(",", ".") if re.search(r",\d{2}$", number) else number.replace(",", "")
    try:
        return float(number)
    except ValueError:
        return None


def _currency_from_price(value) -> str | None:
    if not isinstance(value, str):
        return None
    value_upper = value.upper()
    for token, currency in (
        ("CA$", "CAD"),
        ("C$", "CAD"),
        ("A$", "AUD"),
        ("AU$", "AUD"),
        ("NZ$", "NZD"),
        ("US$", "USD"),
        ("USD", "USD"),
        ("CAD", "CAD"),
        ("AUD", "AUD"),
        ("NZD", "NZD"),
        ("GBP", "GBP"),
        ("EUR", "EUR"),
        ("£", "GBP"),
        ("€", "EUR"),
    ):
        if token in value_upper:
            return currency
    return None


def _ai_mode_pricing(item: dict, source: str) -> dict:
    raw_price = item.get("price")
    if isinstance(raw_price, dict):
        price = raw_price.get("value", raw_price.get("extracted_value"))
        currency = raw_price.get("currency")
    else:
        price = item.get("extracted_price")
        if price is None:
            price = _coerce_price(raw_price)
        currency = item.get("currency") or _currency_from_price(raw_price)

    availability = item.get("availability") or item.get("stock")
    vendor = item.get("vendor") or item.get("merchant") or item.get("seller") or source
    pricing = {}
    if price is not None:
        pricing["price"] = price
    if currency:
        pricing["currency"] = currency
    if availability:
        pricing["availability"] = availability
    if vendor:
        pricing["vendor"] = vendor
    return pricing


def _ai_mode_result(item: dict, result_type: str, query_index: int | None) -> dict | None:
    raw_source = item.get("source")
    if isinstance(raw_source, dict):
        source = raw_source.get("name") or raw_source.get("title") or ""
        source_link = raw_source.get("link") or raw_source.get("url")
    else:
        source = raw_source or item.get("vendor") or item.get("merchant") or ""
        source_link = None

    link = item.get("link") or item.get("product_link") or item.get("url") or source_link
    if not link:
        return None

    snippet = item.get("snippet") or item.get("description") or ""
    result = {
        "query_index": query_index,
        "google_rank": 0,
        "result_type": result_type,
        "title": item.get("title") or item.get("name") or "",
        "link": _web.clean_link(link),
        "source": source,
        "snippet": _web.clean_snippet(snippet),
        "pricing": {},
    }
    if result_type in ("shopping_result", "inline_product"):
        result["pricing"] = _ai_mode_pricing(item, source)
    return result


def _normalize_ai_mode_results(response: dict, query_index: int | None) -> list[dict]:
    records = []
    seen = set()
    sections = (
        ("references", "reference"),
        ("quick_results", "quick_result"),
        ("shopping_results", "shopping_result"),
        ("inline_products", "inline_product"),
    )
    for section_name, result_type in sections:
        for item in _result_items(response.get(section_name)):
            record = _ai_mode_result(item, result_type, query_index)
            if record is None:
                continue
            dedupe_link = record["link"]
            if "://" not in dedupe_link:
                dedupe_link = f"https://{dedupe_link}"
            key = (
                _web.normalize_site(dedupe_link).lower().rstrip("/"),
                record["title"].strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

    for rank, record in enumerate(records, start=1):
        record["google_rank"] = rank
    return records


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

    def ai_mode_single(
        self,
        query,
        prompt: str | None = None,
        query_index: int | None = None,
        country: str = "us",
        language: str = "en",
        location: str | None = None,
        no_cache: bool = False,
        include_raw_response: bool = False,
        **kwargs,
    ) -> dict:
        """Perform one Google AI Mode search and normalize the provider response."""
        if _is_blank_query(query):
            return _ai_mode_payload(
                query,
                query_index,
                metadata={
                    "language": language,
                    "country": country,
                    "location": location,
                },
            )

        query_text = str(query).strip()
        prompt_text = prompt.strip() if prompt else ""
        request_query = f"{prompt_text}\n\n{query_text}" if prompt_text else query_text
        params = {
            **kwargs,
            "engine": "google_ai_mode",
            "q": request_query,
            "output": "json",
            "gl": country,
            "hl": language,
            "device": "desktop",
            "no_cache": no_cache,
        }
        if location:
            params["location"] = location

        try:
            client = self.client_class(api_key=self.api_key)
            response = client.search(params)
            if not isinstance(response, _Mapping):
                raise TypeError("SerpAPI returned a non-object response")
            response = dict(response)

            meta_raw = response.get("search_metadata") or {}
            search_params = response.get("search_parameters") or {}
            provider_error = response.get("error")
            provider_status = str(meta_raw.get("status") or "")
            failed = bool(provider_error) or provider_status.lower() in ("error", "failed", "failure")
            status = "Failure" if failed else "Success"
            error = str(provider_error) if provider_error else (
                provider_status if failed else None
            )
            metadata = {
                "search_id": meta_raw.get("id"),
                "search_date": meta_raw.get("created_at"),
                "response_time": meta_raw.get("total_time_taken"),
                "json_endpoint": meta_raw.get("json_endpoint"),
                "google_url": _web.clean_link(
                    meta_raw.get("google_ai_mode_url") or meta_raw.get("google_url", "")
                ) or None,
                "language": search_params.get("hl", language),
                "country": search_params.get("gl", country),
                "location": search_params.get("location_used") or search_params.get("location") or location,
            }
            result = _ai_mode_payload(
                query_text,
                query_index,
                status=status,
                error=error,
                metadata=metadata,
                search_results=[] if failed else _normalize_ai_mode_results(
                    response,
                    query_index,
                ),
                answer_markdown=None if failed else response.get("reconstructed_markdown"),
                text_blocks=[] if failed else response.get("text_blocks"),
            )
            if include_raw_response:
                result["raw_response"] = _json_safe(response)
            return result
        except Exception as error:
            return _ai_mode_payload(
                query_text,
                query_index,
                status="Failure",
                error=str(error),
                metadata={
                    "language": language,
                    "country": country,
                    "location": location,
                },
            )

    def ai_mode_batch(
        self,
        input_data: _Union[str, list],
        prompt: str | None = None,
        threads: int = 10,
        country: str = "us",
        language: str = "en",
        location: str | None = None,
        no_cache: bool = False,
        include_raw_response: bool = False,
        **kwargs,
    ) -> _Union[dict, list]:
        """Perform ordered Google AI Mode searches in parallel."""
        input_was_scalar = not isinstance(input_data, list)
        queries = [input_data] if input_was_scalar else input_data
        indexed = list(enumerate(queries, start=1))

        with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
            results = list(executor.map(
                lambda item: self.ai_mode_single(
                    query=item[1],
                    prompt=prompt,
                    query_index=item[0],
                    country=country,
                    language=language,
                    location=location,
                    no_cache=no_cache,
                    include_raw_response=include_raw_response,
                    **kwargs,
                ),
                indexed,
            ))

        return results[0] if input_was_scalar else results
