from urllib.parse import urlsplit
from typing import List, Tuple, Dict

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

def _evaluate_match(
    candidates: List[str],
    fields: dict, 
    exact_score: float,
    partial_base: float,
    entity_name: str
) -> Tuple[float, str, float]:
    """Evaluates candidates against text fields."""
    best_score = 0.0
    best_reason = f"No {entity_name} Match"
    best_ratio = 0.0
    
    if not candidates: return best_score, best_reason, best_ratio
        
    for candidate in candidates:
        norm_cand = _compare.normalize_alphanum(candidate)
        if not norm_cand: continue
            
        for field_name, field_text in fields.items():
            if not field_text: continue
                
            if norm_cand in field_text:
                score = exact_score
                if score > best_score:
                    best_score = score
                    best_reason = f"Exact Match ({entity_name}) in {field_name}"
                    best_ratio = 1.0
                continue 
                
            ratio, _, _ = _compare.partial_ratio(norm_cand, field_text)
            score = round(ratio * partial_base, 2)
            
            if score > best_score:
                best_score = score
                best_reason = f"Partial Match ({entity_name}) in {field_name} [{ratio:.2f}]"
                
            if ratio > best_ratio:
                best_ratio = ratio
                
    return best_score, best_reason, best_ratio


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
    Returns: (best_score, best_reason, best_ratio, visual_match_string)
    """
    best_score = 0.0
    best_reason = f"No {entity_name} Match"
    best_ratio = 0.0
    best_visual = ""
    
    if not candidates or not fields_tokens: 
        return best_score, best_reason, best_ratio, best_visual
        
    for candidate in candidates:
        norm_cand = _compare.normalize_alphanum(candidate)
        if not norm_cand: 
            continue
            
        cand_len = len(norm_cand)
        
        # Guardrail: If the code is very short, force an exact token match
        is_short_code = cand_len <= min_length_for_substring
        
        for field_name, tokens in fields_tokens.items():
            for token in tokens:
                if not token: 
                    continue
                    
                token_len = len(token)
                
                # 1. Exact Token Match (The Holy Grail)
                if norm_cand == token:
                    # Perfect match gets immediate return to save cycles
                    return exact_score, f"Exact Match ({entity_name}) in {field_name}", 1.0, f"**{norm_cand}**"
                    
                # 2. Variant / Substring Match (Prefixes, Suffixes, Embeds)
                elif not is_short_code and norm_cand in token:
                    # Calculate how much of the target token consists of our part code
                    # e.g., "lm555" (5) inside "lm555cn" (7) = 0.71 ratio
                    ratio = cand_len / token_len
                    
                    if ratio >= min_partial_ratio:
                        score = round(ratio * partial_base, 2)
                        
                        if score > best_score:
                            best_score = score
                            best_reason = f"Variant Match ({entity_name}) in {field_name} [{ratio:.2f}]"
                            best_ratio = ratio
                            # Create the visual representation (e.g., "**lm555**cn")
                            best_visual = token.replace(norm_cand, f"**{norm_cand}**")
                            
                # Note: We omit standard fuzzy/Levenshtein matching here by default.
                # If a part code is a typo (e.g. "lm556" instead of "lm555"), 
                # substring fails. We rely on exact or prefix/suffix matches.

    return best_score, best_reason, best_ratio, best_visual

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
    """
    Core function that scores a single list of search payloads against given criteria.
    Returns a sorted list of scored dictionary items.
    """
    # --- PHASE 1: SETUP & NORMALIZATION ---
    mpns = mpns or []
    descriptions = descriptions or []
    blacklist = blacklist or []

    # Pool all terms together to build a context-matching dictionary
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

    # --- PHASE 2: FLATTEN & DEDUPLICATE ---
    flat_results = []
    for p in payloads:
        meta = p.get("search_metadata", {})
        for r in p.get("search_results", []):
            r_copy = r.copy()
            r_copy["__meta"] = meta
            flat_results.append(r_copy)

    # Deduplicate results based on normalized URLs, allowing overrides for specific subdomains (e.g., 'shop.')
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
    
    # Helper for tokenizing text specifically for part code matching
    def _get_tokens(text: str) -> list:
        if not text: return []
        clean = text.replace('/', ' ').replace('-', ' ').replace('_', ' ')
        return [t for t in (_compare.normalize_alphanum(w) for w in clean.split()) if t]

    # --- PHASE 3: SCORING LOOP ---
    for item in unique_raw_results:
        meta = item.get("__meta", {})
        
        # Calculate search result degradation weight (results further down the SERP are penalized)
        qi = meta.get("query_index", 1) - 1
        w = round(1.0 * (0.9 ** qi), 2)

        # Build squashed fields for generic string matching (Context, Suppliers)
        fields = {
            "Title": _compare.normalize_alphanum(item.get("title", "")),
            "Snippet": _compare.normalize_alphanum(item.get("snippet", "")),
            "URL": _compare.normalize_alphanum(item.get("link", ""))
        }
        
        # Build tokenized fields specifically for the safer Part Code/MPN matching
        fields_tokens = {
            "Title": _get_tokens(item.get("title", "")),
            "Snippet": _get_tokens(item.get("snippet", "")),
            "URL": _get_tokens(item.get("link", ""))
        }

        # 1. Context Scoring (How many of our general terms show up?)
        combined_norm_text = fields["Title"] + " " + fields["Snippet"] + " " + fields["URL"]
        item_matches = []
        for norm_t, orig_t in unique_terms.items():
            if norm_t in combined_norm_text:
                item_matches.append(orig_t)
            else:
                best_r, best_m_s, best_m_e = 0.0, 0, 0
                for f_text in [fields["Title"], fields["Snippet"], fields["URL"]]:
                    r, m_s, m_e = _compare.partial_ratio(norm_t, f_text)
                    if r > best_r:
                        best_r, best_m_s, best_m_e = r, m_s, m_e
                
                if best_r >= fuzzy_match_threshold:
                    item_matches.append(_compare.mask_original_term(orig_t, best_m_s, best_m_e))

        context_ratio = len(item_matches) / max(1, len(unique_terms))
        context_score = round(context_ratio * context_match_base, 1)
        context_score_reason = f"{len(item_matches)} of {len(unique_terms)} terms matched"

        # 2. Entity Scoring (MPNs, Part Codes, and Suppliers)
        # Note: MPN and Part Code now use the specialized token-based match!
        mpn_score, mpn_reason, mpn_ratio, mpn_vis = _evaluate_part_code_match(mpns, fields_tokens, mpn_exact_score, mpn_partial_base, "MPN")
        pc_score, pc_reason, pc_ratio, pc_vis = _evaluate_part_code_match(part_codes, fields_tokens, part_code_exact_score, part_code_partial_base, "Part Code")
        sup_score, sup_reason, sup_ratio = _evaluate_match(suppliers, fields, supplier_exact_score, supplier_partial_base, "Supplier")

        # Determine the best part match score and capture the visual representation
        if mpn_score >= pc_score:
            best_pc_score, pc_match_reason, best_vis = mpn_score, mpn_reason, mpn_vis
        else:
            best_pc_score, pc_match_reason, best_vis = pc_score, pc_reason, pc_vis

        # Add the visual part match (e.g., "**LM555**CN") to the matches list for frontend display
        if best_vis and best_vis not in item_matches:
            item_matches.append(best_vis)

        # NEW LOGIC: Determine specific enum state for the match
        part_code_found_enum = "none"
        if mpn_score == mpn_exact_score:
            part_code_found_enum = "mpn_exact"
        elif mpn_ratio >= fuzzy_match_threshold:
            part_code_found_enum = "mpn_partial"
        elif pc_score == part_code_exact_score:
            part_code_found_enum = "other_code_exact"
        elif pc_ratio >= fuzzy_match_threshold:
            part_code_found_enum = "other_code_partial"
            
        # temporarily set the boolean flag here so the filter logic still works inside this function.
        # The outer wrapper will now control the definition of what constitutes a "match".
        part_code_found = part_code_found_enum != "none"
            
        supplier_found = sup_ratio >= fuzzy_match_threshold

        # 3. Positional and URL Scoring
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

        # --- PHASE 4: AGGREGATE SCORES & PACKAGE ---
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
            "brand_score": sup_score,
            "brand_match_reason": sup_reason,
        }
        for k, val in sorted_remainder.items():
            scoring_details[k] = val
            scoring_details[f"{k}_reason"] = remainder_reasons[f"{k}_reason"]

        # Check filter conditions (Blacklists and missing part codes)
        reason = ""
        matched_keyword = next((b for b in blacklist if b in site.lower()), None) if blacklist else None

        if matched_keyword:
            reason = f"blacklisted ({matched_keyword})"
        elif must_match_part_code and not part_code_found:
            reason = "no part code match"

        # Final Summary Dict
        summary = {
            "scored_result_index": 0, 
            "source": item.get("source"),
            "score": total_score,                      
            "link": item.get("link"),
            "part_code_found": part_code_found_enum,
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

    # --- PHASE 5: SORT AND FINALIZE ---
    filtered_in = sorted([s for s in scored_flat_results if not s["summary"]["filtered"]], key=lambda x: x["summary"]["score"], reverse=True)
    filtered_out = sorted([s for s in scored_flat_results if s["summary"]["filtered"]], key=lambda x: x["summary"]["score"], reverse=True)

    combined_results = filtered_in + filtered_out
    
    # Re-index based on final sorted position
    for idx, res in enumerate(combined_results, start=1):
        res["summary"]["scored_result_index"] = idx

    return combined_results