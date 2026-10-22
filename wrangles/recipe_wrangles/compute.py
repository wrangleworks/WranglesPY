import pandas as _pd
import numpy as _np

import re as _re
import logging as _logging

# Import our core compute and format functions
from .. import compute as _compute
from .. import format as _format


def case_when(
    df: _pd.DataFrame,
    output: str,
    cases: list,
    default=None
):
    """  
    type: object  
    description: Assign values to a column based on conditional logic  
    additionalProperties: false  
    required:  
      - output  
      - cases  
    properties:  
      output:  
        type: string  
        description: Name of the output column  
      cases:  
        type: array  
        description: List of conditions and corresponding values  
        minItems: 1  
        items:  
          type: object  
          required:  
            - condition  
            - value  
          properties:  
            condition:  
              type: string  
              description: Condition to evaluate (e.g., "Score > 0.84")  
            value:  
              type: [string, number, integer, boolean]  
              description: Value to assign if condition is true  
      default:  
        type: [string, number, integer, boolean, "null"]  
        description: Value to assign if no conditions are met. Default None.  
    """

    _logging.debug(f": Evaluating case_when :: condition_count :: {len(cases)}, output :: {output}")
    df_temp = df.copy()
    df_temp.columns = df_temp.columns.str.replace(
        r'[^a-zA-Z0-9_]', '_', regex=True)

    # Evaluate conditions using the renamed columns
    conditions = [df_temp.eval(case['condition']) for case in cases]
    choices = [case['value'] for case in cases]

    # Use numpy.select to evaluate conditions and assign values
    df[output] = _np.select(conditions, choices, default=default)

    return df


