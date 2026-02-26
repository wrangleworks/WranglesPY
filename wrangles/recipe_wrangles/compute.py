import re as _re
import logging
import pandas as _pd
import numpy as _np

# Import our core compute and format functions
from .. import compute as _compute
from .. import format as _format

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def score_search_results(
    df: _pd.DataFrame,
    input: list,
    output: str | list,
    must_match_part_code: bool = True,
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
    description: Scores and filters search results based on progressive partial/exact matching. Can return dictionaries or a parallel list of formatted strings.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: array
        description: List of 3 to 5 columns -> [results, suppliers, part_codes, mpns (optional), descriptions (optional)]
      output:
        type:
          - string
          - array
        description: Output column for the dictionaries. If a list of 2 is provided, outputs [dicts_column, pretty_strings_column].
      must_match_part_code:
        type: boolean
        description: If true, filters out results that don't satisfy the fuzzy_match_threshold.
      blacklist_keywords:
        type: string
        description: Comma-separated list of keywords to filter out URLs containing them.
      mpn_exact_score:
        type: number
      mpn_partial_base:
        type: number
      part_code_exact_score:
        type: number
      part_code_partial_base:
        type: number
      supplier_exact_score:
        type: number
      supplier_partial_base:
        type: number
      context_match_base:
        type: number
      fuzzy_match_threshold:
        type: number
    """
    
    if not isinstance(input, list) or len(input) not in [3, 4, 5]:
        raise ValueError("score_search_results requires 3 to 5 inputs: [results, suppliers, part_codes, mpns(optional), descriptions(optional)]")

    results_col = input[0]
    suppliers_col = input[1]
    part_codes_col = input[2]
    mpns_col = input[3] if len(input) >= 4 else None
    desc_col = input[4] if len(input) == 5 else None

    if isinstance(blacklist_keywords, str):
        blacklist = [b.strip().lower() for b in blacklist_keywords.split(",") if b.strip()]
    else:
        blacklist = blacklist_keywords or []

    out_series_dicts = []
    out_series_strings = []

    for _, row in df.iterrows():
        payloads = row.get(results_col, [])
        num_queries = len(payloads) if isinstance(payloads, list) else 0

        # Extract and ensure lists
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

        # Execute Core Scoring Math
        combined_results = _compute.score_search_results(
            payloads=payloads,
            suppliers=suppliers,
            part_codes=part_codes,
            mpns=mpns,
            descriptions=descriptions,
            must_match_part_code=must_match_part_code,
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
        
        # Apply Formatter if requested
        row_strings = []
        for res in combined_results:
            row_strings.append(_format.search_result_to_text(res, num_queries))

        out_series_dicts.append(combined_results)
        out_series_strings.append(row_strings)

    # Assign to dataframe
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

    df_temp = df.copy()
    df_temp.columns = df_temp.columns.str.replace(
        r'[^a-zA-Z0-9_]', '_', regex=True)

    # Evaluate conditions using the renamed columns
    conditions = [df_temp.eval(case['condition']) for case in cases]
    choices = [case['value'] for case in cases]

    # Use numpy.select to evaluate conditions and assign values
    df[output] = _np.select(conditions, choices, default=default)

    return df
