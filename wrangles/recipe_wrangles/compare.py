"""
Functions to compare data from within columns
"""

from typing import Union as _Union
import pandas as _pd
from .. import compare as _compare

def text(
    df: _pd.DataFrame,
    input: list,
    output: str,
    method: str = 'difference',
    # Overlap parameters
    char: str = ' ',
    # match parameters
    non_match_char: str = '*',
    include_ratio: bool = False,
    decimal_places: int = 3,
    exact_match_value: str = '<<EXACT_MATCH>>',
    input_a_empty_value: str = '<<A EMPTY>>',
    input_b_empty_value: str = '<<B EMPTY>>',
    both_empty_value: str = '<<BOTH EMPTY>>',
) -> _pd.DataFrame:
    """
    type: object
    description: Compare two strings and return the intersection or difference using overlap or use match to find the matching characters between two strings.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: list
        description: the columns to compare
      output:
        type: string
        description: The column to output the results to
      method:
        type: string
        description: (Optional) The type of comparison to perform
        enum:
          - difference
          - intersection
          - overlap
      char:
        type: string
        description: (Optional difference/intersection) The character to split the strings on. Default is a space
      non_match_char:
        type: string
        description: (Optional overlap) Character to use for non-matching characters
      include_ratio:
        type: boolean
        description: (Optional overlap) Include the ratio of matching characters
      decimal_places:
        type: integer
        description: (Optional overlap) Number of decimal places to round the ratio to
      exact_match_value:
        type: string
        description: (Optional overlap) Value to use for exact matches
      input_a_empty_value:
        type: string
        description: (Optional overlap) Value to use for empty input a
      input_b_empty_value:
        type: string
        description: (Optional overlap) Value to use for empty input b
      both_empty_value:
        type: string
        description: (Optional overlap) Value to use for both inputs
    """

    # Check that input is a list of length 2
    if len(input) != 2:
        raise ValueError("compare.text Wrangle, input must be a list of length 2")
    
    if method not in ['difference', 'intersection', 'overlap']:
        raise ValueError("Method must be one of 'overlap', 'difference' or 'intersection'")

    if method == 'difference' or method == 'intersection':
        df[output] = _compare.contrast(
            input_a=df[input[0]].astype(str).tolist(),
            input_b=df[input[1]].astype(str).tolist(),
            type=method,
            char=char
        )

    if method == 'overlap':
        if isinstance(decimal_places, str):
            int(decimal_places)

        df[output] = _compare.overlap(
            df[input[0]].astype(str).values.tolist(),
            df[input[1]].astype(str).values.tolist(),
            non_match_char,
            include_ratio,
            decimal_places,
            exact_match_value,
            input_a_empty_value,
            input_b_empty_value,
            both_empty_value
        )

    return df