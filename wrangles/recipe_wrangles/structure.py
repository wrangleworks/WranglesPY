"""Current structural recipe operations delegating to the legacy split functions."""

from typing import Union as _Union, List as _list

import pandas as _pd

from . import split as _split


def split_dictionary(
    df: _pd.DataFrame,
    input: _Union[str, int, _list],
    output: _Union[str, _list] = None,
    default: dict = None,
    output_format: str = "columns"
) -> _pd.DataFrame:
    """
    type: object
    catalog_id: "63"
    status: active
    description: |-
      Split one or more dictionaries into columns.
      The dictionary keys will be returned as the new column headers.
      Dictionary keys are case-sensitive. With multiple input columns,
      later dictionaries overwrite earlier keys before defaults are applied.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: |-
          Name or list of columns containing dictionaries or JSON object strings to split.
          For overlapping keys, later input columns take precedence
          before defaults are applied.
      output:
        type:
          - string
          - array
        description: |-
          In columns output_format, this is an optional subset of keys to extract
          from the dictionary. If not provided, all keys will be returned.
          Columns can be renamed with the following syntax:
          output:
            - key1: new_column_name1
            - key2: new_column_name2
          In to_lists output_format, this must be two output columns for the keys
          and values lists. If not provided, Keys and Values will be used.
      default:
        type: object
        description: >-
          Provide defaults for missing top-level keys or keys with null values
          after merging the input dictionaries. Keys use their original names
          before output renaming. Non-null values, including 0, false, empty
          strings, lists, and dictionaries, are preserved. Nested values are
          not filled recursively.
          When default is supplied (including {}), invalid or non-dictionary
          input cells are treated as empty dictionaries, so valid values from
          other input columns are retained. Without default, invalid input
          raises an error.
      output_format:
        type: string
        enum:
          - columns
          - to_lists
        description: |-
          How to split the dictionary.
          columns creates one output column for each dictionary key.
          In recipes, remaining null cells are normalized to empty strings.
          to_lists creates two output columns containing lists of keys and values.
          Remaining null values inside these lists are preserved.
    """
    return _split.dictionary(df=df, input=input, output=output, default=default, output_format=output_format)


def split_list(df: _pd.DataFrame, input: _Union[str, int], output: _Union[str, _list]) -> _pd.DataFrame:
    """
    type: object
    catalog_id: "64"
    status: active
    description: Split a list in a single column to multiple columns.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - int
        description: Name of the column to be split
      output:
        type:
          - string
          - array
        description: >-
          Name of column(s) for the results.
          If providing a single column, use a wildcard (*)
          to indicate a incrementing integer
    """
    return _split.list(df=df, input=input, output=output)


def split_text(
    df: _pd.DataFrame,
    input: str,
    output: _Union[str, _list] = None,
    char: str = ',',
    pad: bool = None,
    element: _Union[int, str] = None,
    inclusive: bool = False,
    skip_empty: bool = False
) -> _pd.DataFrame:
    """
    type: object
    catalog_id: "65"
    status: active
    description: Split a string to multiple columns or a list.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the column to be split
      output:
        type:
          - string
          - array
        description: |-
          Name of the output column(s)
          If a single column is provided,
          the results will be returned as a list
          If multiple columns are listed,
          the results will be separated into the columns.
          If omitted, will overwrite the input.
      char:
        type: string
        description: |-
          Set the character(s) to split on.
          Default comma (,)
          Can also prefix with "regex:" to split on a pattern.
      pad:
        type: boolean
        description: >-
          Choose whether to pad to ensure a consistent length.
          Default true if outputting to columns, false for lists.
      element:
        type:
          - integer
          - string
        description: >-
          Select a specific element or range after splitting
          using slicing syntax. e.g. 0, ":5", "5:", "2:8:2"
      inclusive:
        type: boolean
        description: >-
          If true, include the split character in the output.
          Default False
      skip_empty:
        type: boolean
        description: Whether to skip empty values
        default: false
    """
    return _split.text(df=df, input=input, output=output, char=char, pad=pad, element=element, inclusive=inclusive, skip_empty=skip_empty)


def tokenize(
    df: _pd.DataFrame,
    input: _Union[str, int, _list],
    output: _Union[str, _list] = None,
    method: str = 'space',
    functions: dict = None
) -> _pd.DataFrame:
    """
    type: object
    catalog_id: "66"
    status: active
    description: >-
      Split text into tokens. A variety of methods are available.
      The default method is to split on spaces.
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Column(s) to be split into tokens
      output:
        type:
          - string
          - array
        description: Name of the output column
      method:
        anyOf:
          - type: string
            enum:
              - space
              - boundary
              - boundary_ignore_space
            description: >-
              Method to split the list.
              Options: space, boundary, boundary_ignore_space
              or use a custom function with custom.<function>
              or use a regex pattern with regex:<pattern>
          - type: string
            description: >-
              Method to split the list.
              Options: space, boundary, boundary_ignore_space
              or use a custom function with custom.<function>
              or use a regex pattern with regex:<pattern>
    """
    return _split.tokenize(df=df, input=input, output=output, method=method, functions=functions)
