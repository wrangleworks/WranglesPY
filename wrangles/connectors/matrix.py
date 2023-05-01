"""

"""
import re as _re
import itertools as _itertools
from collections import ChainMap as _chainmap
import wrangles as _wrangles
import pandas as _pd
import yaml as _yaml


def write(df: _pd.DataFrame, keys: list, write: list):
    """
    """
    permutations = []

    for key, val in keys.items():
        if isinstance(val, list):
            vals = val
        
        elif _re.fullmatch(r'set\((.*)\)', val.strip()):
            column_name = _re.fullmatch(r'set\((.*)\)', val.strip())[1]
            vals = list(set(df[column_name]))

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
            variables=permutation
        )


"""
write:
  - matrix:
      keys:
        filename: set(header)
        filename2: [a, b, c]
      write:
        - file:
            name: ${filename}-${filename2}.csv
            where: header = '${filename}'
    
"""