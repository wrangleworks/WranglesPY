"""
Functions to perform web searches using various search engines.
"""
from typing import Union as _Union, Any, List, Tuple, Optional
import concurrent.futures as _futures
import html
import re
import logging
from datetime import datetime
import pytz


logger = logging.getLogger(__name__)


def _get_serpapi_client():
    try:
        from serpapi import Client as SerpApiClient
        return SerpApiClient
    except ImportError:
        raise ImportError(
            "The serpapi package is required for search functionality. "
            "Install it with: pip install serpapi"
        )


# =========================================================
# SECTION 1: HELPERS (Link Cleaning & Parsing)
# =========================================================

def _ensure_list(x: Any) -> List[str]:
    """Normalizes input (string or list) into a flat list of strings."""
    if x is None:
        return []
    if isinstance(x, str):
        return [x.strip()] if x.strip() else []
    if isinstance(x, (list, tuple, set)):
        out = []
        for i in x:
            if i and str(i).strip():
                out.append(str(i).strip())
        return out
    return [str(x)]


def _clean_link(url: str) -> str:
    """Aggressively strips 'srsltid' and other tracking parameters."""
    if not url: 
        return ""
    url = html.unescape(url)
    if "srsltid=" in url:
        url = url.split("srsltid=")[0]
    return url.rstrip("?&")


def _normalize_site(url: str) -> str:
    """
    Normalize a URL for deduplication purposes.
    Strips protocol, www, trailing slashes, and query parameters.
    """
    if not url:
        return ""
    
    # Clean the link first
    url = _clean_link(url)
    
    # Convert to lowercase
    url = url.lower()
    
    # Remove protocol
    url = re.sub(r'^https?://', '', url)
    
    # Remove www.
    url = re.sub(r'^www\.', '', url)
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Remove query parameters and fragments
    url = re.split(r'[?#]', url)[0]
    
    return url


def _format_card_price(item: dict) -> str:
    """Format Product Card prices (Price + Original + Tag)."""
    price = item.get("price", "")
    original = item.get("original_price")
    tag = item.get("tag")

    if original:
        formatted = f"{price} (Was: {original}"
        if tag:
            formatted += f" - {tag}"
        formatted += ")"
        return formatted
    return price


def convert_to_eastern(timestamp_str: str) -> datetime:
    """
    Convert ISO timestamp string to Eastern Time.
    
    :param timestamp_str: ISO format timestamp string
    :return: datetime object in Eastern Time
    """
    if not timestamp_str:
        return datetime.now(pytz.timezone('US/Eastern'))
    
    try:
        # Parse the timestamp (assuming UTC if no timezone info)
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Convert to Eastern Time
        eastern = pytz.timezone('US/Eastern')
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        return dt.astimezone(eastern)
    except (ValueError, AttributeError):
        # If parsing fails, return current time in Eastern
        return datetime.now(pytz.timezone('US/Eastern'))


