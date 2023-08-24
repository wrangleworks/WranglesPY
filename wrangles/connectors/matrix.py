"""
The matrix connector lets you use variables in a single write definition to
automatically execute multiple writes that are based on the combinations of the variables. 
"""
import re as _re
import itertools as _itertools
from collections import ChainMap as _chainmap
from typing import Union as _Union
import types as _types
import wrangles as _wrangles
import pandas as _pd
import yaml as _yaml


_schema = {}


def write(
    df: _pd.DataFrame,
    variables: dict,
    write: list,
    functions: _Union[_types.FunctionType, list] = []
):
    """
    The matrix write connector lets you use variables in a single write definition to
    automatically execute multiple writes that are based on the combinations of the variables. 
    """
    permutations = []

    for key, val in variables.items():
        if isinstance(val, list):
            vals = val
        
        elif _re.fullmatch(r'set\((.*)\)', val.strip()):
            column_name = _re.fullmatch(r'set\((.*)\)', val.strip())[1]
            vals = list(set(df[column_name]))

        elif _re.fullmatch(r'custom.(.*)', val.strip()):
            # Run custom function
            pass
        
        else:
            vals = [val]

        permutations.append([{key: var} for var in vals])

    # Calc all permutations
    permutations = list(_itertools.product(*permutations))
    permutations = [
        dict(_chainmap(*permutation))
        for permutation in permutations
    ]

    for permutation in permutations:
        _wrangles.recipe.run(
            _yaml.dump({'write': write}),
            dataframe=df,
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
      A list of variables. The write will be execute once for 
      each combination of variables.
  write:
    type: array
    description: The write to use
    minItems: 1
    items:
      - $ref: "#/$defs/write/items"
"""