import concurrent.futures as _futures
import requests
import json
import time
import logging
from bs4 import BeautifulSoup

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
    drop_info: str | list = None
    ):
    """
    Parses JSON headers and removes specified keys based on the drop_info list.
    Supports exact matches and wildcard prefixes (e.g., 'x-*').
    
    :param raw_headers_json: The HTTP headers formatted as a JSON string.
    :param drop_info: A string or list of strings representing header keys to remove.
    :return: A JSON string of the cleaned headers.
    """

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
    # Check to ensure drop_info is a list or sting, convert to list
    if not isinstance(drop_info, (str, list)):
        raise TypeError(f"drop_info must be string or list, got {type(drop_info)} instead.")
    if isinstance(drop_info, str): drop_info=[drop_info]

    try:
        headers_dict = json.loads(raw_headers_json)
    except (json.JSONDecodeError, TypeError):
        return raw_headers_json # Return as-is if it fails to parse
        
    cleaned_dict = {}
    drop_info_lower = [k.lower() for k in drop_info]
    
    for key, value in headers_dict.items():
        key_lower = key.lower()
        should_drop = False
        
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
    :return: The cleaned HTML string.
    """
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
    if not isinstance(keep_info, list): drop_info=[keep_info]

    if not raw_html:
        return ""
        
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    if not keep_info:
        for tag_name in drop_info:
            for tag in soup.find_all(tag_name):
                tag.decompose() # Destroys the tag and everything inside it
    else:
        for tag in soup.find_all(tag_name):
            if tag not in keep_info:
                tag.decompose() # Destroys the tag and everything inside it

    return str(soup)


def retrieve_metadata(
    url: str,
    headers_to_drop: str | list=None,
    tags_to_drop: str | list=None
) -> tuple:
    """
    Connects to a URL using browser spoofing, extracts metadata, and streams the 
    HTML <head> block. Implements strict timeouts to prevent latency bloat. 
    Applies subtractive cleaning to both the headers and the HTML.
    
    :param url: The target webpage URL.
    :param headers_to_drop: A string or list of strings representing header keys to remove.
    :param tags_to_drop: A single or list of HTML tag names to remove (e.g., ['script', 'style']).
    :return: tuple: (size_in_bytes (int), cleaned_headers (str), cleaned_html (str))
    """
    # Add log stating keep will override drop
    # Input Validation & Cleaning
    if not url or not isinstance(url, str):
        return "Invalid Data", "{}", ""
    
    # Check that headers_to_drop is a string
    if not isinstance(headers_to_drop, (str, list)):
        raise TypeError(f"headers_to_drop must be a string or list, got {type(headers_to_drop)} instead.")
    # Check to ensure tags_to_drop is a list or sting, convert to list
    if not isinstance(tags_to_drop, (str, list)):
        raise TypeError(f"tags_to_drop must be string or list, got {type(tags_to_drop)} instead.")

    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Disguise as a standard Chrome browser to bypass basic bot-blocking
    request_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    try:
        # 2. Connection Phase (Max 3s to connect, max 5s for first byte)
        response = requests.get(url, headers=request_headers, stream=True, timeout=(3, 5))
        
        if response.status_code != 200:
            error_msg = f"Blocked: HTTP {response.status_code}"
            raw_headers = json.dumps(dict(response.headers), indent=2)
            cleaned_headers = _clean_headers(raw_headers, headers_to_drop)
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
        final_headers = _clean_headers(raw_headers, headers_to_drop)
        final_html = _clean_html_head(html_content, tags_to_drop)
        
        # End State: Return the fully optimized, scraped, and sanitized data tuple
        return size_out, final_headers, final_html
            
    except requests.exceptions.Timeout:
        return "Error: Connection Timed Out", "{}", ""
    except Exception as e:
        return f"Error: {str(e)}", "{}", ""
