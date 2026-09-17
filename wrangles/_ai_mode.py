"""Shared configuration validation and lossless section grouping for AI Mode."""

from collections.abc import Mapping
from copy import deepcopy
import math
import unicodedata


def heading_key(value):
    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


def query_headings(query_config):
    """Return canonical headings from the same configuration used by Jinja."""
    if not isinstance(query_config, list) or not query_config:
        raise ValueError("query_config must be a non-empty list of single-entry dictionaries.")
    headings, seen = [], set()
    for entry in query_config:
        if not isinstance(entry, Mapping) or len(entry) != 1:
            raise ValueError("Each query_config dictionary must contain exactly one entry.")
        name, instruction = next(iter(entry.items()))
        if not isinstance(name, str) or not name.strip() or any(c in name for c in "\r\n"):
            raise ValueError("query_config keys must be non-empty, single-line strings.")
        if not isinstance(instruction, str):
            raise ValueError(f"The query_config instruction for {name!r} must be a string.")
        key = heading_key(name)
        if key in seen:
            raise ValueError(f"Duplicate query_config key: {name!r}.")
        seen.add(key)
        if key in ("references", "meta_data", "raw_response"):
            raise ValueError(f"{name!r} is a reserved AI Mode output key, not a query heading.")
        if key in ("base_query", "query_suffix"):
            if name != key:
                raise ValueError(f"Use the exact reserved configuration key {key!r}.")
        else:
            headings.append(name.strip())
    if not headings:
        raise ValueError("query_config must contain at least one requested heading.")
    return headings


def normalize_query(query):
    if query is None or (isinstance(query, float) and math.isnan(query)):
        return ""
    if not isinstance(query, str):
        raise TypeError("search.ai_mode requires one query string per row; explode query lists first.")
    return query.strip()


def request_parameters(kwargs):
    """Keep local output controls out of the provider request."""
    params = dict(kwargs)
    for name in ("n_results", "num", "google_domain"):
        if name in params:
            raise ValueError(f"search.ai_mode does not support {name}; all references are retained.")
    for alias, parameter in (("country", "gl"), ("language", "hl")):
        if alias in params:
            value = params.pop(alias)
            if parameter in params and params[parameter] != value:
                raise ValueError(f"Conflicting {alias} and {parameter} values.")
            params[parameter] = value
    params.setdefault("gl", "us")
    params.setdefault("hl", "en")
    return params


