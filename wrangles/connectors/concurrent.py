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
    :param max_concurrency: The maximum number to execute in parallel. If there are more than this, the rest will be queued.
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
    description: Actions to run concurrently
    minItems: 1
    items:
      - $ref: "#/$defs/run/items"
  max_concurrency:
    type: integer
    description: >-
      The maximum number to execute in parallel. If there are
      more than this, the rest will be queued.
    minimum: 1
"""

def read(
    read: list,
    max_concurrency: int = 10,
    use_multiprocessing: bool = False,
    functions: _Union[_types.FunctionType, list, dict] = {},
    variables: dict = {}
):
    """
    Run multiple reads simulatenously.
    This must be nested under a connector that aggregates multiple sources
    such as join, union, or concatenate.

    :param read: List of read connectors to run concurrently
    :param max_concurrency: The maximum number to execute in parallel. If there are more than this, the rest will be queued.
    :param use_multiprocessing: Use multiprocessing instead of threading. Default is False.
    :param functions: Custom functions to make available downstream.
    :param variables: Variables to make available downstream.
    """
    if use_multiprocessing:
        # Not publicly documented. Use at your own risk.
        pool_executor = _futures.ProcessPoolExecutor
    else:
        pool_executor = _futures.ThreadPoolExecutor
    
    with pool_executor(max_workers=max_concurrency) as executor:
        dfs = list(executor.map(
            _wrangles.recipe.run,
            [{'read': [read_definition]} for read_definition in read],
            [variables for _ in read],
            [None for _ in read],
            [functions for _ in read]
        ))

    return dfs

_schema['read'] = """
type: object
description: >-
  The concurrent connector lets you read multiple sources
  simultaneously rather than sequentially.
  This must be nested under a connector that aggregates multiple sources
  such as join, union, or concatenate.
required:
  - read
properties:
  read:
    type: array
    description: Reads to be run concurrently
    minItems: 1
    items:
      - $ref: "#/$defs/read/items"
  max_concurrency:
    type: integer
    description: >-
      The maximum number to execute in parallel. If there are
      more than this, the rest will be queued.
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
    :param max_concurrency: The maximum number to execute in parallel. If there are more than this, the rest will be queued.
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
                recipe= {'write': [write_definition]},
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
    description: Writes to run concurrently
    minItems: 1
    items:
      - $ref: "#/$defs/write/items"
  max_concurrency:
    type: integer
    description: >-
      The maximum number to execute in parallel. If there are
      more than this, the rest will be queued.
    minimum: 1
"""
