import html
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from typing import Tuple

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



def is_product_url(url: str) -> Tuple[int, str]:
    """
    Scores a URL's likelihood of being a Product Detail Page (PDP).
    Returns a tuple: (score, summary_string).
    """
    if not url: 
        return 0, "Empty URL"

    # --- 1. Upfront Calculations & Property Analysis ---
    parts = urlsplit(url)
    path = parts.path.lower()
    query = parts.query.lower()
    
    path_segments = [s for s in path.split('/') if s]
    num_segments = len(path_segments)
    
    # i18n product plurals 
    product_plurals = {'products', 'produkte', 'produits', 'productos'}
    
    last_segment_props = {'has_dash_and_digit': False, 'is_long_numeric': False}
    if path_segments:
        last_segment = path_segments[-1]
        if '-' in last_segment and any(char.isdigit() for char in last_segment):
            last_segment_props['has_dash_and_digit'] = True
        elif len(last_segment) > 5 and sum(c.isdigit() for c in last_segment) > 3 and '_' not in last_segment:
            last_segment_props['is_long_numeric'] = True

    # --- 2. Apply Hard Exits (Negatives) ---
    if num_segments == 0: 
        return -2, "Root domain"
        
    if num_segments == 1 and (path_segments[0] in product_plurals or path_segments[0] in ['brands', 'industries']):
        return -2, f"Top-level category page (/{path_segments[0]})"
        
    if 'brands' in path_segments: 
        return -2, "Brands page pattern"
    if 'industries' in path_segments: 
        return -2, "Industries page pattern"

    negative_pattern = re.compile(r'/(search|cart|account|login|blog|category)(/|\.|$)')
    file_extensions = ['.csv', '.jpg', '.jpeg', '.zip', '.docx', '.png']
    
    neg_match = negative_pattern.search(path)
    if neg_match:
        return -2, f"Non-product keyword in path ({neg_match.group(1)})"
        
    if any(path.endswith(ext) for ext in file_extensions):
        return -2, "File extension detected"

    # --- 3. Initialize Score and Trackers ---
    score = 0
    triggers = []

    # --- 4. Apply Demotions ---
    if sum(1 for s in path_segments if s.isdigit()) >= 2: 
        score -= 2
        triggers.append("Archive/Repo Pattern (-2)")

    # --- 5. Apply Promotions (Positive Scoring) ---
    if any(p in query for p in ['product_id=', 'pid=', 'item_id=', 'sku=']): 
        score += 2
        triggers.append("ID in Query (+2)")
        
    if any(kw in path for kw in [
        '/product/', '/produkt/', '/produit/', '/producto/', 
        '/item/', '/itm/', '/sku/', '/p/', '/dp/', '/shop/'
    ]): 
        score += 2
        triggers.append("Product Keyword in Path (+2)")
    
    try:
        products_index = next(i for i, seg in enumerate(path_segments) if seg in product_plurals)
        if num_segments > products_index + 2: 
            score += 2
            triggers.append("Deep Product Hierarchy (+2)")
        elif num_segments == products_index + 2: 
            score += 1
            triggers.append("Sub-category Product Hierarchy (+1)")
    except StopIteration:
        pass

    if num_segments >= 3: 
        score += 1
        triggers.append("Deep Path (+1)")
        
    if last_segment_props['has_dash_and_digit']: 
        score += 2
        triggers.append("Slug with ID (+2)")
    elif last_segment_props['is_long_numeric']: 
        score += 2
        triggers.append("Long Numeric ID (+2)")
        
    # --- 6. Construct Summary & Final Score ---
    summary = ", ".join(triggers) if triggers else "No distinct product features found"
    
    if score >= 3: 
        return 2, summary
    elif score >= 1: 
        return 1, summary
    
    return 0, summary