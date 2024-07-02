"""
The matrix connector lets you use variables in a single write definition to
automatically execute multiple writes that are based on the combinations of the variables. 
"""
import re as _re
import itertools as _itertools
from collections import ChainMap as _chainmap
from typing import Union as _Union
import types as _types
import concurrent.futures as _futures
import wrangles as _wrangles
import pandas as _pd
import yaml as _yaml


_schema = {}


def write(
    df: _pd.DataFrame,
    variables: dict,
    write: list,
    functions: _Union[_types.FunctionType, list] = [],
    strategy: str = "loop"
):
    """
    The matrix write connector lets you use variables in a single write definition to
    automatically execute multiple writes that are based on the combinations of the variables.

    :param df: The input dataframe
    :param variables: A list of variables. The write will be execute once for \
        each combination of variables.
    :param write: The write section of a recipe to execute for each \
        combination of variables
    :param functions: Custom functions to provide to the write recipes
    :param strategy: Determines how to combine variables when there are multiple. \
        loop (default) iterates over each set of variables, repeating shorter lists until the longest \
        is completed. permutations uses the combination of all variables against all other variables. \
    """
    def _zip_cycle(*iterables, empty_default=None):
        cycles = [_itertools.cycle(i) for i in iterables]
        for _ in _itertools.zip_longest(*iterables):
            yield dict(_chainmap(*[next(i, empty_default) for i in cycles]))

    permutations = []

    for key, val in variables.items():
        if isinstance(val, list):
            vals = val
        
        elif _re.fullmatch(r'set\((.*)\)', val.strip()):
            column_name = _re.fullmatch(r'set\((.*)\)', val.strip())[1]
            vals = list(dict.fromkeys(df[column_name]))

        elif _re.fullmatch(r'custom.(.*)', val.strip()):
            # Run custom function
            vals = functions[val.strip()[7:]]()
        
        else:
            vals = [val]

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

    with _futures.ThreadPoolExecutor(max_workers=min(len(permutations), 10)) as executor:
        for permutation in permutations:
            executor.submit(
                _wrangles.recipe.run,
                recipe= _yaml.dump({'write': write}, sort_keys=False),
                dataframe=df.copy(),
                variables=permutation,
                functions=functions
            )


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
"""
