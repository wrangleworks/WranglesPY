"""
The matrix connector lets you use variables to define multiple actions
that are executed based on the combinations of those variables. 
"""
import re as _re
import itertools as _itertools
from collections import ChainMap as _chainmap
from typing import Union as _Union
import types as _types
import concurrent.futures as _futures
import wrangles as _wrangles
import pandas as _pd
from ..utils import get_nested_function as _get_nested_function
import os as _os


_schema = {}

def _define_permutations(
    variables: dict,
    strategy: str = "loop",
    functions: dict = {},
    df: _pd.DataFrame = None
):

    def _zip_cycle(*iterables, empty_default=None):
        cycles = [_itertools.cycle(i) for i in iterables]
        for _ in _itertools.zip_longest(*iterables):
            yield dict(_chainmap(*[next(i, empty_default) for i in cycles]))

    permutations = []

    for key, val in variables.items():
        # User provided a list
        if isinstance(val, list):
            vals = val

        # set(column) - unique values in a column 
        elif _re.fullmatch(r'set\((.*)\)', val.strip()):
            column_name = _re.fullmatch(r'set\((.*)\)', val.strip())[1]

            if df is None or not isinstance(df, _pd.DataFrame):
                raise ValueError("The set(column_name) syntax is not valid for this type of matrix.")

            if column_name not in df.columns:
                raise ValueError(f"{column_name} not recognized as a valid column")

            try:
                # Fast path for hashable types
                vals = list(dict.fromkeys(df[column_name]))
            except TypeError:
                # Fallback for non-hashable types (lists, dicts, etc.)
                # Use pandas drop_duplicates which handles most non-hashable types
                vals = df[column_name].drop_duplicates().tolist()

        # dir(path) - List a directory 
        elif _re.fullmatch(r'dir\((.*)\)', val.strip()):
            directory = _re.fullmatch(r'dir\((.*)\)', val.strip())[1]
            # Ensure directory doesn't end with a slash
            if directory.endswith('/'):
                directory = directory[:-1]
            vals = [
                '/'.join([directory, fname])
                for fname in sorted(_os.listdir(directory))
            ]

        # Use a custom function
        elif _re.fullmatch(r'custom.(.*)', val.strip()):
            vals = _get_nested_function(val, custom_functions=functions)()

        else:
            vals = [val]

        # Ensure vals is a list
        if not isinstance(vals, list):
            vals = [vals]

        permutations.append([{key: var} for var in vals])

    if strategy.lower() == "permutations":
        # Calc all permutations
        permutations = list(_itertools.product(*permutations))
        permutations = [
            dict(_chainmap(*permutation))
            for permutation in permutations
        ]
    elif strategy.lower() == "loop":
        permutations = [
            permutation
            for permutation in _zip_cycle(*permutations)
        ]
    else:
        raise ValueError(f"Invalid setting {strategy} for strategy")
    
    return permutations


def run(
    variables: dict,
    run: list,
    functions: dict = {},
    strategy: str = "loop",
    use_multiprocessing: bool = False,
    max_concurrency: int = 10
):
    """
    The matrix connector lets you use variables to automatically execute
    multiple actions based on the combinations of those variables.

    :param df: The input dataframe
    :param variables: A list of variables. The action will be execute once for \
        each combination of variables.
    :param run: The run section of a recipe to execute for each \
        combination of variables
    :param functions: Any user defined custom functions
    :param strategy: Determines how to combine variables when there are multiple. \
        loop (default) iterates over each set of variables, repeating shorter lists until the longest \
        is completed. permutations uses the combination of all variables against all other variables. \
    :param use_multiprocessing: Use multiprocessing instead of threading
    :param max_concurrency: The maximum number to execute in parallel. If there are more than this, the rest will be queued.
    """    
    if use_multiprocessing:
        # Not publicly documented. Use at your own risk.
        pool_executor = _futures.ProcessPoolExecutor
    else:
        pool_executor = _futures.ThreadPoolExecutor

    with pool_executor(max_workers=max_concurrency) as executor:
        futures = []
        for permutation in _define_permutations(
            variables=variables,
            strategy=strategy,
            functions=functions
        ):
            future = executor.submit(
                _wrangles.recipe.run,
                recipe={'run': {"on_start": run}},
                variables=permutation,
                functions=functions
            )

            # Wait for all futures to complete
            for future in futures:
                future.result()

_schema['run'] = """
type: object
description: >-
  The matrix connector lets you use variables to automatically execute
  multiple actions based on the combinations of those variables.
required:
  - variables
  - run
properties:
  variables:
    type: object
    description: >-
      A set of variables as key/values.
      The action will be execute once for each combination of variables.\n
      Values may be a single value or a list or reference a custom function.
  run:
    type: array
    description: >-
      The run section of a recipe to execute for each
      combination of variables
    minItems: 1
    items:
      - $ref: "#/$defs/run/items"
  strategy:
    type: string
    enum:
      - permutations
      - loop
    description: >-
      Determines how to combine variables when there are multiple.
      loop (default) iterates over each set of variables, repeating shorter lists 
      until the longest is completed. permutations uses the combination of all 
      variables against all other variables.
  max_concurrency:
    type: integer
    minimum: 1
    description: >-
      The maximum number to execute in parallel. If there are
      more than this, the rest will be queued. Default 10.
"""

