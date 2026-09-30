"""Explicit saved-model lookup operations for recipes."""
from typing import Union as _Union

import pandas as _pd

from .main import _lookup_with_variant


def key(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    model_id: str,
    output: _Union[str, list] = None,
    lookup_mode: str = 'by_row',
    n: int = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Look up values using a saved key lookup model. Requires a WrangleWorks
      account and a model with purpose lookup and stored variant key.
      Missing or unknown variants are rejected; use lookup for legacy models.
    additionalProperties: true
    required: [input, model_id]
    allOf:
      - if:
          required: [n]
          properties:
            n: {type: integer}
        then:
          properties:
            lookup_mode: {const: by_row}
      - if:
          required: [lookup_mode]
          properties:
            lookup_mode: {const: by_matrix}
        then:
          required: [matrix_variables]
    properties:
      input:
        type: [string, integer, array]
        items:
          type: [string, integer]
        minItems: 1
        maxItems: 1
        description: One input column, optionally expressed as a single-item list.
      model_id:
        type: string
        description: Existing saved key lookup model ID, not a catalog ID.
      output:
        type: [string, array, 'null']
        default: null
        description: >-
          Output column or columns; defaults to the input column. Named lookup
          columns return their values; other names receive match dictionaries.
          With n greater than one, n output columns or a wildcard name such as
          'Match *' distribute match dictionaries across columns.
      lookup_mode:
        type: string
        default: by_row
        enum: [by_row, by_dataframe, by_matrix]
        description: >-
          Look up each row, each distinct input, or each matrix permutation.
          by_matrix requires matrix_variables in the forwarded options.
      matrix_variables:
        type: array
        minItems: 1
        items: {type: string}
        description: Columns that define the permutations for by_matrix mode.
      n:
        type: [integer, 'null']
        default: null
        description: >-
          Optional number of matches using the existing lookup behavior.
          Supported only with by_row. When greater than one, a single output
          contains a list of match dictionaries unless expanded with a wildcard.
    examples:
      - input: ProductCode
        output: KeyResult
        model_id: '${KEY_LOOKUP_MODEL_ID}'
    """
    return _lookup_with_variant(
        'key', df, input, output, model_id, lookup_mode, n, **kwargs
    )


def semantic(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    model_id: str,
    output: _Union[str, list] = None,
    lookup_mode: str = 'by_row',
    n: int = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: >-
      Look up values using a saved semantic lookup model. Requires a WrangleWorks
      account and a model with purpose lookup and stored variant embedding.
      Missing or unknown variants are rejected; use lookup for legacy models.
    additionalProperties: true
    required: [input, model_id]
    allOf:
      - if:
          required: [n]
          properties:
            n: {type: integer}
        then:
          properties:
            lookup_mode: {const: by_row}
      - if:
          required: [lookup_mode]
          properties:
            lookup_mode: {const: by_matrix}
        then:
          required: [matrix_variables]
    properties:
      input:
        type: [string, integer, array]
        items:
          type: [string, integer]
        minItems: 1
        maxItems: 1
        description: One input column, optionally expressed as a single-item list.
      model_id:
        type: string
        description: Existing saved semantic lookup model ID, not a catalog ID.
      output:
        type: [string, array, 'null']
        default: null
        description: >-
          Output column or columns; defaults to the input column. Named lookup
          columns return their values; other names receive match dictionaries.
          With n greater than one, n output columns or a wildcard name such as
          'Match *' distribute match dictionaries across columns.
      lookup_mode:
        type: string
        default: by_row
        enum: [by_row, by_dataframe, by_matrix]
        description: >-
          Look up each row, each distinct input, or each matrix permutation.
          by_matrix requires matrix_variables in the forwarded options.
      matrix_variables:
        type: array
        minItems: 1
        items: {type: string}
        description: Columns that define the permutations for by_matrix mode.
      n:
        type: [integer, 'null']
        default: null
        description: >-
          Optional number of matches. Supported only with by_row. When greater
          than one, a single output contains a list of match dictionaries unless
          expanded with a wildcard. Each of n output columns receives one match.
    examples:
      - input: Description
        output: 'Match *'
        model_id: '${SEMANTIC_LOOKUP_MODEL_ID}'
        n: 3
    """
    return _lookup_with_variant(
        'semantic', df, input, output, model_id, lookup_mode, n, **kwargs
    )