def normalize_response(response, query, headings, query_index=None, *,
                       status=None, error=None, include_raw_response=False):
    """Keep provider blocks/references intact and expose a separate Markdown string."""
    if not isinstance(response, Mapping):
        raise TypeError("AI Mode returned a non-object JSON response.")
    provider_meta = response.get("search_metadata")
    provider_meta = provider_meta if isinstance(provider_meta, Mapping) else {}
    parameters = response.get("search_parameters")
    parameters = parameters if isinstance(parameters, Mapping) else {}
    error = error or response.get("error")
    status = "Error" if error else status or provider_meta.get("status", "Unknown")
    warnings = []
    metadata = {
        "query": query,
        "query_index": query_index,
        "search_id": provider_meta.get("id"),
        "status": status,
        "error": error,
        "search_date": provider_meta.get("created_at"),
        "processed_at": provider_meta.get("processed_at"),
        "response_time": provider_meta.get("total_time_taken"),
        "google_ai_mode_url": provider_meta.get("google_ai_mode_url"),
        "json_endpoint": provider_meta.get("json_endpoint"),
        "markdown_endpoint": provider_meta.get("markdown_endpoint"),
        "country": parameters.get("gl"),
        "language": parameters.get("hl"),
        "device": parameters.get("device"),
        "location": parameters.get("location_used", parameters.get("location")),
        "missing_headings": [],
        "inferred_headings": [],
        "repeated_headings": [],
        "unmatched_sections": [],
        "unsectioned_text_blocks": [],
        "warnings": warnings,
    }
    result = {name: [] for name in headings}
    lookup = {heading_key(name): name for name in headings}
    seen = set()
    observed_headings = []

    def field(name, expected_type, default):
        value = response.get(name, default)
        if isinstance(value, expected_type):
            return value
        if value is not None:
            warnings.append(f"invalid_{name}")
            metadata.setdefault("invalid_fields", {})[name] = deepcopy(value)
        return default

    current = metadata["unsectioned_text_blocks"]
    for block in field("text_blocks", list, []):
        if isinstance(block, Mapping) and block.get("type") == "heading":
            label = block.get("snippet")
            name = lookup.get(heading_key(label)) if isinstance(label, str) else None
            observed_headings.append(name)
            if name is not None:
                if name in seen:
                    warnings.append(f"repeated_heading: {name}")
                    if name not in metadata["repeated_headings"]:
                        metadata["repeated_headings"].append(name)
                seen.add(name)
                current = result[name]
            else:
                section = {"heading": deepcopy(dict(block)), "text_blocks": []}
                metadata["unmatched_sections"].append(section)
                warnings.append(f"unexpected_heading: {label}")
                current = section["text_blocks"]
        else:
            # Preserve list/table structure, nested blocks and unfamiliar block types.
            current.append(deepcopy(block))
            if not isinstance(block, Mapping):
                warnings.append("invalid_text_block")

    # Google can omit the first heading while labeling subsequent sections.
    # Infer only opening paragraphs bounded by the second requested heading.
    leading = metadata["unsectioned_text_blocks"]
    if (
        status == "Success" and len(headings) > 1 and headings[0] not in seen
        and observed_headings and observed_headings[0] == headings[1] and leading
        and all(
            isinstance(block, Mapping) and block.get("type") == "paragraph"
            and isinstance(block.get("snippet"), str) and block["snippet"].strip()
            for block in leading
        )
    ):
        result[headings[0]].extend(leading)
        metadata["unsectioned_text_blocks"] = []
        metadata["inferred_headings"].append(headings[0])
        seen.add(headings[0])
        warnings.append(f"inferred_heading: {headings[0]}")

    references = field("references", list, [])
    result["references"] = []
    for position, reference in enumerate(references):
        if isinstance(reference, Mapping):
            result["references"].append(deepcopy(dict(reference)))
        else:
            warnings.append(f"invalid_reference: {position}")
            metadata.setdefault("invalid_fields", {})[f"references[{position}]"] = deepcopy(reference)

    markdown = field("reconstructed_markdown", str, "")
    if status not in ("Skipped", "Error"):
        metadata["missing_headings"] = [name for name in headings if name not in seen]
        warnings.extend(f"missing_heading: {name}" for name in metadata["missing_headings"])
        warnings.extend(f"empty_heading: {name}" for name in headings if name in seen and not result[name])
        if metadata["unsectioned_text_blocks"]:
            warnings.append("unsectioned_text_blocks")
        if not markdown:
            warnings.append("missing_reconstructed_markdown")
        if status != "Success":
            warnings.append(f"provider_status: {status}")

    reference_ids = {
        reference["index"] for reference in result["references"]
        if isinstance(reference.get("index"), int)
    }

    def check_citations(value):
        if isinstance(value, Mapping):
            indexes = value.get("reference_indexes", [])
            if isinstance(indexes, list):
                for index in indexes:
                    if not isinstance(index, int) or index not in reference_ids:
                        warning = f"unresolved_reference_index: {index}"
                        if warning not in warnings:
                            warnings.append(warning)
            for child in value.values():
                check_citations(child)
        elif isinstance(value, list):
            for child in value:
                check_citations(child)

    check_citations(response.get("text_blocks", []))
    if status == "Skipped":
        metadata["parse_status"] = "skipped"
    elif status == "Error":
        metadata["parse_status"] = "error"
    else:
        metadata["parse_status"] = "partial" if warnings else "complete"
    extra_fields = [key for key in response if key not in (
        "search_metadata", "search_parameters", "text_blocks", "references",
        "reconstructed_markdown", "error",
    )]
    if extra_fields:
        metadata["unmapped_fields"] = extra_fields
    result["meta_data"] = metadata
    if include_raw_response:
        result["raw_response"] = deepcopy(dict(response))
    return {"ai_mode_result": result, "ai_mode_markdown": markdown}
