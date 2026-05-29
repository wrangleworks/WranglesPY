import concurrent.futures as _futures
import requests
import json
import time
import logging as _logging
import random

# Import our client factory
from .clients import get_client as _get_client


def import_soup():
    # Attempt to import BeautifulSoup
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        def BeautifulSoup(*args, **kwargs):
            raise ImportError(
                "beautifulsoup4 is required to parse HTML content in "
                "wrangles.search. Install `beautifulsoup4` to use this functionality."
            )

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


def _clean_headers(
    raw_headers_json: str,
    drop_info: str | list = None,
    keep_info: str | list = None
    ):
    """
    Parses JSON headers and removes specified keys based on the drop_info list.
    Supports exact matches and wildcard prefixes (e.g., 'x-*').
    
    :param raw_headers_json: The HTTP headers formatted as a JSON string.
    :param drop_info: A string or list of strings representing header keys to remove.
    :param keep_info: A string or list of strings representing header keys to keep.
    :return: A JSON string of the cleaned headers.
    """
    # Attempt to import BeautifulSoup
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        def BeautifulSoup(*args, **kwargs):
            raise ImportError(
                "beautifulsoup4 is required to parse HTML content in "
                "wrangles.search. Install `beautifulsoup4` to use this functionality."
            )

    if drop_info=='': drop_info=[
                            "x-*",              # Drops X-Frame-Options, X-Cache, X-Amz, etc.
                            "cf-*",             # Drops CF-RAY, cf-cache-status, etc.
                            "content-security-policy",
                            "strict-transport-security",
                            "server-timing",
                            "set-cookie",       # Crucial to drop to save space
                            "report-to",
                            "nel",
                            "alt-svc"
                        ]

    # Check that raw_headers_json is a string
    if not isinstance(raw_headers_json, str):
        raise TypeError(f"raw_headers_json must be a string, got {type(raw_headers_json)} instead.")
    if isinstance(drop_info, str): drop_info=[drop_info]
    # Only transform keep_info into a list if it exists
    if isinstance(keep_info, str) and keep_info: keep_info=[keep_info]

    try:
        headers_dict = json.loads(raw_headers_json)
    except (json.JSONDecodeError, TypeError):
        return raw_headers_json # Return as-is if it fails to parse
        
    cleaned_dict = {}
    drop_info_lower = [k.lower() for k in drop_info]
    keep_info_lower = [k.lower() for k in keep_info]
    
    for key, value in headers_dict.items():
        key_lower = key.lower()
        should_drop = False
        
        # Only drop headers when keep_info is not passed
        if not keep_info:
            for drop_item in drop_info_lower:
                # Handle wildcards (e.g., 'x-*')
                if drop_item.endswith('*'):
                    prefix = drop_item[:-1]
                    if key_lower.startswith(prefix):
                        should_drop = True
                        break
                # Handle exact matches
                elif key_lower == drop_item:
                    should_drop = True
                    break
        else:
            for keep_item in keep_info_lower:
                # Handle wildcards (e.g., 'x-*')
                if keep_item.endswith('*'):
                    prefix = keep_item[:-1]
                    if key_lower.startswith(prefix):
                        should_drop = False
                        break
                    else:
                        should_drop = True
                # Handle exact matches
                elif key_lower == keep_item:
                    should_drop = False
                    break
                else:
                    should_drop = True
                
        if not should_drop:
            cleaned_dict[key] = value
            
    return json.dumps(cleaned_dict, indent=2)


def _clean_html_head(
    raw_html: str,
    drop_info: str | list=None,
    keep_info: str | list=None
    ):
    """
    Parses an HTML string and structurally removes entire specified tags 
    (and their contents) using BeautifulSoup.
    
    :param raw_html: The raw HTML string to clean.
    :param drop_info: A single or list of HTML tag names to remove (e.g., ['script', 'style']).
    :param keep_info: A single or list of HTML tag names to keep (e.g., ['script', 'style']).
    :return: The cleaned HTML string.
    """
    # Attempt to import BeautifulSoup
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        def BeautifulSoup(*args, **kwargs):
            raise ImportError(
                "beautifulsoup4 is required to parse HTML content in "
                "wrangles.search. Install `beautifulsoup4` to use this functionality."
            )
    
    if drop_info=='': drop_info=[
                            "script",   # Removes all JavaScript functions and external script links
                            "style",    # Removes all inline CSS blocks
                            "noscript", # Removes fallback tracking pixels
                            "svg"       # Removes massive embedded vector graphics
                        ]
        
    # Check that raw_html is a string
    if not isinstance(raw_html, str):
        raise TypeError(f"raw_html must be a string, got {type(raw_html)} instead.")
    # Check to ensure that drop_info is a list
    if not isinstance(drop_info, list): drop_info=[drop_info]
    # Check to ensure that keep_info is a list
    if not isinstance(keep_info, list) and keep_info: keep_info=[keep_info]

    # Lowercase tags for matching
    drop_info_lower = [k.lower() for k in drop_info]
    keep_info_lower = [k.lower() for k in keep_info]

    if not raw_html:
        return ""
        
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Only drop tags when keep_info is not passed
    if not keep_info:
        for tag_name in drop_info_lower:
            for tag in soup.find_all(tag_name):
                tag.decompose() # Destroys the tag and everything inside it
    else:
        for tag in reversed(soup.find_all()):
            if tag.name.lower() not in keep_info_lower:
                # tag.decompose() # Destroys the tag and everything inside it
                tag.unwrap()  # removes tag, keeps contents

        # Remove stray text/newlines outside allowed tags
        for text in list(soup.find_all(string=True)):
            parent = text.parent

            # Remove whitespace-only nodes outside allowed tags
            if (
                parent.name.lower() not in keep_info_lower
                and text.strip() == ""
            ):
                text.extract()

            # Remove non-whitespace text outside allowed tags
            elif (
                parent.name.lower() not in keep_info_lower
            ):
                text.extract()

    return str(soup)


