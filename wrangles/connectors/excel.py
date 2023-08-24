"""

"""
_schema = {}

stored_dfs = []


def write(df, **kwargs):
    """
    """
    stored_dfs.append({
        "columns": df.columns.tolist(),
        "values": df.values.tolist(),
        **kwargs
    })


_schema['write'] = """
type: object
description: Define the output
properties:
  sheet:
    type: string
    description: The name of the sheet to write the results to
  
"""
