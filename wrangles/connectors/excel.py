"""
Connector intended to be used by recipes within Excel
This stores the results within the memory connector
to be returned to Excel.
"""
from . import memory as _memory

_schema = {}

def write(df, **kwargs):
    """
    """
    _memory.write(df, **kwargs)

_schema['write'] = """
type: object
description: Define the output
properties:
  sheet:
    type: string
    description: The name of the sheet to write the results to  
"""
