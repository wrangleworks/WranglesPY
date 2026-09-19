"""Shared AI-search cleanup and the original deterministic compact projection."""

from collections.abc import Mapping
import html
import re
from urllib.parse import parse_qsl, urlsplit

from . import web
from ._text_cleanup import _link_end
from .standardize import clean


_MARKDOWN_LINK = re.compile(r"!?\[((?:\\.|[^\]\\])*)\]\(")
_URL = re.compile(r"<?(?:https?://|www\.)[^\s<>]+>?", re.IGNORECASE)
_FOLLOW_UP = re.compile(
    r"^(?:if you (?:need|want|would like)\b.*\blet me know\b"
    r"|(?:would|do) you (?:like|want|need)\b|let me know (?:if|whether)\b)",
    re.IGNORECASE,
)
_PRICING_HEADING = re.compile(r"\b(?:price|prices|pricing)\b", re.IGNORECASE)
_TABLE_LINK_HEADING = re.compile(r"(?:product\s+)?(?:links?|urls?|pages?)|website", re.IGNORECASE)
_SPECIFICATION_HEADING = re.compile(r"\bspecifications?\b", re.IGNORECASE)
_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_GOOGLE_HOST = re.compile(r"(?:^|\.)google\.(?:com|[a-z]{2}|(?:co|com)\.[a-z]{2})$", re.IGNORECASE)


def _without_srsltid(match):
    original = match[0]
    # Preserve prose/Markdown delimiters after the URL, including nested paths.
    url = original.rstrip(".,;")
    suffix = original[len(url):]
    while url.endswith(")") and url.count(")") > url.count("("):
        url, suffix = url[:-1], ")" + suffix
    return web.clean_link(
        url, tracking_params={"srsltid"}, strip_scheme=False, preserve_encoding=True,
    ) + suffix


def prune_noise(value):
    """Copy provider content without image fields or srsltid URL parameters."""
    if isinstance(value, Mapping):
        return {key: prune_noise(child) for key, child in value.items()
                if key not in ("source_icon", "thumbnail")}
    if isinstance(value, list):
        return [prune_noise(child) for child in value]
    if isinstance(value, str):
        return _URL_IN_TEXT.sub(_without_srsltid, value)
    return value


def _plain_text(value):
    if not isinstance(value, str):
        return ""
    value = clean(value, unescape_unicode=True, latex_to_text=True,
                  unescape_html=True, uncurl_quotes=False)
    value = value.replace("Go to product viewer dialog for this item.", "")
    value = re.sub(r"</?a\b[^>]*>", "", value, flags=re.IGNORECASE)
    parts, pos = [], 0
    while match := _MARKDOWN_LINK.search(value, pos):
        end = _link_end(value, match.end())
        if end is None:
            break
        parts.extend((value[pos:match.start()], match[1]))
        pos = end
    parts.append(value[pos:])
    value = _URL.sub("", "".join(parts))
    value = re.sub(r"(\*\*|__)(.*?)\1", r"\2", value)
    value = re.sub(r"\\([\\`*{}\[\]()#+\-.!_])", r"\1", value)
    return " ".join(value.split()).strip()


def _table_lines(table, pricing=False):
    """Flatten each table data row while retaining its links and citation IDs."""
    if not isinstance(table, list):
        return
    rows = [row for row in table if isinstance(row, list)]
    if not rows:
        return
    headers, rows = (rows[0], rows[1:]) if len(rows) > 1 else ([], rows)
    headers = [_plain_text(cell.get("snippet") if isinstance(cell, Mapping) else cell) for cell in headers]
    price_columns = sum(bool(_PRICING_HEADING.search(header)) for header in headers)
    for row in rows:
        cells, links, indexes = [], [], []
        for cell in row:
            if isinstance(cell, Mapping):
                if isinstance(cell.get("snippet_links"), list):
                    links.extend(cell["snippet_links"])
                if isinstance(cell.get("reference_indexes"), list):
                    indexes.extend(cell["reference_indexes"])
                cell = cell.get("snippet", "")
            elif isinstance(cell, (int, float)):
                cell = str(cell)
            cells.append(_plain_text(cell))
        if not cells:
            continue
        context = {"snippet_links": links, "reference_indexes": indexes}
        if len(cells) == 2:
            yield ": ".join(cells), context
        elif len(cells) > 2:
            details = []
            for index, value in enumerate(cells[1:], 1):
                label = headers[index] if index < len(headers) else ""
                if pricing and _TABLE_LINK_HEADING.fullmatch(label):
                    continue
                if pricing and price_columns == 1 and _PRICING_HEADING.search(label):
                    label = ""
                if value:
                    details.append(f"{label}: {value}" if label else value)
            yield f"{cells[0]}: {'; '.join(details)}", context
        elif cells[0]:
            yield cells[0], context