def score_search_results(
    df: _pd.DataFrame,
    input: list,
    output: str | list,
    must_match_part_code: bool = True,
    allow_mpn_exact: bool = True,
    allow_mpn_partial: bool = True,
    allow_other_exact: bool = True,
    allow_other_partial: bool = True,
    blacklist_keywords: str = "",
    mpn_exact_score: float = 8.0,
    mpn_partial_base: float = 4.0,
    part_code_exact_score: float = 6.0,
    part_code_partial_base: float = 2.0,
    supplier_exact_score: float = 3.0,
    supplier_partial_base: float = 1.0,
    context_match_base: float = 2.0,
    fuzzy_match_threshold: float = 0.8
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Deduplicates and ranks structured search results using part-number, supplier
      text, context, original-rank, query-order, supplier-domain, and product-URL
      signals. Unfiltered results come first; filtered results are retained at
      the end, with each group sorted by descending score. Each result contains
      summary, scoring_details, pricing, metadata, reduced part_code_matches,
      and part_code_match_count before evidence reduction. Numeric part-match
      categories use broad normalized containment and can differ from the exact,
      stripped, and partial diagnostic evidence levels. Does not search again or
      visit result pages. See docs/search_result_scoring.md for the full contract.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: array
        minItems: 3
        maxItems: 5
        items:
          type: string
        description: >-
          Three to five ordered column names: results, suppliers, part_codes,
          optional MPNs, optional descriptions. Results cells contain lists of
          payloads with search_metadata and search_results. Text-input cells
          accept scalar values or lists. To use descriptions without an MPN,
          provide five inputs and leave the fourth column's values blank.
      output:
        type:
          - string
          - array
        minItems: 1
        maxItems: 2
        items:
          type: string
        description: >-
          One name or a one-element list receives scored dictionaries. Two names
          receive parallel dictionary and formatted-summary lists in that order.
          Each row retains its result lists; results are not expanded into rows.
          Part-code evidence and counts remain nested in each dictionary, not in
          a third output column. Empty or non-list results cells produce empty lists.
      must_match_part_code:
        type: boolean
        default: true
        description: >-
          If true, mark results filtered when their scoring match category is not
          allowed. If false, keep such results eligible, while part_code_found
          still reports category eligibility. Blacklisting applies in both cases.
          Filtered dictionaries remain in the output with their scores and reasons.
      allow_mpn_exact:
        type: boolean
        default: true
        description: >-
          Allow the mpn_exact scoring category. Containment of an MPN with at
          least four normalized characters can receive this category even when its
          diagnostic evidence is partial. Does not change scores or evidence.
      allow_mpn_partial:
        type: boolean
        default: true
        description: >-
          Allow the mpn_partial scoring category, not every partial diagnostic
          evidence record. MPN categories take precedence over other-code categories.
      allow_other_exact:
        type: boolean
        default: true
        description: >-
          Allow other_code_exact when no positive MPN match is recognized.
          Normalized containment can receive exact points. Disallowing an MPN
          category does not fall back to this category.
      allow_other_partial:
        type: boolean
        default: true
        description: >-
          Allow other_code_partial when no positive MPN match is recognized.
          Applies to the scoring category, not the diagnostic match_level.
      blacklist_keywords:
        type:
          - string
          - array
        items:
          type: string
        default: ""
        description: >-
          Literal substrings of the full lowercased URL to mark as filtered.
          A comma-separated string is trimmed and lowercased; list entries are
          used as supplied, so provide trimmed lowercase strings. Does not match
          titles or snippets and applies even when must_match_part_code is false.
      mpn_exact_score:
        type: number
        default: 8.0
        description: >-
          Exact-score MPN points, including normalized containment for inputs of
          at least four characters. Only the higher MPN or other-code contribution
          is added; a tie prefers the MPN explanation. Keep exact weights positive.
      mpn_partial_base:
        type: number
        default: 4.0
        description: >-
          Base points for partial/variant MPN scoring. Ordinary normalized
          containment already receives exact points; this is not a weight for
          every partial diagnostic evidence record.
      part_code_exact_score:
        type: number
        default: 6.0
        description: >-
          Exact-score other-code points, including normalized containment for
          inputs of at least four characters. Not added on top of the MPN score.
      part_code_partial_base:
        type: number
        default: 2.0
        description: >-
          Base points for partial/variant other-code scoring. Does not change
          diagnostic levels; containment can already receive exact points.
      supplier_exact_score:
        type: number
        default: 3.0
        description: >-
          Points when a normalized supplier name equals a complete title, snippet,
          or URL field. An embedded name instead uses supplier_partial_base.
      supplier_partial_base:
        type: number
        default: 1.0
        description: >-
          Base for embedded supplier text; reverse containment uses 95 percent
          of the base, and fuzzy matches at the fixed 0.8 cutoff use their
          similarity times the base. Only the strongest text match contributes.
      context_match_base:
        type: number
        default: 2.0
        description: >-
          Points when all normalized unique input context terms match. Terms
          include suppliers, codes, MPNs, full descriptions, and description words
          longer than two characters. The matched fraction times this base is
          rounded to one decimal place; repeated occurrences do not add points.
      fuzzy_match_threshold:
        type: number
        default: 0.8
        description: >-
          Similarity cutoff for context terms and supplier-text recognition in
          brand_found. Does not change the fixed supplier fuzzy-scoring cutoff,
          part-code evidence levels, or allowed scoring categories. Domain evidence
          can set brand_found independently of this threshold.
    """
    if not isinstance(input, list) or len(input) not in [3, 4, 5]:
        raise ValueError("score_search_results requires 3 to 5 inputs")

    results_col = input[0]
    suppliers_col = input[1]
    part_codes_col = input[2]
    mpns_col = input[3] if len(input) >= 4 else None
    desc_col = input[4] if len(input) == 5 else None

    if isinstance(blacklist_keywords, str):
        blacklist = [b.strip().lower() for b in blacklist_keywords.split(",") if b.strip()]
    else:
        blacklist = blacklist_keywords or []

    allowed_match_types = set()
    if allow_mpn_exact: allowed_match_types.add("mpn_exact")
    if allow_mpn_partial: allowed_match_types.add("mpn_partial")
    if allow_other_exact: allowed_match_types.add("other_code_exact")
    if allow_other_partial: allowed_match_types.add("other_code_partial")

    out_series_dicts = []
    out_series_strings = []

    for _, row in df.iterrows():
        payloads = row.get(results_col, [])
        num_queries = len(payloads) if isinstance(payloads, list) else 0

        def _get_list_strings(col_name):
            val = row.get(col_name, [])
            l = val if isinstance(val, list) else ([val] if _pd.notna(val) else [])
            return [str(i) for i in l if i]

        suppliers = _get_list_strings(suppliers_col)
        part_codes = _get_list_strings(part_codes_col)
        mpns = _get_list_strings(mpns_col) if mpns_col else []
        descriptions = _get_list_strings(desc_col) if desc_col else []

        if not isinstance(payloads, list) or not payloads:
            out_series_dicts.append([])
            out_series_strings.append([])
            continue

        combined_results = _compute.score_search_results(
            payloads=payloads,
            suppliers=suppliers,
            part_codes=part_codes,
            mpns=mpns,
            descriptions=descriptions,
            must_match_part_code=False, 
            blacklist=blacklist,
            mpn_exact_score=mpn_exact_score,
            mpn_partial_base=mpn_partial_base,
            part_code_exact_score=part_code_exact_score,
            part_code_partial_base=part_code_partial_base,
            supplier_exact_score=supplier_exact_score,
            supplier_partial_base=supplier_partial_base,
            context_match_base=context_match_base,
            fuzzy_match_threshold=fuzzy_match_threshold
        )
        
        final_results = []
        for res in combined_results:
            match_enum = res["summary"].get("part_code_found", "none")
            is_valid_match = match_enum in allowed_match_types
            
            if must_match_part_code and not is_valid_match:
                res["summary"]["filtered"] = True
                res["summary"]["filtered_reason"] = f"unauthorized match type ({match_enum})"
            
            # Cast back to boolean for schema health, save enum to new key
            res["summary"]["part_code_found"] = is_valid_match
            res["summary"]["part_match_type"] = match_enum 
            
            final_results.append(res)
            
        filtered_in = sorted([s for s in final_results if not s["summary"]["filtered"]], key=lambda x: x["summary"]["score"], reverse=True)
        filtered_out = sorted([s for s in final_results if s["summary"]["filtered"]], key=lambda x: x["summary"]["score"], reverse=True)
        final_results = filtered_in + filtered_out

        row_strings = []
        for idx, res in enumerate(final_results, start=1):
            res["summary"]["scored_result_index"] = idx 
            row_strings.append(_format.search_result_to_text(res, num_queries))

        out_series_dicts.append(final_results)
        out_series_strings.append(row_strings)

    if isinstance(output, list) and len(output) == 2:
        df[output[0]] = out_series_dicts
        df[output[1]] = out_series_strings
    elif isinstance(output, list) and len(output) == 1:
        df[output[0]] = out_series_dicts
    elif isinstance(output, str):
        df[output] = out_series_dicts
    else:
        raise ValueError("output must be a single column name or a list of two column names")

    return df
