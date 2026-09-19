"""Evidence and source alignment shared by AI-search extraction recipes.

These helpers accept answer content, not a search API envelope. AI Mode's
grouped complete result and a future adapter's ai_overview object both fit
this boundary. They never fetch URLs or interpret supplier/attribute prose.
"""

from collections.abc import Mapping
from urllib.parse import urlsplit

from ._search_ai_content import _plain_text, _source_url, prune_noise


def prepare_evidence(answer):
    """Copy structured answer content and assign IDs to its actual source URLs.

    Preserve parallel table representations and unfamiliar content. Transport
    metadata stays outside the model input; unmatched content from section
    grouping remains available to the extractor. IDs are local to this answer.
    """
    if not isinstance(answer, Mapping):
        raise TypeError("AI-search evidence requires an answer dictionary.")
    content = prune_noise({key: value for key, value in answer.items()
                           if key not in ("meta_data", "raw_response", "search_metadata", "search_parameters")})
    metadata = answer.get("meta_data", {})
    if isinstance(metadata, Mapping):
        for key in ("unmatched_sections", "unsectioned_text_blocks", "invalid_fields"):
            if metadata.get(key):
                content[key] = prune_noise(metadata[key])

    sources, by_url, named_urls = [], {}, set()

    def add(value, path, reference=None):
        # Entire URLs only: a label or a sentence containing a URL is not a URL.
        if not isinstance(value, str) or any(char.isspace() for char in value.strip()):
            return
        url = _source_url(value)
        if not url:
            return
        if url not in by_url:
            source = {
                "id": f"s{len(sources) + 1}", "url": url,
                "site": urlsplit(url).hostname.removeprefix("www."),
                "reference_indexes": [], "evidence_paths": [],
            }
            sources.append(source)
            by_url[url] = source
        source = by_url[url]
        if path not in source["evidence_paths"]:
            source["evidence_paths"].append(path)
        if isinstance(reference, Mapping):
            name = _plain_text(reference.get("source"))
            if name and url not in named_urls:
                source["site"] = name
                named_urls.add(url)
            index = reference.get("index")
            if isinstance(index, int) and not isinstance(index, bool) and index not in source["reference_indexes"]:
                source["reference_indexes"].append(index)

    references = content.get("references", [])
    if isinstance(references, list):
        for index, reference in enumerate(references):
            if isinstance(reference, Mapping):
                for key in ("link", "url"):
                    add(reference.get(key), f"/references/{index}/{key}", reference)

    def visit(value, path=""):
        if isinstance(value, Mapping):
            for key, child in value.items():
                token = str(key).replace("~", "~0").replace("/", "~1")
                visit(child, f"{path}/{token}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}/{index}")
        elif isinstance(value, str):
            add(value, path)

    visit(content)
    return {"content": content, "sources": sources}


def format_product_result(extracted, evidence, *, description, specifications, pricing):
    """Format typed extraction fields and align offers to captured source IDs.

    The model supplies description, specifications [{name, value}] and offers
    [{supplier, price, source_ids}]. Only the captured catalog supplies URLs.
    Invalid IDs remain diagnostics; an offer with no valid ID stays unlinked.
    """
    warnings, matches = [], []
    result = {description: "", specifications: [], pricing: [], "references": []}
    valid_record = isinstance(extracted, Mapping)
    if not valid_record:
        warnings.append("invalid_extraction")
        extracted = {}

    def text(value, path):
        if isinstance(value, str):
            return _plain_text(value)
        warnings.append(f"invalid_text: {path}")
        return ""

    if valid_record:
        result[description] = text(extracted.get("description"), "description")
    attributes = extracted.get("specifications", [])
    if not isinstance(attributes, list):
        warnings.append("invalid_specifications")
        attributes = []
    for index, attribute in enumerate(attributes):
        if not isinstance(attribute, Mapping):
            warnings.append(f"invalid_specification: {index}")
            continue
        name = text(attribute.get("name"), f"specifications[{index}].name")
        value = text(attribute.get("value"), f"specifications[{index}].value")
        if not name:
            warnings.append(f"unnamed_specification: {index}")
        result[specifications].append({name or "text": value})

    sources = evidence["sources"]
    catalog = {source["id"]: source for source in sources}
    by_source, unlinked = {}, []
    offers = extracted.get("offers", [])
    if not isinstance(offers, list):
        warnings.append("invalid_offers")
        offers = []
    for index, offer in enumerate(offers):
        if not isinstance(offer, Mapping):
            warnings.append(f"invalid_offer: {index}")
            continue
        supplier = text(offer.get("supplier"), f"offers[{index}].supplier")
        price = text(offer.get("price"), f"offers[{index}].price")
        source_ids = offer.get("source_ids", [])
        if not isinstance(source_ids, list):
            warnings.append(f"invalid_source_ids: offers[{index}]")
            source_ids = []
        valid_ids = []
        for source_id in source_ids:
            if not isinstance(source_id, str) or source_id not in catalog:
                warnings.append(f"unknown_source_id: offers[{index}]: {source_id}")
            elif source_id not in valid_ids:
                valid_ids.append(source_id)
        matches.append({"offer_index": index, "source_ids": valid_ids, "method": "extract.ai"})
        if valid_ids:
            for source_id in valid_ids:
                key = supplier or catalog[source_id]["site"]
                by_source.setdefault(source_id, []).append({key: price})
        else:
            unlinked.append({supplier or "text": price})
            warnings.append(f"unlinked_offer: {index}")

    for source in sources:
        prices = by_source.get(source["id"]) or [{source["site"]: ""}]
        for price in prices:
            result[pricing].append(price)
            result["references"].append(source["url"])
    for price in unlinked:
        result[pricing].append(price)
        result["references"].append("")
    return result, {
        "status": "error" if not valid_record else "partial" if warnings else "complete",
        "warnings": warnings, "source_matches": matches,
    }
