"""AI Mode request validation and Markdown transport normalization."""

from collections.abc import Mapping
import math

from ._search_ai_content import split_markdown


def normalize_query(query):
    if query is None or (isinstance(query, float) and math.isnan(query)):
        return ""
    if not isinstance(query, str):
        raise TypeError("search.ai_mode requires one query string per row; explode query lists first.")
    return query.strip()


def request_parameters(kwargs):
    params = dict(kwargs)
    for name in ("n_results", "num", "google_domain", "query_config", "output"):
        if name in params:
            raise ValueError(f"search.ai_mode does not support {name}; it returns the Markdown answer and metadata.")
    for name in ("country", "language", "location", "gl", "hl", "uule"):
        if name in params and (params[name] is None or params[name] == ""):
            params.pop(name)
    for alias, parameter in (("country", "gl"), ("language", "hl")):
        if alias in params:
            value = params.pop(alias)
            if parameter in params and params[parameter] != value:
                raise ValueError(f"Conflicting {alias} and {parameter} values.")
            params[parameter] = value
    return params


def normalize_response(response, query, query_index=None, *, status=None, error=None,
                       include_raw_response=False):
    """Separate provider metadata from Markdown, without semantic interpretation."""
    body, metadata = "", {}
    if status != "Skipped" and not error:
        if isinstance(response, Mapping):
            # Error/processing responses may still be JSON despite output=md.
            provider = response.get("search_metadata")
            if isinstance(provider, Mapping):
                metadata["search_metadata"] = dict(provider)
            error = response.get("error")
            if not error and metadata.get("search_metadata", {}).get("status") not in ("Processing", "Queued"):
                error = "Expected Markdown from SerpAPI; received a JSON response."
        else:
            try:
                body, metadata = split_markdown(response)
            except ValueError as exc:
                body = response if isinstance(response, str) else ""
                error = str(exc)
    provider = metadata.get("search_metadata", {})
    if not isinstance(provider, dict):
        provider = {}
        error = error or "Invalid search_metadata in frontmatter."
    if status != "Skipped" and (not isinstance(provider.get("status"), str) or not provider["status"].strip()):
        error = error or "Missing or invalid search status in frontmatter."
    error = error or metadata.get("error")
    status = "Error" if error else status or provider.get("status", "Unknown")
    if status == "Success" and not body.strip():
        status, error = "Error", "Search returned an empty Markdown answer."
    metadata.update(query=query, query_index=query_index, status=status, error=error,
                    search_id=provider.get("id"))
    if include_raw_response:
        metadata["raw_response"] = response if isinstance(response, str) else None
    return {"ai_mode_results": body, "ai_mode_metadata": metadata}