def read(
    variables: dict,
    read: list,
    functions: dict = {},
    strategy: str = "loop",
    use_multiprocessing: bool = False,
    max_concurrency: int = 10
):
    """
    The matrix connector lets you use variables to automatically execute
    multiple reads that are based on the combinations of the variables.

    :param df: The input dataframe
    :param variables: A list of variables. The read will be execute once for \
        each combination of variables.
    :param read: The read section of a recipe to execute for each combination of variables
    :param functions: Any user defined custom functions
    :param strategy: Determines how to combine variables when there are multiple. \
        loop (default) iterates over each set of variables, repeating shorter lists until the longest \
        is completed. permutations uses the combination of all variables against all other variables. \
    :param use_multiprocessing: Use multiprocessing instead of threading
    :param max_concurrency: The maximum number to execute in parallel. If there are more than this, the rest will be queued.
    """    
    if use_multiprocessing:
        # Not publicly documented. Use at your own risk.
        pool_executor = _futures.ProcessPoolExecutor
    else:
        pool_executor = _futures.ThreadPoolExecutor

    with pool_executor(max_workers=max_concurrency) as executor:
        permutations = _define_permutations(
            variables=variables,
            strategy=strategy,
            functions=functions
        )

        dfs = list(executor.map(
            _wrangles.recipe.run,
            [{'read': read} for _ in permutations],
            permutations,
            [None for _ in permutations],
            [functions for _ in permutations]
        ))

    return dfs

_schema['read'] = """
type: object
description: >-
  The matrix connector lets you use variables to automatically execute
  multiple reads that are based on the combinations of the variables.
  If the outputs of the reads are not otherwise aggregated,
  they will be merged together via a union.
required:
  - variables
  - read
properties:
  variables:
    type: object
    description: >-
      A set of variables as key/values.
      The action will be execute once for each combination of variables.\n
      Values may be a single value or a list or reference a custom function.
  read:
    type: array
    description: >-
      The read section of a recipe to execute for each
      combination of variables
    minItems: 1
    items:
      - $ref: "#/$defs/read/items"
  strategy:
    type: string
    enum:
      - permutations
      - loop
    description: >-
      Determines how to combine variables when there are multiple.
      loop (default) iterates over each set of variables, repeating shorter lists 
      until the longest is completed. permutations uses the combination of all 
      variables against all other variables.
  max_concurrency:
    type: integer
    minimum: 1
    description: >-
      The maximum number to execute in parallel. If there are
      more than this, the rest will be queued. Default 10.
"""

def write(
    df: _pd.DataFrame,
    variables: dict,
    write: list,
    functions: _Union[_types.FunctionType, list, dict] = {},
    strategy: str = "loop",
    use_multiprocessing: bool = False,
    max_concurrency: int = 10
):
    """
    The matrix connector lets you use variables in a single write definition to
    automatically execute multiple writes that are based on the combinations of the variables.

    :param df: The input dataframe
    :param variables: A list of variables. The write will be execute once for \
        each combination of variables.
    :param write: The write section of a recipe to execute for each \
        combination of variables
    :param functions: Any user defined custom functions
    :param strategy: Determines how to combine variables when there are multiple. \
        loop (default) iterates over each set of variables, repeating shorter lists until the longest \
        is completed. permutations uses the combination of all variables against all other variables. \
    :param use_multiprocessing: Use multiprocessing instead of threading
    :param max_concurrency: The maximum number to execute in parallel. If there are more than this, the rest will be queued.
    """    
    if use_multiprocessing:
        # Not publicly documented. Use at your own risk.
        pool_executor = _futures.ProcessPoolExecutor
    else:
        pool_executor = _futures.ThreadPoolExecutor

    with pool_executor(max_workers=max_concurrency) as executor:
        futures = []
        for permutation in _define_permutations(
            variables=variables,
            strategy=strategy,
            functions=functions,
            df=df
        ):
            future = executor.submit(
                _wrangles.recipe.run,
                recipe={'write': write},
                dataframe=df.copy(),
                variables=permutation,
                functions=functions
            )

            # Wait for all futures to complete
            for future in futures:
                future.result()

_schema['write'] = """
type: object
description: >-
  The matrix connector lets you use variables in a single write definition to
  automatically execute multiple writes that are based on the combinations of the variables. 
required:
  - variables
  - write
properties:
  variables:
    type: object
    description: >-
      A set of variables as key/values.
      The write will be execute once for each combination of variables.\n
      Values may be a single value or a list,
      may use custom functions and may use the special syntax
      set(column_name) to use the unique values from a column.
  write:
    type: array
    description: >-
      The write section of a recipe to execute for each
      combination of variables
    minItems: 1
    items:
      - $ref: "#/$defs/write/items"
  strategy:
    type: string
    enum:
      - permutations
      - loop
    description: >-
      Determines how to combine variables when there are multiple.
      loop (default) iterates over each set of variables, repeating shorter lists 
      until the longest is completed. permutations uses the combination of all 
      variables against all other variables.
  max_concurrency:
    type: integer
    minimum: 1
    description: >-
      The maximum number to execute in parallel. If there are
      more than this, the rest will be queued. Default 10.
"""
