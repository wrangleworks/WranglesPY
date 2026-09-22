"""Small, engine-independent helpers for AI-search Markdown and source URLs."""

from datetime import date, datetime
import html
from itertools import groupby
import json
import re
from urllib.parse import parse_qsl, urlsplit

import yaml

from . import web
from ._text_cleanup import _link_end, map_markdown_prose


_FRONTMATTER = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
_LINK = re.compile(r"(?<!\\)!?\[")
_URL = re.compile(r"https?://[^\s<>\"']+", re.I)
_MARKDOWN_ESCAPE = re.compile(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])")
_GOOGLE_HOST = re.compile(r"(?:^|\.)google\.(?:com|[a-z]{2}|(?:co|com)\.[a-z]{2})$", re.I)


def _markdown_links(text):
    """Yield complete inline links, allowing escaped/nested labels and destinations."""
    pos = 0
    while match := _LINK.search(text, pos):
        label_start, depth = match.end(), 1
        pos = label_start
        while pos < len(text) and depth:
            if text[pos] == "\\":
                pos += 2
                continue
            if text[pos] == "[":
                depth += 1
            elif text[pos] == "]":
                depth -= 1
            pos += 1
        if depth or pos >= len(text) or text[pos] != "(":
            continue
        end = _link_end(text, pos + 1)
        if end is None:
            continue
        yield match.start(), end, text[label_start:pos - 1], text[pos + 1:end - 1], match[0].startswith("!")
        pos = end


def unlink_description(markdown, description_heading, section_headings):
    """Unlink description prose, retaining removed destinations as source evidence.

    This is a markup repair, not semantic section extraction. Other sections,
    citations and code examples stay intact; extract.ai handles their meaning.
    """
    if not isinstance(markdown, str):
        return markdown
    labels = list(dict.fromkeys([description_heading, *section_headings, "References"]))
    section = re.compile(
        r"^[ \t]{0,3}(?:#{1,6}[ \t]+)?(?:(?:[-+*]|\d+[.)])[ \t]+)?"
        r"(?:\*\*|__)?(?P<label>" + "|".join(re.escape(label) for label in labels) + r")"
        r"(?:\*\*|__)?(?:[ \t]*:(?:\*\*|__)?[ \t]*|[ \t]*(?:#+[ \t]*)?(?:\r?\n|$))",
        re.I | re.M,
    )
    description = description_heading.casefold()
    # Older responses sometimes omit the first heading but start with the description.
    active = not any(match["label"].casefold() == description for match in section.finditer(markdown))
    removed, definitions = {}, {}
    definition = re.compile(r"^ {0,3}\[([^\]\n]+)\]:[ \t]*(<[^>\n]+>|\S+)[^\n]*", re.M)

    def remember(label, destination):
        label = label.removesuffix("Go to product viewer dialog for this item.").rstrip()
        destination = destination.strip()
        if destination and destination not in removed:
            removed[destination] = label or "Source"
        return label

    def collect_definitions(prose):
        definitions.update((match[1].casefold(), match[2]) for match in definition.finditer(prose))
        return prose

    map_markdown_prose(markdown, collect_definitions, protect_links=False)

    def strip_links(prose):
        parts, pos = [], 0
        # Reuse the balanced destination scanner: URLs can contain parentheses.
        for start, end, label, destination, _ in _markdown_links(prose):
            parts.extend((prose[pos:start], remember(label, destination)))
            pos = end
        prose = "".join(parts) + prose[pos:]

        def reference(match):
            label, ref = match[1], match[2]
            target = definitions.get((ref or label).casefold())
            return remember(label, target) if target else match[0]

        # Resolved reference links only; ordinary citation numbers are not removed.
        prose = re.sub(r"(?<!\\)\[([^\]\n]+)\](?:\[([^\]\n]*)\])?", reference, prose)

        def anchor(match):
            href = re.search(r'''\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''', match[1], re.I)
            return remember(match[2], next(value for value in href.groups() if value is not None)) if href else match[2]

        prose = re.sub(r"<a\b([^>]*)>(.*?)</a\s*>", anchor, prose, flags=re.I | re.S)
        prose = re.sub(r"<(https?://[^<>\n]+)>", lambda match: remember("", match[1]), prose)

        def bare_url(match):
            url = match[0].rstrip(".,;:!?")
            for closing, opening in ((")", "("), ("]", "["), ("}", "{")):
                while url.endswith(closing) and url.count(closing) > url.count(opening):
                    url = url[:-1]
            remember("", url)
            return match[0][len(url):]

        return re.sub(r'''(?:https?://|www\.)[^\s<>"']+''', bare_url, prose, flags=re.I)

    def clean(prose):
        nonlocal active
        lines, chunks = [], []
        for line in prose.splitlines(keepends=True):
            if match := section.match(line):
                active = match["label"].casefold() == description
            elif re.match(r"^ {0,3}#{1,6}[ \t]+", line):
                active = False
            # Keep reference definitions outside description text available to the model.
            lines.append((active and not definition.match(line), line))
        # Keep consecutive description lines together so wrapped links remain whole.
        for should_strip, group in groupby(lines, key=lambda item: bool(item[0])):
            chunk = "".join(line for _, line in group)
            chunks.append(strip_links(chunk) if should_strip else chunk)
        return "".join(chunks)

    result = map_markdown_prose(markdown, clean, protect_links=False)
    missing = [(label, destination) for destination, label in removed.items() if destination not in result]
    if missing:
        result += f"\n\n### Links from {description_heading}\n\n" + "\n".join(
            f"- [{label}]({destination})" for label, destination in missing
        ) + "\n"
    return result