def _parse_snippet_extensions(rich_snippet: dict, primary_currency: str) -> Tuple[Optional[float], str, str]:
    """
    Extract price/currency/availability from Organic Rich Snippets.
    Returns: (Price as Float, Currency String, Availability String)
    """
    price = None
    currency = ""
    availability = ""

    bottom = rich_snippet.get("bottom", {})
    detected = bottom.get("detected_extensions", {})
    
    # Placeholder for the raw string we find before cleaning
    raw_price_input = None

    # 1. Look in structured extensions
    if "price" in detected:
        raw_price_input = str(detected["price"])
        currency = detected.get("currency", "")

    # 2. Look in text extensions (always check for availability, check price if missing)
    extensions = bottom.get("extensions", [])
    for ext in extensions:
        # Force string conversion before operations
        ext_str = str(ext) 
        ext_lower = ext_str.lower()
        
        if "in stock" in ext_lower or "out of stock" in ext_lower:
            availability = ext_str
        # Check if this extension looks like a price (if we don't have one yet)
        elif raw_price_input is None and ext_str.strip().startswith(primary_currency):
            raw_price_input = ext_str

    # 3. Process the Price String (if found)
    if raw_price_input:
        # A. Handle Ranges: Split by " to ", " - ", etc. and take the lower bound
        # Matches "€19.56 to €21.09" -> takes "€19.56"
        split_match = re.split(r'\s+(?:to|-)\s+', raw_price_input, maxsplit=1, flags=re.IGNORECASE)
        lower_bound = split_match[0]

        # B. Backup Currency Extraction
        # If currency key was empty, try to extract non-numeric symbol from the string
        if not currency:
            # Find the first sequence of chars that isn't a digit, space, dot, or comma
            cur_match = re.search(r'([^\d\s\.,]+)', lower_bound)
            if cur_match:
                currency = cur_match.group(1)

        # C. Extract and Convert Price to Float
        # 1. Remove commas to handle "1,200"
        clean_str = lower_bound.replace(',', '')
        # 2. Find the first valid float number in the string
        num_match = re.search(r'(\d+\.?\d*)', clean_str)
        
        if num_match:
            try:
                price = float(num_match.group(1))
                price = round(price, 2)
            except ValueError:
                price = None

    return price, currency, availability


def google_search(query: str, api_key: str, config: dict = None, n_results: int = 10) -> dict:
    """
    Perform a Google search using SerpAPI.
    
    :param query: Search query string
    :param api_key: SerpAPI API key
    :param config: Configuration dictionary with search parameters
    :param n_results: Number of results to return
    :return: Raw SerpAPI response dictionary
    """
    if config is None:
        config = {
            "language": "en",
            "country": "us",
            "location": "Philadelphia, Pennsylvania"
        }
    
    try:
        SerpApiClient = _get_serpapi_client()
        client = SerpApiClient(api_key=api_key)
        
        params = {
            "q": query,
            "num": min(n_results, 100),
            "engine": "google"
        }
        
        # Add config parameters
        if "language" in config:
            params["hl"] = config["language"]
        if "country" in config:
            params["gl"] = config["country"]
        if "location" in config:
            params["location"] = config["location"]
        
        results = client.search(params)
        return results
    
    except Exception as e:
        logger.error(f"Error in google_search for query '{query}': {e}")
        return {}


# =========================================================
# MAIN FUNCTION (Row-by-Row Optimized)
# =========================================================

