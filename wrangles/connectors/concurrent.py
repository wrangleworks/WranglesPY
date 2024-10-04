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

def run(
    run: list,
    max_concurrency: int = 10,
    variables: dict = {},
    functions: _Union[_types.FunctionType, list] = [],
    use_multiprocessing: bool = False
):
    """
    Run multiple actions concurrently.

    :param run: List of actions to run concurrently
    :param max_concurrency: Maximum number to run concurrently. If more, the rest will be queued.
    :param variables: Variables to pass to any downstream recipes
    :param functions: Custom functions to pass to any downstream recipes
    :param use_multiprocessing: Use multiprocessing instead of threading. Default is False.
    """
    if use_multiprocessing:
        # Not publicly documented. Use at your own risk.
        pool_executor = _futures.ProcessPoolExecutor
    else:
        pool_executor = _futures.ThreadPoolExecutor

    with pool_executor(max_workers=max_concurrency) as executor:
        futures = []
        for run_definition in run:
            future = executor.submit(
                _wrangles.recipe.run,
                recipe= {'run': {"on_start": [run_definition]}},
                variables=variables,
                functions=functions
            )
            futures.append(future)
        
        # Wait for all futures to complete
        for future in futures:
            future.result()

_schema['run'] = """
type: object
description: >-
  The concurrent connector lets you run multiple actions
  simultaneously rather than sequentially
required:
  - run
properties:
  run:
    type: array
    description: >-
      The write section of a recipe to execute for each
      combination of variables
    minItems: 1
    items:
      - $ref: "#/$defs/run/items"
  max_concurrency:
    type: integer
    description: >-
      The maximum number of writes to execute in parallel
    minimum: 1
"""

def write(
    df: _pd.DataFrame,
    write: list,
    max_concurrency: int = 10,
    variables: dict = {},
    functions: _Union[_types.FunctionType, list] = [],
    use_multiprocessing: bool = False
):
    """
    Run multiple write connectors concurrently.

    :param df: Dataframe to write
    :param write: List of write connectors to run concurrently
    :param max_concurrency: Maximum number to write concurrently. If more, the rest will be queued.
    :param variables: Variables to pass to any downstream recipes
    :param functions: Custom functions to pass to any downstream recipes
    :param use_multiprocessing: Use multiprocessing instead of threading. Default is False.
    """
    if use_multiprocessing:
        # Not publicly documented. Use at your own risk.
        pool_executor = _futures.ProcessPoolExecutor
    else:
        pool_executor = _futures.ThreadPoolExecutor

    with pool_executor(max_workers=max_concurrency) as executor:
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
