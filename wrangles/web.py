import html
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_PARAMS = {
    "srsltid", "gclid", "gbraid", "wbraid", "fbclid",
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
}

def clean_link(url: str) -> str:
    """
    Remove known tracking query parameters and drop the http(s):// scheme 
    to return a cleaner link.
    """
    if not url:
        return ""

    url = html.unescape(url).strip()

    try:
        parts = urlsplit(url)
    except Exception:
        cleaned = re.sub(r"^https?://", "", url)
        return cleaned.rstrip("?&")

    if parts.query:
        params = parse_qsl(parts.query, keep_blank_values=True)
        filtered = [(k, v) for (k, v) in params if k.lower() not in TRACKING_PARAMS]
        new_query = urlencode(filtered, doseq=True)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    cleaned = re.sub(r"^https?://", "", url)
    return cleaned.rstrip("?&")


def normalize_site(url: str) -> str:
    """
    Normalizes a URL to a core path for deduplication.
    """
    if not url:
        return ""
    if "srsltid=" in url:
        url = url.split("srsltid=")[0].rstrip("?")
        
    try:
        parts = urlsplit(url)
        netloc = parts.netloc.replace("www.", "").replace("shop.", "")
        path = parts.path or ""
        if path == "/":
            path = ""
        return f"{netloc}{path}"
    except Exception:
        return url


def clean_snippet(snippet: str) -> str:
    """
    Clean snippet text: normalize whitespace, strip leading/trailing ellipses,
    de-dupe pipe-separated chunks, and remove repeated lead phrase occurrences.
    """
    if not snippet:
        return ""

    s = re.sub(r"\s+", " ", str(snippet)).strip()
    s = re.sub(r"^(?:\.\.\.|…)\s*", "", s)
    s = re.sub(r"\s*(?:\.\.\.|…)$", "", s)

    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        seen = set()
        deduped = []
        for p in parts:
            if not p: continue
            key = p.lower()
            if key in seen: continue
            seen.add(key)
            deduped.append(p)
        s = " | ".join(deduped).strip()

    m = re.match(r"^\s*([^.!?]{6,}?)\.(?:\s+|$)", s)
    if not m: return s

    lead = m.group(1).strip()
    if not lead: return s

    tail = s[m.end():]
    pattern = re.compile(rf"\b{re.escape(lead)}\.\s+", re.IGNORECASE)
    tail = pattern.sub("", tail)

    cleaned = f"{lead}. {tail}".strip()
    return re.sub(r"\s+", " ", cleaned).strip()


def is_product_url(url: str) -> int:
    """Scores a URL's likelihood of being a Product Detail Page (PDP)."""
    if not url: return 0

    parts = urlsplit(url)
    path = parts.path.lower()
    query = parts.query.lower()
    
    path_segments = [s for s in path.split('/') if s]
    num_segments = len(path_segments)
    
    last_segment_props = {'has_dash_and_digit': False, 'is_long_numeric': False}
    if path_segments:
        last_segment = path_segments[-1]
        if '-' in last_segment and any(char.isdigit() for char in last_segment):
            last_segment_props['has_dash_and_digit'] = True
        elif len(last_segment) > 5 and sum(c.isdigit() for c in last_segment) > 3 and '_' not in last_segment:
            last_segment_props['is_long_numeric'] = True
            
    score = 0
    hard_exit_triggers = []

    if num_segments == 0: hard_exit_triggers.append('is_root_domain')
    if num_segments == 1 and path_segments[0] in ['products', 'brands', 'industries']:
        hard_exit_triggers.append('is_toplevel_category')
    if 'brands' in path_segments: hard_exit_triggers.append('brands_page_pattern')
    if 'industries' in path_segments: hard_exit_triggers.append('industries_page_pattern')
    
    if hard_exit_triggers: return -2

    negative_pattern = re.compile(r'/(search|cart|account|login|blog|category)(/|\.|$)')
    file_extensions = ['.csv', '.jpg', '.jpeg', '.zip', '.docx', '.png']
    
    if negative_pattern.search(path) or any(path.endswith(ext) for ext in file_extensions):
        return -2

    if sum(1 for s in path_segments if s.isdigit()) >= 2: score -= 2
    if any(p in query for p in ['product_id=', 'pid=', 'item_id=', 'sku=']): score += 2
    if any(kw in path for kw in ['/product/', '/item/', '/sku/', '/p/', '/dp/']): score += 2
    
    try:
        products_index = path_segments.index('products')
        if num_segments > products_index + 2: score += 2
        elif num_segments == products_index + 2: score += 1
    except ValueError:
        pass

    if num_segments >= 3: score += 1
    if last_segment_props['has_dash_and_digit']: score += 2
    elif last_segment_props['is_long_numeric']: score += 2
        
    if score >= 3: return 2  
    elif score >= 1: return 1  
    return 0