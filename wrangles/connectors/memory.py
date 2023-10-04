"""
The memory connector allows saving dataframes and
variables in memory for communication between successive wrangles 
and recipes. All contents of the memory connector are lost once the
python script finishes executing.

>>> from wrangles.connectors import memory
>>> memory.dataframes
>>> memory.variables
>>> memory.queue
"""
import uuid as _uuid
from collections import deque as _deque
import pandas as _pandas

_schema = {}

dataframes = {}
variables = {}
queue = _deque([])

def clear():
    """
    Clear and reset any existing data
    stored in the connector
    """
    global dataframes, variables, queue
    dataframes = {}
    variables = {}
    queue = _deque([])


def read(id: str = None, orient: str = "tight", **kwargs):
    """
    Read a dataframe previous saved in memory

    >>> from wrangles.connectors import memory
    >>> memory.read(
    >>>    id="find_me_later",
    >>>    custom_key="custom_value"
    >>> )

    :param df: Dataframe to be exported
    :param id: A unique ID to identify the data. \
        If not specified, will read the last dataframe \
        saved in memory
    :param orient: Set the arrangement of the data. \
        See pandas.DataFrame.to_dict method for options. \
        Default is tight.
    """
    # If there isn't anything saved
    if not dataframes:
        raise RuntimeError("No saved dataframes found.")

    # Either read the last dataframe
    # or the specific one set by the user
    if id is None:
        data = list(dataframes.values())[-1]
    else:
        if id not in dataframes:
            raise RuntimeError(f"Dataframe {id} not found.")
        data = dataframes[id]

    if orient == "split":
        # Ensure custom user keys aren't included
        data = {
            k: v
            for k, v in data.items()
            if k in ["data", "columns", "index"]
        }
        return _pandas.DataFrame(**data)
    elif orient in ["tight", "index"]:
        return _pandas.DataFrame().from_dict(data, orient=orient)
    else:
        return _pandas.DataFrame(data)


_schema['read'] = """
type: object
description: >-
  The memory connector allows saving dataframes and
  variables in memory for communication between successive wrangles
  and recipes. All contents of the memory connector are lost once the
  python script finishes executing.
properties:
  id:
    type: string
    description: >-
      A unique ID to identify the data.
      If not specified, will read the last
      dataframe saved in memory
  orient:
    type: string
    enum:
      - dict
      - list
      - split
      - tight
      - index
    description: >-
      Set the arrangement of the data.
      See pandas.DataFrame.to_dict method for options.
      Default is tight
"""

def write(df, id: str = None, orient: str = "tight", **kwargs):
    """
    Write a dataframe to memory for reference later

    >>> from wrangles.connectors import memory
    >>> memory.write(
    >>>    df,
    >>>    id="find_me_later",
    >>>    custom_key="custom_value"
    >>> )

    :param df: Dataframe to be exported
    :param id: A unique ID to identify the data
    :param orient: Set the arrangement of the data. \
        See pandas.DataFrame.to_dict method for options. \
        Default is tight.
    """
    if id is None:
        id = _uuid.uuid4()

    dataframes[id] = {
        **df.to_dict(orient=orient),
        **kwargs
    }


_schema['write'] = """
type: object
description: >-
  The memory connector allows saving dataframes and
  variables in memory for communication between successive wrangles
  and recipes. All contents of the memory connector are lost once the
  python script finishes executing.
properties:
  id:
    type: string
    description: A unique ID to identify the data
  orient:
    type: string
    enum:
      - dict
      - list
      - split
      - tight
      - index
    description: >-
      Set the arrangement of the data.
      See pandas.DataFrame.to_dict method for options.
      Default is tight
"""
