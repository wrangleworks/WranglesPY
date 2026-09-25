"""Validate model-structured AI-search content without interpreting product prose."""

from collections import Counter
from collections.abc import Mapping
import math
from urllib.parse import urlsplit

from ._search_ai_content import google_product_url, markdown_urls, source_url


def validate_sources(references, offers, markdown, *, google_product=None):
    """Validate source URLs and offer references without reshaping AI outputs.

    Product Description, Match Confidence and Specifications remain the direct
    extract.ai outputs. Relevance and supplier matching belong to the model.
    google_product is captured from the description before extraction; it alone
    can populate reserved navigation reference 00.
    """
    checked_references, checked_offers = [], []
    warnings, rejected = [], []
    valid = isinstance(references, list) and isinstance(offers, list)

    def text(value, path, nullable=False):
        if value is None and nullable:
            return None
        if isinstance(value, str):
            return value.strip() or (None if nullable else "")
        warnings.append(f"invalid_text: {path}")
        return None if nullable else ""

    def records(value, name):
        if not isinstance(value, list):
            warnings.append(f"invalid_{name}")
            return []
        return value

    observed_urls = set(markdown_urls(markdown))
    if google_product:
        viewer = google_product_url(google_product)
        if viewer and viewer in markdown_urls(markdown, include_google_products=True):
            checked_references.append({"id": "00", "source": "Google", "url": viewer})
        else:
            warnings.append("google_product_url_not_in_evidence")
    references = records(references, "references")
    counts = Counter(ref["id"].strip() for ref in references
                     if isinstance(ref, Mapping) and isinstance(ref.get("id"), str))
    for index, reference in enumerate(references):
        if not isinstance(reference, Mapping):
            warnings.append(f"invalid_reference: {index}")
            continue
        ref_id = text(reference.get("id"), f"references[{index}].id")
        url = source_url(reference.get("url"))
        reason = None
        if ref_id == "00":
            reason = "reserved_reference_id"
        elif not ref_id or counts[ref_id] != 1:
            reason = "missing_or_duplicate_reference_id"
        elif not url or url not in observed_urls:
            reason = "reference_url_not_in_evidence"
        if reason:
            warnings.append(f"{reason}: {index}")
            rejected.append({"reference": dict(reference), "reason": reason})
            continue
        source = text(reference.get("source"), f"references[{index}].source")
        checked_references.append({"id": ref_id, "source": source or urlsplit(url).hostname, "url": url})

    # The captured viewer is navigation, not a substitute for an offer's supplier.
    accepted_ids = {reference["id"] for reference in checked_references if reference["id"] != "00"}
    for index, offer in enumerate(records(offers, "offers")):
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
        checked_offers.append({
            "price": price, "currency": currency,
            "uom": text(offer.get("uom"), f"offers[{index}].uom", nullable=True),
            "source": text(offer.get("source"), f"offers[{index}].source"),
            "reference_ids": selected,
            "price_text": text(offer.get("price_text"), f"offers[{index}].price_text"),
        })
    return checked_references, checked_offers, {
        "status": "error" if not valid else "partial" if warnings else "complete",
        "warnings": warnings, "rejected_references": rejected,
        "unselected_source_urls": sorted(observed_urls - {ref["url"] for ref in checked_references}),
    }
