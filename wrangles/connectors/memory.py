"""
The memory connector allows saving dataframes and
variables in memory for communication between successive wrangles 
and recipes. All contents of the memory connector are lost once the
python script finishes executing.
"""
_schema = {}

dataframes = []
variables = {}


def write(df, **kwargs):
    """
    """
    dataframes.append({
        **df.to_dict(orient='split'),
        **kwargs
    })


_schema['write'] = """
type: object
description: >-
  The memory connector allows saving dataframes and
  variables in memory for communication between successive wrangles 
  and recipes. All contents of the memory connector are lost once the
  python script finishes executing.
"""
