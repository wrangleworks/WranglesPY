"""
Functions to compare data from within columns
"""

import pandas as _pd
from .. import compare as _compare


def lists(
    df: _pd.DataFrame,
    input: list,
    output: str,
    method: str = "intersection",
    remove_duplicates: bool = False,
    ignore_case: bool = False,
) -> _pd.DataFrame:
    """
    type: object
    description: Compare multiple lists and return the intersection, difference, or union
    required:
      - input
      - output
      - method
    properties:
      input:
        type: array
        description: List of input columns containing lists to compare
      output:
        type: string
        description: Name of the output column
      method:
        type: string
        description: Type of comparison to perform
        enum:
          - intersection
          - difference
          - union
          - overlap
      remove_duplicates:
        type: boolean
        description: Remove duplicates from the result
      ignore_case:
        type: boolean
        description: Ignore case when comparing string items
    """

    if method not in ["intersection", "difference", "union", "overlap"]:
        raise ValueError(
            "Method must be one of 'intersection', 'difference', 'union', or 'overlap'"
        )

    # ensure that input is at least a list of two columns
    if len(input) < 2:
        raise ValueError("Input must contain at least two columns")

    def compare_lists(row):
        # Handle case sensitivity for strings
        processed_lists = []
        for item in row:
            if isinstance(item, list):
                if ignore_case:
                    processed = [
                        str(x).lower() if isinstance(x, str) else x for x in item
                    ]
                else:
                    processed = item
                processed_lists.append(processed)
            else:
                processed_lists.append([item])

        main_list = processed_lists[0]
        other_lists = processed_lists[1:]

        # Find the intersection by keeping only common elements in the same order
        if method == "intersection":
            result = []
            for item in main_list:
                if all(item in s for s in other_lists):
                    result.append(item)

        # Find the difference by keeping elements that are in any lists but not in the main list
        elif method == "difference":
            result = [
                item for item in main_list if not any(item in s for s in other_lists)
            ]

        elif method == "union":
            seen = []
            result = []
            for lst in processed_lists:
                for item in lst:
                    if item not in seen:
                        seen.append(item)
                        result.append(item)

        # Handle remove_duplicates
        result = _compare.deduplicate(result, remove_duplicates, ignore_case)

        return result

    # Apply the comparison function to each row
    df[output] = df[input].apply(compare_lists, axis=1)

    return df


def text(
    df: _pd.DataFrame,
    input: list,
    output: str,
    method: str = "difference",
    # Overlap parameters
    char: str = " ",
    # match parameters
    non_match_char: str = "*",
    include_ratio: bool = False,
    decimal_places: int = 3,
    exact_match: str = None,
    empty_a: str = None,
    empty_b: str = None,
    all_empty: str = None,
    case_sensitive: bool = True,
) -> _pd.DataFrame:
    """
    type: object
    description: Compare two strings and return the intersection or difference, or use overlap to find the matching characters between the two strings.
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
            case_sensitive:
              type: boolean
              description: "(Optional) Whether the comparison is case sensitive. Default is True"
      - if:
          properties:
            method:
              const: intersection
        then:
          properties:
            char:
              type: string
              description: "(Optional) The character to split the strings on. Default is a space"
            case_sensitive:
              type: boolean
              description: "(Optional) Whether the comparison is case sensitive. Default is True"
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
            exact_match:
              type: string
              description: "(Optional) Value to use for exact matches"
            empty_a:
              type: string
              description: "(Optional) Value to use for empty input a"
            empty_b:
              type: string
              description: "(Optional) Value to use for empty input b"
            all_empty:
              type: string
              description: "(Optional) Value to use for both inputs"
            case_sensitive:
              type: boolean
              description: "(Optional) Whether the comparison is case sensitive. Default is True"

    """
    if method not in ["difference", "intersection", "overlap"]:
        raise ValueError(
            "Method must be one of 'overlap', 'difference' or 'intersection'"
        )

    if method == "difference" or method == "intersection":
        # ensure that input is at least a list of two columns
        if not isinstance(input, list) or len(input) < 2:
            raise ValueError("Input must be a list of at least two columns")

        df[output] = _compare.contrast(
            input=df[input].astype(str).values.tolist(),
            type=method,
            char=char,
            case_sensitive=case_sensitive,
        )

    if method == "overlap":
        if isinstance(decimal_places, str):
            int(decimal_places)

        # ensure that input is a list of two columns
        if not isinstance(input, list) or len(input) != 2:
            raise ValueError("Input must be a list of two columns")

        df[output] = _compare.overlap(
            input=df[input].astype(str).values.tolist(),
            non_match_char=non_match_char,
            include_ratio=include_ratio,
            decimal_places=decimal_places,
            exact_match=exact_match,
            empty_a=empty_a,
            empty_b=empty_b,
            all_empty=all_empty,
            case_sensitive=case_sensitive,
        )

    return df
