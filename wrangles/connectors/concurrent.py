"""
Utility connector that allows running
other write connectors concurrently.
"""
import pandas as _pd
import wrangles as _wrangles
import concurrent.futures as _futures
import types as _types
from typing import Union as _Union


_schema = {}

def write(
    df: _pd.DataFrame,
    write: list,
    max_concurrency: int = 10,
    variables: dict = {},
    functions: _Union[_types.FunctionType, list] = [],
):
    """
    """
    with _futures.ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        futures = []
        for write_definition in write:
            future = executor.submit(
                _wrangles.recipe.run,
                recipe= {'write': write_definition},
                dataframe=df.copy(),
                variables=variables,
                functions=functions
            )
            futures.append(future)
        
        # Wait for all futures to complete
        for future in futures:
            future.result()

_schema['write'] = """
type: object
description: >-
  The concurrent connector lets you run multiple write connectors
  in parallel rather than sequentially
required:
  - write
properties:
  write:
    type: array
    description: >-
      The write section of a recipe to execute for each
      combination of variables
    minItems: 1
    items:
      - $ref: "#/$defs/write/items"
  max_concurrency:
    type: integer
    description: >-
      The maximum number of writes to execute in parallel
    minimum: 1
"""
