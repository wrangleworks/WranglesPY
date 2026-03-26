from urllib.parse import urlsplit
from typing import List, Tuple, Dict

from attrs import fields

# Import our separated helpers
from . import web as _web
from . import compare as _compare

def _get_position_weight(position: int) -> float:
    """
    Calculates a Google search results position weight score based on a discrete mapping.
    - Positions 1-2:   Score 2.0
    - Positions 3-4:   Score 1.5
    - Position 5:      Score 1.0
    - Positions 6+:    Score 0.0
    """
    if position <= 2: return 2.0
    elif position <= 4: return 1.5
    elif position == 5: return 1.0
    return 0.0

def _get_supplier_site_score(supplier_names: list, netloc: str) -> int:
    if not supplier_names or not netloc: return 0

    domain_parts = netloc.split('.')
    if len(domain_parts) < 2: return 0
        
    normalized_domain = _compare.normalize_alphanum(domain_parts[-2])
    normalized_suppliers = [_compare.normalize_alphanum(s) for s in supplier_names]

    for sup_norm in normalized_suppliers:
        if sup_norm == normalized_domain: return 2

    for sup_norm in normalized_suppliers:
        if len(normalized_domain) > 4 and normalized_domain in sup_norm: return 1
        if len(sup_norm) > 4 and sup_norm in normalized_domain: return 1
            
    return 0


def _evaluate_part_code_match(
    candidates: List[str],
    fields_tokens: Dict[str, List[str]], 
    exact_score: float,
    partial_base: float,
    entity_name: str,
    min_length_for_substring: int = 3,
    min_partial_ratio: float = 0.50
) -> Tuple[float, str, float, str]:
    """
    Specialized evaluator for Part Codes and MPNs using tokenized fields.
    Returns: (score, reason, ratio, visual_match_string)
    """
    best_score, best_ratio = 0.0, 0.0
    best_reason = f"No {entity_name} Match"
    best_visual = ""
    
    if not candidates or not fields_tokens: 
        return best_score, best_reason, best_ratio, best_visual
        
    for candidate in candidates:
        norm_cand = _compare.normalize_alphanum(candidate)
        if not norm_cand: continue
            
        cand_len = len(norm_cand)
        is_short_code = cand_len <= min_length_for_substring
        
        for field_name, tokens in fields_tokens.items():
            for token in tokens:
                if not token: continue
                token_len = len(token)
                
                # 1. Exact Token Match
                if norm_cand == token:
                    return exact_score, f"Exact Match '{candidate}' ({entity_name}) in {field_name}", 1.0, f"**{norm_cand}**"
                    
                # 2. Variant / Substring Match
                elif not is_short_code and norm_cand in token:
                    ratio = cand_len / token_len
                    if ratio >= min_partial_ratio:
                        score = round(ratio * partial_base, 2)
                        if score > best_score:
                            best_score, best_ratio = score, ratio
                            best_reason = f"Variant Match '{candidate}' ({entity_name}) in {field_name} [{ratio:.2f}]"
                            best_visual = token.replace(norm_cand, f"**{norm_cand}**")

    return best_score, best_reason, best_ratio, best_visual


def _evaluate_match(
    candidates: List[str],
    fields: Dict[str, str], 
    exact_score: float,
    partial_base: float,
    entity_name: str,
    min_ratio: float = 0.80
) -> Tuple[float, str, float, str]:
    """
    Evaluates context/brands using Substring Priority and Tokenized difflib.
    Returns: (score, reason, ratio, match_string)
    """
    best_score, best_ratio = 0.0, 0.0
    best_reason = f"No {entity_name} Match"
    best_match_str = ""
    
    if not candidates or not fields: 
        return best_score, best_reason, best_ratio, best_match_str
        
    for candidate in candidates:
        norm_cand = _compare.normalize_alphanum(candidate)
        if not norm_cand: continue
            
        for field_name, field_text in fields.items():
            if not field_text: continue
            
            norm_field = _compare.normalize_alphanum(field_text)
            if not norm_field: continue
                
            # 1. EXACT MATCH
            if norm_cand == norm_field:
                return exact_score, f"Exact Match '{candidate}' ({entity_name}) in {field_name}", 1.0, candidate
                
            # 2. SUBSTRING BYPASS
            if norm_cand in norm_field:
                score = round(1.0 * partial_base, 2)
                if score > best_score:
                    best_score, best_ratio = score, 1.0
                    best_reason = f"Embedded Match '{candidate}' ({entity_name}) in {field_name}"
                    best_match_str = candidate
                continue
                
            # 3. TOKENIZED FALLBACKS (Reverse Substring & Fuzzy)
            clean_field = field_text.replace('/', ' ').replace('-', ' ').replace('.', ' ').replace('_', ' ')
            tokens = clean_field.split()
            
            for token in tokens:
                norm_token = _compare.normalize_alphanum(token)
                if not norm_token: continue
                
                # A. Reverse Substring Bypass
                if len(norm_token) >= 5 and norm_token in norm_cand:
                    score = round(0.95 * partial_base, 2)
                    if score > best_score:
                        best_score, best_ratio = score, 0.95
                        best_reason = f"Reverse Embed '{candidate}' ({entity_name}) in {field_name}"
                        best_match_str = candidate
                    continue

                # B. Standard Fuzzy Match
                ratio, _, _ = _compare.partial_ratio(norm_cand, norm_token)
                if ratio >= min_ratio:
                    score = round(ratio * partial_base, 2)
                    if score > best_score:
                        best_score, best_ratio = score, ratio
                        best_reason = f"Fuzzy Match '{candidate}' ({entity_name}) in {field_name} [{ratio:.2f}]"
                        best_match_str = candidate
                        
    return best_score, best_reason, best_ratio, best_match_str