def fetch_serp_results(
    queries: Any, 
    api_key: str, 
    primary_currency: str = "$",  
    n_results: int = 5,
    config: dict = None
) -> Tuple[list, list, list]:
    """
    Row-by-Row execution. 
    - Deduplicates results across multiple queries using normalized links.
    - Injects search metadata (query, location, query_index).
    - Returns flat lists containing unique results for this row.
    
    :param queries: Single query string or list of query strings
    :param api_key: SerpAPI API key
    :param primary_currency: Primary currency symbol for price parsing (default: "$")
    :param n_results: Number of results to return per query (default: 5)
    :param config: Configuration dictionary with language, country, location
    :return: Tuple of (search_content, pricing_content, organic_results)
    """
    if config is None:
        config = {
            "language": "en", 
            "country": "us", 
            "location": "Philadelphia, Pennsylvania"
        }
        
    n_results = int(n_results)
    row_queries = _ensure_list(queries)
    
    # Accumulators for this row
    row_search_content = []
    row_pricing_content = []
    row_organic_results = []

    # --- NEW: Deduplication Tracker ---
    # Keeps track of normalized links seen across ALL queries for this row
    seen_links = set()

    for query_idx, q in enumerate(row_queries, start=1):
        try:
            res = google_search(q, api_key, config=config, n_results=n_results)
        except Exception as e:
            logger.error(f"Error for {q}: {e}")
            res = {}

        search_params = (res or {}).get("search_parameters", {})
        meta_q = search_params.get("q", q)
        meta_loc = search_params.get("location_used", "")
        meta_country = search_params.get("gl", "")
        meta_language = search_params.get("hl", "")

        search_meta = (res or {}).get("search_metadata", {})
        meta_id = search_meta.get("id","")
        meta_status = search_meta.get("status", "")
        meta_google_url = search_meta.get("google_url", "")
        meta_date_time = convert_to_eastern(search_meta.get("processed_at", "")).strftime("%Y-%m-%d %H:%M:%S")

        raw_organic = (res or {}).get("organic_results", []) or []
        raw_card_pricing = (res or {}).get("product_result", {}).get("pricing", []) or []

        # --- A. Process Organic Results with Deduplication ---
        for it in raw_organic:
            link = it.get("link", "")
            if not link:
                continue
            
            # Use the existing helper to normalize the link for comparison
            norm_link = _normalize_site(link)
            
            if norm_link in seen_links:
                logger.debug(f"Skipping duplicate link found in query {query_idx}: {link}")
                continue
            
            # Mark as seen
            seen_links.add(norm_link)

            # 1. Inject Metadata for Scoring
            it["query"] = meta_q
            it["search_id"] = meta_id
            it["status"] = meta_status
            it["location_used"] = meta_loc
            it["country"] = meta_country
            it["language"] = meta_language
            it["google_url"] = meta_google_url
            it["date_time"] = meta_date_time
            it["query_index"] = query_idx
            row_organic_results.append(it)

            # 2. Refined Search Content (Limit to n_results per query for the UI)
            # We check length of current query results added to keep the limit per query
            if len([x for x in row_search_content if x['query_index'] == query_idx]) < n_results:
                row_search_content.append({
                    "item_index": len(row_search_content) + 1,
                    "query_index": query_idx,
                    "query": meta_q,
                    "search_id": meta_id,
                    "status": meta_status,
                    "location_used": meta_loc,
                    "country": meta_country,
                    "language": meta_language,
                    "google_url": meta_google_url,
                    "date_time": meta_date_time,
                    "position": it.get("position", 0),
                    "title": html.unescape(str(it.get("title", ""))),
                    "link": _clean_link(link),
                    "snippet": html.unescape(str(it.get("snippet", ""))),
                    "matched_words": list(set(it.get("snippet_highlighted_words", []))),
                    "source": html.unescape(str(it.get("source", "")))
                })

        # --- B. Pricing Content (Rich Snippets from Organic) ---
        # Note: Since row_organic_results is already deduped, these will be unique
        pricing_idx_counter = len(row_pricing_content) + 1
        for it in [x for x in row_organic_results if x.get("query_index") == query_idx]:
            rich_snippet = it.get("rich_snippet", {})
            rs_price, rs_currency, rs_avail = _parse_snippet_extensions(rich_snippet, primary_currency)
            
            if rs_price: 
                row_pricing_content.append({
                    "item_index": pricing_idx_counter,
                    "price": rs_price,
                    "currency": rs_currency,
                    "vendor": html.unescape(str(it.get("source", ""))),
                    **({"availability": rs_avail} if rs_avail else {}), # only add if found
                    "part_code_found": False, # placeholder, gets updated after scoring
                    "link": _clean_link(it.get("link", "")),
                    "description": html.unescape(str(it.get("snippet", ""))),
                    "query": meta_q,
                    "status": meta_status,
                    "date_time": meta_date_time,
                    "google_url": meta_google_url,
                    "data_source": "Rich Snippet",
                })
                pricing_idx_counter += 1

        # --- C. Product Cards ---
        for item in raw_card_pricing:
            card_link = item.get("link", "")
            norm_card_link = _normalize_site(card_link)
            
            # Deduplicate product cards as well
            if norm_card_link in seen_links:
                continue
            seen_links.add(norm_card_link)

            buying_options = item.get("buying_options", [])
            avail = buying_options[0] if buying_options else ""
            
            row_pricing_content.append({
                "item_index": pricing_idx_counter,
                "query": meta_q,
                "status": meta_status,
                "google_url": meta_google_url,
                "date_time": meta_date_time,
                "data_source": "Product Card",
                "vendor": html.unescape(str(item.get("name", ""))),
                "price": _format_card_price(item),
                "currency": primary_currency, # this should be the currency found, not input
                "availability": avail,
                "link": _clean_link(card_link),
                "description": html.unescape(str(item.get("description", ""))),
                "source": html.unescape(str(it.get("source", "")))
            })
            pricing_idx_counter += 1

    return row_search_content, row_pricing_content, row_organic_results