def retrieve_metadata(
    url: str,
    headers_to_drop: str | list=None,
    headers_to_keep: str | list=None,
    tags_to_drop: str | list=None,
    tags_to_keep: str | list=None
) -> tuple:
    """
    Connects to a URL using browser spoofing, extracts metadata, and streams the 
    HTML <head> block. Implements strict timeouts to prevent latency bloat. 
    Applies subtractive cleaning to both the headers and the HTML.
    
    :param url: The target webpage URL.
    :param headers_to_drop: A string or list of strings representing header keys to remove.
    :param headers_to_keep: A string or list of strings representing header keys to keep. Overrides headers_to_drop.
    :param tags_to_drop: A single or list of HTML tag names to remove (e.g., ['script', 'style']).
    :param tags_to_keep: A single or list of HTML tag names to keep (e.g., ['script', 'style']). Overrides tags_to_drop.
    :return: tuple: (size_in_bytes (int), cleaned_headers (str), cleaned_html (str))
    """
    if headers_to_drop and headers_to_keep:
        _logging.info(f"headers_to_keep overriding headers_to_drop")
    if tags_to_drop and tags_to_keep:
        _logging.info(f"tags_to_keep overriding tags_to_drop")

    # Input Validation & Cleaning
    if not url or not isinstance(url, str):
        return "Invalid Data", "{}", ""
    
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", # Chrome Windows
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15", # Safari Mac
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0", # Edge Windows
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0" # Firefox Linux
    ]

    # Disguise as a random, fully-featured browser coming from a search engine
    request_headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com"
    }

    try:
        # 2. Connection Phase (Max 3s to connect, max 5s for first byte)
        response = requests.get(url, headers=request_headers, stream=True, timeout=(3, 5))
        
        if response.status_code != 200:
            error_msg = f"Blocked: HTTP {response.status_code}"
            raw_headers = json.dumps(dict(response.headers), indent=2)
            cleaned_headers = _clean_headers(raw_headers, headers_to_drop, headers_to_keep)
            response.close()
            return error_msg, cleaned_headers, ""
            
        # 3. Metadata Extraction
        size = response.headers.get('Content-Length')
        size_out = int(size) if size is not None else 0
        raw_headers = json.dumps(dict(response.headers), indent=2)
        
        # 4. Streaming Phase
        html_content = ""
        max_bytes = 50000 # Absolute payload limit just in case a </head> tag is missing
        bytes_read = 0
        
        start_time = time.time()
        max_duration = 3.0 # Absolute execution stopwatch limit (seconds)
        
        for chunk in response.iter_content(chunk_size=512):
            # Enforce the strict stopwatch
            if time.time() - start_time > max_duration:
                break 
                
            if chunk:
                html_content += chunk.decode('utf-8', errors='ignore')
                bytes_read += len(chunk)
                
                # Snip the stream the millisecond we find the closing head tag
                if '</head>' in html_content.lower():
                    split_point = html_content.lower().find('</head>') + 7
                    html_content = html_content[:split_point]
                    break
                    
                # Enforce the byte limit
                if bytes_read >= max_bytes:
                    break
                    
        response.close()
        
        # 5. Cleaning Phase
        final_headers = _clean_headers(raw_headers, headers_to_drop, headers_to_keep)
        final_html = _clean_html_head(html_content, tags_to_drop, tags_to_keep)
        
        # End State: Return the fully optimized, scraped, and sanitized data tuple
        return size_out, final_headers, final_html
            
    except requests.exceptions.Timeout:
        return "Error: Connection Timed Out", "{}", ""
    except Exception as e:
        return f"Error: {str(e)}", "{}", ""
