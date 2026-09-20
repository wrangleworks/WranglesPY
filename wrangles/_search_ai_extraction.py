"""Validate model-structured AI-search content without interpreting product prose."""

from collections import Counter
from collections.abc import Mapping
import math
from urllib.parse import urlsplit

from ._search_ai_content import markdown_urls, source_url


def format_product_result(extracted, markdown, *, description, specifications, pricing):
    """Validate evidence URLs and reference IDs, retaining independent offer rows.

    Relevance, supplier association, cleanup and price interpretation belong to
    extract.ai. This function neither fetches sources nor matches supplier names.
    """
    result = {description: "", specifications: [], pricing: [], "references": []}
    warnings, rejected = [], []
    valid = isinstance(extracted, Mapping)
    if not valid:
        extracted = {}
        warnings.append("invalid_extraction")

    def text(value, path, nullable=False):
        if value is None and nullable:
            return None
        if isinstance(value, str):
            return value.strip() or (None if nullable else "")
        warnings.append(f"invalid_text: {path}")
        return None if nullable else ""

    def records(name):
        value = extracted.get(name, [])
        if not isinstance(value, list):
            warnings.append(f"invalid_{name}")
            return []
        return value

    if valid:
        result[description] = text(extracted.get("description"), "description")
    for index, attribute in enumerate(records("specifications")):
        if not isinstance(attribute, Mapping):
            warnings.append(f"invalid_specification: {index}")
            continue
        name = text(attribute.get("name"), f"specifications[{index}].name")
        value = text(attribute.get("value"), f"specifications[{index}].value")
        if not name:
            warnings.append(f"unnamed_specification: {index}")
        result[specifications].append({name or "text": value})

    observed_urls = set(markdown_urls(markdown))
    references = records("references")
    counts = Counter(ref["id"].strip() for ref in references
                     if isinstance(ref, Mapping) and isinstance(ref.get("id"), str))
    for index, reference in enumerate(references):
        if not isinstance(reference, Mapping):
            warnings.append(f"invalid_reference: {index}")
            continue
        ref_id = text(reference.get("id"), f"references[{index}].id")
        url = source_url(reference.get("url"))
        reason = None
        if not ref_id or counts[ref_id] != 1:
            reason = "missing_or_duplicate_reference_id"
        elif not url or url not in observed_urls:
            reason = "reference_url_not_in_evidence"
        if reason:
            warnings.append(f"{reason}: {index}")
            rejected.append({"reference": dict(reference), "reason": reason})
            continue
        source = text(reference.get("source"), f"references[{index}].source")
        result["references"].append({"id": ref_id, "source": source or urlsplit(url).hostname, "url": url})

    accepted_ids = {reference["id"] for reference in result["references"]}
    for index, offer in enumerate(records("offers")):
        if not isinstance(offer, Mapping):
            warnings.append(f"invalid_offer: {index}")
            continue
        price = offer.get("price")
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float))
                                  or not math.isfinite(price) or price < 0):
            warnings.append(f"invalid_price: {index}")
            price = None
        currency = text(offer.get("currency"), f"offers[{index}].currency", nullable=True)
        if currency:
            if len(currency) == 3 and currency.isascii() and currency.isalpha():
                currency = currency.upper()
            else:
                warnings.append(f"invalid_currency: {index}")
                currency = None
        ref_ids = offer.get("reference_ids", [])
        if not isinstance(ref_ids, list):
            warnings.append(f"invalid_reference_ids: {index}")
            ref_ids = []
        selected = []
        for ref_id in ref_ids:
            if not isinstance(ref_id, str) or ref_id not in accepted_ids:
                warnings.append(f"unknown_reference_id: offers[{index}]: {ref_id}")
            elif ref_id not in selected:
                selected.append(ref_id)
        result[pricing].append({
            "price": price, "currency": currency,
            "uom": text(offer.get("uom"), f"offers[{index}].uom", nullable=True),
            "source": text(offer.get("source"), f"offers[{index}].source"),
            "reference_ids": selected,
            "price_text": text(offer.get("price_text"), f"offers[{index}].price_text"),
        })
    return result, {
        "status": "error" if not valid else "partial" if warnings else "complete",
        "warnings": warnings, "rejected_references": rejected,
        "unselected_source_urls": sorted(observed_urls - {ref["url"] for ref in result["references"]}),
    }
