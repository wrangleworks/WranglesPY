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
      - method
    properties:
      input:
        type: array
        description: the columns to compare. First column is the base column
      output:
        type: string
        description: The column to output the results to
      method:
        type: string
        description: The type of comparison to perform (difference, intersection, overlap)
        enum:
          - difference
          - intersection
          - overlap
    allOf:
      - if:
          properties:
            method:
              const: difference
        then:
          properties:
            char:
              type: string
              description: "(Optional) The character to split the strings on. Default is a space"
      - if:
          properties:
            method:
              const: intersection
        then:
          properties:
            char:
              type: string
              description: "(Optional) The character to split the strings on. Default is a space"
      - if:
          properties:
            method:
              const: overlap
        then:
          properties:
            non_match_char:
              type: string
              description: "(Optional) Character to use for non-matching characters"
            include_ratio:
              type: boolean
              description: "(Optional) Include the ratio of matching characters"
            decimal_places:
              type: integer
              description: "(Optional) Number of decimal places to round the ratio to"
            exact_match_value:
              type: string
              description: "(Optional) Value to use for exact matches"
            input_a_empty_value:
              type: string
              description: "(Optional) Value to use for empty input a"
            input_b_empty_value:
              type: string
              description: "(Optional) Value to use for empty input b"
            both_empty_value:
              type: string
              description: "(Optional) Value to use for both inputs"

    """

    # Check that input is a list of length 2
    if len(input) != 2:
        raise ValueError("compare.text Wrangle, input must be a list of length 2")
    
    if method not in ['difference', 'intersection', 'overlap']:
        raise ValueError("Method must be one of 'overlap', 'difference' or 'intersection'")

    if method == 'difference' or method == 'intersection':
        df[output] = _compare._contrast(
            input_a=df[input[0]].astype(str).tolist(),
            input_b=df[input[1]].astype(str).tolist(),
            type=method,
            char=char
        )

    if method == 'overlap':
        if isinstance(decimal_places, str):
            int(decimal_places)

        df[output] = _compare._overlap(
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