def split_markdown(response):
    """Return the untouched body and JSON-compatible frontmatter dictionary."""
    if not isinstance(response, str):
        raise ValueError("Expected a Markdown response.")
    match = _FRONTMATTER.match(response)
    if not match:
        raise ValueError("Missing or unterminated YAML frontmatter.")
    try:
        if any(isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken))
               for token in yaml.scan(match[1])):
            raise ValueError("YAML anchors are not supported in search metadata.")
        metadata = yaml.safe_load(match[1])
        if not isinstance(metadata, dict):
            raise ValueError("Search frontmatter must be an object.")

        def scalar(value):
            if isinstance(value, (datetime, date)):
                return value.isoformat()
            raise ValueError("Search metadata contains a non-JSON value.")

        metadata = json.loads(json.dumps(metadata, default=scalar, allow_nan=False))
    except (yaml.YAMLError, TypeError, ValueError, RecursionError) as error:
        # Do not echo provider text through parser exceptions.
        raise ValueError("Invalid YAML search metadata.") from error
    return response[match.end():], metadata


def source_url(value):
    """Clean a supplied HTTP(S) source URL without resolving or inventing URLs."""
    if not isinstance(value, str):
        return ""
    # Decode complete entities only: preserve query parameters such as &currency.
    value = re.sub(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);",
                   lambda match: html.unescape(match[0]), value)
    value = _MARKDOWN_ESCAPE.sub(r"\1", value).strip()
    if any(char.isspace() for char in value):
        return ""
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            return ""
        if _GOOGLE_HOST.search(parts.hostname):
            query = dict(parse_qsl(parts.query))
            if (parts.path.rstrip("/") == "/search" and (query.get("ibp") == "oshop" or "prds" in query)
                    or parts.path.startswith("/shopping/product/")):
                return ""
            if parts.path.rstrip("/") in ("/goto", "/url"):
                # Opaque Google IDs are not source URLs; unwrap explicit URLs only.
                destination = query.get("url", query.get("q", ""))
                target = urlsplit(destination)
                if target.scheme not in ("http", "https") or not target.hostname or _GOOGLE_HOST.search(target.hostname):
                    return ""
                value = destination
    except ValueError:
        return ""
    return web.clean_link(value, strip_scheme=False, preserve_encoding=True)


def markdown_urls(markdown):
    """Collect link destinations and literal URLs; never interpret section prose."""
    if not isinstance(markdown, str):
        return []
    candidates, prose, pos = [], [], 0
    for start, end, _, destination, is_image in _markdown_links(markdown):
        prose.append(markdown[pos:start])
        destination = destination.strip()
        if not is_image:
            if destination.startswith("<"):
                destination = destination[1:].partition(">")[0]
            elif destination:
                destination = destination.split()[0]
            candidates.append(destination)
        pos = end
    prose.append(markdown[pos:])
    for match in _URL.finditer(" ".join(prose)):
        url = _MARKDOWN_ESCAPE.sub(r"\1", match[0]).rstrip(".,;")
        for closing, opening in ((")", "("), ("]", "["), ("}", "{")):
            while url.endswith(closing) and url.count(closing) > url.count(opening):
                url = url[:-1]
        candidates.append(url)
    return list(dict.fromkeys(url for candidate in candidates if (url := source_url(candidate))))
