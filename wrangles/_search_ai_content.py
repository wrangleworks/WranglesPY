"""Small, engine-independent helpers for AI-search Markdown and source URLs."""

from datetime import date, datetime
import html
import json
import re
from urllib.parse import parse_qsl, urlsplit

import yaml

from . import web
from ._text_cleanup import _link_end


_FRONTMATTER = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
_LINK = re.compile(r"!?\[(?:\\.|[^\]\\])*\]\(")
_URL = re.compile(r"https?://[^\s<>\"']+", re.I)
_MARKDOWN_ESCAPE = re.compile(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])")
_GOOGLE_HOST = re.compile(r"(?:^|\.)google\.(?:com|[a-z]{2}|(?:co|com)\.[a-z]{2})$", re.I)


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
    while match := _LINK.search(markdown, pos):
        end = _link_end(markdown, match.end())
        if end is None:
            break
        prose.append(markdown[pos:match.start()])
        destination = markdown[match.end():end - 1].strip()
        if not match[0].startswith("!"):
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