def _search_single_query(
    query: str,
    api_key: str,
    n_results: int,
    include_prices: bool,
    kwargs: dict = None
) -> list:
    """
    Perform a single web search using SerpAPI.
    
    :param query: Search query string
    :param api_key: SerpAPI API key
    :param n_results: Number of results to return
    :param include_prices: Include price information if available
    :param kwargs: Additional SerpAPI parameters (gl, hl, num, etc.)
    :return: List of search results
    """
    query_str = str(query).strip().lower()
    if query is None or not query_str or query_str in ('none', 'nan', 'nat'):
        return []
    
    if kwargs is None:
        kwargs = {}
    
    try:
        SerpApiClient = _get_serpapi_client()
        client = SerpApiClient(api_key=api_key)
        
        params = {
            "q": str(query).strip(),
            "num": min(n_results, 100),  
            **kwargs
        }
        
        results = client.search(params)

        organic_results = results.get("organic_results", [])
        
        formatted_results = []
        for idx, result in enumerate(organic_results[:n_results]):
            result_dict = {
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "position": result.get("position", idx + 1)
            }
            
            if include_prices and "price" in result:
                result_dict["price"] = result.get("price")
            
            formatted_results.append(result_dict)
        
        return formatted_results
    
    except Exception as e:
        return [{"error": str(e), "query": query}]


def web(
    input: _Union[str, list],
    api_key: str,
    n_results: int = 10,
    include_prices: bool = False,
    threads: int = 10,
    **kwargs
) -> _Union[list, list]:
    """
    Perform web searches using SerpAPI.
    
    >>> wrangles.search.web(
    >>>     "best python libraries 2024",
    >>>     api_key="your_api_key",
    >>>     n_results=5
    >>> )
    [
        {
            "title": "...",
            "link": "https://...",
            "snippet": "...",
            "position": 1
        },
        ...
    ]
    
    :param input: Search query or list of queries
    :param api_key: SerpAPI API key
    :param n_results: Number of results to return per query (default 10, max 100)
    :param include_prices: Include price information if available (default False)
    :param threads: Number of concurrent threads for parallel processing (default 10)
    :param kwargs: Additional SerpAPI parameters:
        - gl: Country code (e.g., 'us', 'uk')
        - hl: Language code (e.g., 'en', 'es')
        - location: Location for search results
        - device: Device type ('desktop', 'mobile', 'tablet')
    :return: List of search results for each query. If input was a string, returns a single list.
             If input was a list, returns a list of lists.
    """
    if not api_key:
        raise ValueError("api_key is required")
    
    if not isinstance(n_results, int) or n_results < 1:
        raise ValueError("n_results must be a positive integer")
    
    if n_results > 100:
        raise ValueError("n_results cannot exceed 100")

    input_was_scalar = False
    if not isinstance(input, list):
        input_was_scalar = True
        input = [input]
    
    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = list(executor.map(
            _search_single_query,
            input,
            [api_key] * len(input),
            [n_results] * len(input),
            [include_prices] * len(input),
            [kwargs] * len(input)
        ))
    
    if input_was_scalar:
        return results[0]
    
    return results