### Main Score Function ###

def score_search_results(
    payloads: list,
    suppliers: list,
    part_codes: list,
    mpns: list | None = None,
    descriptions: list | None = None,
    must_match_part_code: bool = True,
    blacklist: list | None = None,
    mpn_exact_score: float = 8.0,
    mpn_partial_base: float = 4.0,
    part_code_exact_score: float = 6.0,
    part_code_partial_base: float = 2.0,
    supplier_exact_score: float = 3.0,
    supplier_partial_base: float = 1.0,
    context_match_base: float = 2.0,
    fuzzy_match_threshold: float = 0.8
) -> list:
    """Core function that scores a single list of search payloads."""
    mpns = mpns or []
    descriptions = descriptions or []
    blacklist = blacklist or []

    raw_terms = []
    raw_terms.extend(suppliers)
    raw_terms.extend(part_codes)
    raw_terms.extend(mpns)
    for d in descriptions:
        raw_terms.append(d)
        raw_terms.extend([w for w in d.split() if len(w) > 2]) 

    unique_terms = {}
    for t in raw_terms:
        norm_t = _compare.normalize_alphanum(t)
        if norm_t and norm_t not in unique_terms:
            unique_terms[norm_t] = t

    flat_results = []
    for p in payloads:
        meta = p.get("search_metadata", {})
        for r in p.get("search_results", []):
            r_copy = r.copy()
            r_copy["__meta"] = meta
            flat_results.append(r_copy)

    deduped_map = {}
    for item in flat_results:
        link = item.get("link", "")
        if not link: continue
        
        norm_link = _web.normalize_site(link)
        if norm_link not in deduped_map:
            deduped_map[norm_link] = item
        else:
            if "shop." in link:
                deduped_map[norm_link] = item

    unique_raw_results = list(deduped_map.values())
    scored_flat_results = []
    
    def _get_tokens(text: str) -> list:
        if not text: return []
        clean = text.replace('/', ' ').replace('-', ' ').replace('_', ' ')
        return [t for t in (_compare.normalize_alphanum(w) for w in clean.split()) if t]

    for item in unique_raw_results:
        meta = item.get("__meta", {})
        qi = meta.get("query_index", 1) - 1
        w = round(1.0 * (0.9 ** qi), 2)

        # 1. Keep the raw fields so _evaluate_match can see the punctuation!
        raw_fields = {
            "Title": str(item.get("title", "")),
            "Snippet": str(item.get("snippet", "")),
            "URL": str(item.get("link", ""))
        }

        # 2. Create the tokenized version for the Part Code Matcher
        fields_tokens = {k: _get_tokens(v) for k, v in raw_fields.items()}
        
        # --- REFACTORED CONTEXT MATH ---
        item_matches = []
        # Pool all tokens together from title, snippet, and URL
        all_tokens = fields_tokens["Title"] + fields_tokens["Snippet"] + fields_tokens["URL"]
        
        for norm_t, orig_t in unique_terms.items():
            term_matched = False
            
            for token in all_tokens:
                if not token: continue
                
                # 1. Exact Token Match
                if norm_t == token:
                    term_matched = True
                    break
                    
                # 2. Embedded Match (Only if the term is > 3 chars to prevent false positives)
                elif len(norm_t) > 3 and norm_t in token:
                    term_matched = True
                    break
                    
                # 3. Token Fuzzy Match (Typos)
                else:
                    ratio, _, _ = _compare.partial_ratio(norm_t, token)
                    if ratio >= fuzzy_match_threshold:
                        term_matched = True
                        break
                        
            if term_matched:
                item_matches.append(orig_t)

        context_ratio = len(item_matches) / max(1, len(unique_terms))
        context_score = round(context_ratio * context_match_base, 1)
        
        # Build the specific reason string for context score
        if item_matches:
            matched_terms_str = ", ".join([f"'{t}'" for t in item_matches])
            # --- NEW FORMAT HERE ---
            context_score_reason = f"Matched {len(item_matches)} terms ({matched_terms_str}) out of {len(unique_terms)} from input query"
        else:
            context_score_reason = "No context terms matched"

        # Entity Scoring (Unpacking 4 elements now!)
        mpn_score, mpn_reason, mpn_ratio, mpn_vis = _evaluate_part_code_match(mpns, fields_tokens, mpn_exact_score, mpn_partial_base, "MPN")
        pc_score, pc_reason, pc_ratio, pc_vis = _evaluate_part_code_match(part_codes, fields_tokens, part_code_exact_score, part_code_partial_base, "Part Code")
        sup_score, sup_reason, sup_ratio, sup_vis = _evaluate_match(suppliers, raw_fields, supplier_exact_score, supplier_partial_base, "Supplier")

        if mpn_score >= pc_score:
            best_pc_score, pc_match_reason, best_vis = mpn_score, mpn_reason, mpn_vis
        else:
            best_pc_score, pc_match_reason, best_vis = pc_score, pc_reason, pc_vis

        if best_vis and best_vis not in item_matches:
            item_matches.append(best_vis)

        # Build Enum
        part_code_found_enum = "none"
        if mpn_score == mpn_exact_score:
            part_code_found_enum = "mpn_exact"
        elif mpn_score > 0:
            part_code_found_enum = "mpn_partial"
        elif pc_score == part_code_exact_score:
            part_code_found_enum = "other_code_exact"
        elif pc_score > 0:
            part_code_found_enum = "other_code_partial"
            
        part_code_found = part_code_found_enum != "none"
        supplier_found = sup_ratio >= fuzzy_match_threshold

        position = item.get("google_rank", 1)
        position_weight = _get_position_weight(position)
        
        supplier_site_score = 0
        site = item.get("link", "")
        try:
            netloc = urlsplit(site).netloc.lower()
            supplier_site_score = _get_supplier_site_score(suppliers, netloc)
        except Exception:
            pass

        brand_found = bool(supplier_site_score > 0 or supplier_found)
        product_url_score, product_url_reason = _web.is_product_url(site)
        supplier_site_reason = "Exact domain match" if supplier_site_score == 2 else "Partial domain match" if supplier_site_score == 1 else "No domain match"

        remainder_elements = {
            "product_url": product_url_score,
            "position_weight": position_weight,
            "supplier_site": supplier_site_score,
            "query_weight": w,
            "context_score": context_score,
        }
        remainder_reasons = {
            "product_url_reason": product_url_reason,
            "position_weight_reason": f"Rank {position}",
            "supplier_site_reason": supplier_site_reason,
            "query_weight_reason": f"Query Index {meta.get('query_index', 1)}",
            "context_score_reason": context_score_reason,
        }

        total_score = round(best_pc_score + sup_score + sum(remainder_elements.values()), 1)
        sorted_remainder = dict(sorted(remainder_elements.items(), key=lambda item: item[1], reverse=True))

        scoring_details = {
            "score": total_score,
            "part_match_score": best_pc_score,
            "part_match_reason": pc_match_reason,
            "part_match_visual": best_vis,         
            "brand_score": sup_score,
            "brand_match_reason": sup_reason,
            "brand_match_visual": sup_vis,     
        }
        for k, val in sorted_remainder.items():
            scoring_details[k] = val
            scoring_details[f"{k}_reason"] = remainder_reasons[f"{k}_reason"]

        reason = ""
        matched_keyword = next((b for b in blacklist if b in site.lower()), None) if blacklist else None
        if matched_keyword:
            reason = f"blacklisted ({matched_keyword})"
        elif must_match_part_code and not part_code_found:
            reason = "no part code match"

        summary = {
            "scored_result_index": 0, 
            "input_row_id": item.get("input_row_id"),
            "source": item.get("source"),
            "score": total_score,                      
            "link": item.get("link"),
            "part_code_found": part_code_found_enum, # Storing the enum string here momentarily
            "brand_found": brand_found,
            "matches": item_matches,
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "query": meta.get("query"),
            "filtered": bool(reason),
        }
        if reason: summary["filtered_reason"] = reason

        metadata = {
            "query": meta.get("query"),
            "status": meta.get("status"),
            "google_rank": item.get("google_rank"),
            "highlighted_words": item.get("highlighted_words"),
            "missing_words": item.get("missing_words"),
            "search_date": meta.get("search_date"),
            "response_time": meta.get("response_time"),
            "google_url": meta.get("google_url"),
            "search_id": meta.get("search_id"),
            "query_index": meta.get("query_index"),
        }

        raw_pricing = item.get("pricing", {})
        formatted_pricing = {}
        if raw_pricing:
            formatted_pricing = {
                "price": raw_pricing.get("price"),
                "currency": raw_pricing.get("currency"),
                "vendor": item.get("source"),
                "availability": raw_pricing.get("availability")
            }

        scored_item = {
            "summary": summary,
            "pricing": formatted_pricing,
            "scoring_details": scoring_details,
            "metadata": metadata
        }
            
        scored_flat_results.append(scored_item)

    filtered_in = sorted([s for s in scored_flat_results if not s["summary"]["filtered"]], key=lambda x: x["summary"]["score"], reverse=True)
    filtered_out = sorted([s for s in scored_flat_results if s["summary"]["filtered"]], key=lambda x: x["summary"]["score"], reverse=True)
    combined_results = filtered_in + filtered_out
    
    for idx, res in enumerate(combined_results, start=1):
        res["summary"]["scored_result_index"] = idx

    return combined_results