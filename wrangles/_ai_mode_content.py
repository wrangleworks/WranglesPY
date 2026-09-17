"""Remove AI Mode UI noise and build a shallow view of requested sections."""

from collections.abc import Mapping
import re

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
_SPECIFICATION_HEADING = re.compile(r"\bspecifications?\b", re.IGNORECASE)
_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


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


def _table_lines(table):
    """SerpAPI's table grid begins with a header row; keep each data row flat."""
    if not isinstance(table, list):
        return
    rows = [row for row in table if isinstance(row, list)]
    if not rows:
        return
    headers, rows = (rows[0], rows[1:]) if len(rows) > 1 else ([], rows)
    for row in rows:
        cells = []
        for cell in row:
            if isinstance(cell, Mapping):
                cell = cell.get("snippet", "")
            elif isinstance(cell, (int, float)):
                cell = str(cell)
            cells.append(_plain_text(cell))
        if not cells:
            continue
        if len(cells) == 2:
            yield ": ".join(cells)
        elif len(cells) > 2:
            details = []
            for index, value in enumerate(cells[1:], 1):
                label = _plain_text(headers[index]) if index < len(headers) else ""
                if value:
                    details.append(f"{label}: {value}" if label else value)
            yield f"{cells[0]}: {'; '.join(details)}"
        elif cells[0]:
            yield cells[0]


def _visible_items(blocks, listed=False):
    """Visit visible content only, never links, references or other metadata."""
    if not isinstance(blocks, list):
        return
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        text = _plain_text(block.get("snippet"))
        if _FOLLOW_UP.match(text):
            continue
        if text:
            yield text, block.get("snippet_links"), listed
        yield from _visible_items(block.get("list"), listed=True)
        yield from _visible_items(block.get("text_blocks"), listed=listed)
        for line in _table_lines(block.get("table")):
            if line:
                yield line, None, True


def _supplier_price(text, links):
    supplier, separator, detail = text.partition(":")
    if not separator or not supplier.strip() or not detail.strip():
        return text
    detail = detail.strip()
    # Remove navigation instructions rather than extracting just the first number:
    # ranges, currencies, quantity breaks and per-pack qualifiers must survive.
    detail = re.sub(r"\s+[-–—]\s+(?:check availability|view listing|order via|purchase through)\b.*$",
                    "", detail, flags=re.IGNORECASE)
    if isinstance(links, list):
        for link in links:
            label = _plain_text(link.get("text")) if isinstance(link, Mapping) else ""
            if label:
                detail = re.sub(r"\s+(?:via|at|on|from)\s+" + re.escape(label) + r"[.!]?\s*$",
                                "", detail, flags=re.IGNORECASE)
    detail = re.sub(r"\s+(?:via|at|on|from)\s*[.!]?\s*$", "", detail, flags=re.IGNORECASE)
    detail = re.sub(r"^(?:available for|priced at|price is|price:)\s*", "", detail, flags=re.IGNORECASE)
    detail = detail.rstrip(" .")
    return {supplier.strip(): detail} if detail else text


def compact_result(complete, headings):
    """Return heading values as strings, flat string lists or supplier dictionaries."""
    result = {}
    for heading in headings:
        items = list(_visible_items(complete.get(heading)))
        pricing = bool(_PRICING_HEADING.search(heading))
        if pricing:
            result[heading] = [_supplier_price(text, links) for text, links, _ in items]
        elif _SPECIFICATION_HEADING.search(heading) or any(listed for _, _, listed in items):
            result[heading] = [text for text, _, _ in items]
        else:
            result[heading] = "\n\n".join(text for text, _, _ in items)
    result["references"] = [
        reference["link"] for reference in complete.get("references", [])
        if isinstance(reference, Mapping) and isinstance(reference.get("link"), str)
        and reference["link"].strip()
    ]
    return result