def _visible_items(blocks, listed=False, pricing=False):
    """Yield visible text with source context, without turning metadata into prose."""
    if not isinstance(blocks, list):
        return
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        text = _plain_text(block.get("snippet"))
        if _FOLLOW_UP.match(text):
            continue
        if text:
            yield text, block, listed
        yield from _visible_items(block.get("list"), listed=True, pricing=pricing)
        yield from _visible_items(block.get("text_blocks"), listed=listed, pricing=pricing)
        for line, context in _table_lines(block.get("table"), pricing=pricing):
            if line:
                yield line, context, True


def _supplier_price(text, links):
    labels = sorted(dict.fromkeys(
        label for link in (links if isinstance(links, list) else [])
        if isinstance(link, Mapping) and (label := _plain_text(link.get("text")))
    ), key=len, reverse=True)
    prefix = r"(?:available|offered|sold)\s+(?:at|from|by)\s+"
    parts = None
    # Prefer the linked name so a supplier containing "for" or "at" stays whole.
    for label in labels:
        match = re.fullmatch(prefix + re.escape(label) + r"\s+(?:for|at)\s+(.+)", text, re.IGNORECASE)
        if match:
            parts = (label, match[1])
            break
    if parts is None:
        match = re.fullmatch(prefix + r"(.+?)\s+(?:for|at)\s+(.+)", text, re.IGNORECASE)
        parts = match.groups() if match else re.split(r"\s*[:：]\s*|\s+[–—]\s+", text, maxsplit=1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return {"text": text}
    supplier, detail = parts
    detail = detail.strip()
    # Remove navigation instructions rather than extracting just the first number:
    # ranges, currencies, quantity breaks and per-pack qualifiers must survive.
    detail = re.sub(r"\s+[-–—]\s+(?:check availability|view listing|order via|purchase through)\b.*$",
                    "", detail, flags=re.IGNORECASE)
    for label in labels:
        detail = re.sub(r"\s+(?:via|at|on|from)\s+" + re.escape(label) + r"[.!]?\s*$",
                        "", detail, flags=re.IGNORECASE)
    detail = re.sub(r"\s+(?:via|at|on|from)\s*[.!]?\s*$", "", detail, flags=re.IGNORECASE)
    detail = re.sub(r"^(?:available for|priced at|price is|price:)\s*", "", detail, flags=re.IGNORECASE)
    detail = detail.rstrip(" .")
    return {supplier.strip(): detail} if detail else {"text": text}


def _specification(text):
    """Keep each named specification separate, preserving unlabeled text too."""
    parts = re.split(r"\s*[:：]\s*|\s+[–—]\s+", text, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return {parts[0].strip(): parts[1].strip()}
    return {"text": text}


def _snippet_urls(value):
    """Visit source links attached to visible blocks, including lists and tables."""
    if isinstance(value, Mapping):
        links = value.get("snippet_links")
        if isinstance(links, list):
            for link in links:
                if isinstance(link, Mapping):
                    yield link.get("link")
        for key in ("list", "text_blocks", "table"):
            yield from _snippet_urls(value.get(key))
    elif isinstance(value, list):
        for child in value:
            yield from _snippet_urls(child)


def _source_url(value):
    """Return a clean web URL; Google product viewers do not identify a source."""
    if not isinstance(value, str):
        return ""
    # Require complete entities: html.unescape alone treats &currency as &curren
    # and corrupts the query parameter into a currency symbol followed by "cy".
    value = re.sub(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);",
                   lambda match: html.unescape(match[0]), value)
    value = value.replace(r"\&", "&").strip()
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            return ""
        if _GOOGLE_HOST.search(parts.hostname):
            query = dict(parse_qsl(parts.query))
            if (parts.path.rstrip("/") == "/search" and (query.get("ibp") == "oshop" or "prds" in query)
                    or parts.path.startswith("/shopping/product/")):
                return ""
    except ValueError:
        return ""
    return web.clean_link(value, strip_scheme=False, preserve_encoding=True)


def _reference_urls(complete, headings):
    candidates = [reference.get("link") for reference in complete.get("references", [])
                  if isinstance(reference, Mapping)]
    for heading in headings:
        candidates.extend(_snippet_urls(complete.get(heading)))
    urls, seen = [], set()
    for candidate in candidates:
        url = _source_url(candidate)
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    return urls


def _reference_sites(complete, urls):
    """Prefer the provider's site name, falling back to the URL's hostname."""
    names = {}
    for reference in complete.get("references", []):
        if isinstance(reference, Mapping):
            url = _source_url(reference.get("link"))
            name = _plain_text(reference.get("source"))
            if url and name:
                names.setdefault(url, name)
    return {url: names.get(url) or urlsplit(url).hostname.removeprefix("www.") for url in urls}


def _price_urls(price, context, references, sites):
    """Associate an offer using inline links, citation IDs or a unique site name."""
    links = context.get("snippet_links")
    urls = list(dict.fromkeys(
        url for link in (links if isinstance(links, list) else [])
        if isinstance(link, Mapping) and (url := _source_url(link.get("link")))
    ))
    if urls:
        return urls
    indexes = context.get("reference_indexes")
    cited_urls = list(dict.fromkeys(
        url for reference in references
        if isinstance(reference, Mapping) and isinstance(indexes, list)
        and "index" in reference and reference["index"] in indexes
        and (url := _source_url(reference.get("link")))
    ))
    if len(cited_urls) == 1:
        return cited_urls
    supplier = next(iter(price))
    if supplier == "text":
        return []

    def name_key(name):
        return re.sub(r"[\W_]+", "", name.casefold())

    # Different regional sites or multiple pages for one supplier are ambiguous.
    # A shared hostname alone does not establish where an offer was published.
    matches = [url for url in (cited_urls or sites)
               if name_key(sites[url]) == name_key(supplier)]
    return matches if len(matches) == 1 else []


def _align_pricing(complete, headings, pricing_items):
    """Build parallel pricing and reference lists without discarding either."""
    urls = _reference_urls(complete, headings)
    if not pricing_items:
        return {}, urls
    sites = _reference_sites(complete, urls)
    by_url = {heading: {} for heading in pricing_items}
    unlinked = []
    for heading, items in pricing_items.items():
        for text, context, _ in items:
            price = _supplier_price(text, context.get("snippet_links"))
            matches = _price_urls(price, context, complete.get("references", []), sites)
            if matches:
                for url in matches:
                    by_url[heading].setdefault(url, []).append(price)
            else:
                unlinked.append((heading, price))

    aligned, references = {heading: [] for heading in pricing_items}, []

    def append_row(url, name, prices):
        references.append(url)
        for heading in aligned:
            aligned[heading].append(dict(prices[heading]) if heading in prices else {name: ""})

    for url in urls:
        offers = {heading: values.get(url, []) for heading, values in by_url.items()}
        # Multiple offers for the same URL get separate rows and repeat that URL.
        for index in range(max(1, *(len(values) for values in offers.values()))):
            append_row(url, sites[url], {heading: values[index] for heading, values in offers.items()
                                         if index < len(values)})
    for heading, price in unlinked:
        append_row("", next(iter(price)), {heading: price})
    return aligned, references


def compact_result(complete, headings):
    """Return shallow content with pricing sections aligned to reference URLs."""
    result, pricing_items = {}, {}
    for heading in headings:
        pricing = bool(_PRICING_HEADING.search(heading))
        items = list(_visible_items(complete.get(heading), pricing=pricing))
        if pricing:
            result[heading] = []
            pricing_items[heading] = items
        elif _SPECIFICATION_HEADING.search(heading):
            result[heading] = [_specification(text) for text, _, _ in items]
        elif any(listed for _, _, listed in items):
            result[heading] = [text for text, _, _ in items]
        else:
            result[heading] = "\n\n".join(text for text, _, _ in items)
    aligned, references = _align_pricing(complete, headings, pricing_items)
    result.update(aligned)
    result["references"] = references
    return result
