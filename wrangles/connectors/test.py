"""
Generate test data with fixed or randomly generated values
"""
import pandas as _pd
import logging as _logging
from lorem.text import TextLorem as _TextLorem
import random as _random
import string as _string
from typing import Union as _Union
import re as _re


_lorem = _TextLorem()


_schema = {}


def _generate_cell_values(data_type: _Union[str, list], rows: int):
    """
    Create a list of a set length (rows) of test data. Either the input string will
    be used, or certain codes can cause random input generation.

    :param data_type: String or code to create random data
    :param rows: Number of rows to create
    """
    if isinstance(data_type, list):
        return [data_type[_random.randint(0, len(data_type) - 1)] for _ in range(rows)]
    elif isinstance(data_type, str):
        if data_type == '<char>':
            return [_random.choice(_string.ascii_lowercase) for _ in range(rows)]

        elif data_type == '<word>':
            return [_lorem._word() for _ in range(rows)]

        elif data_type == '<sentence>':
            return [_lorem.sentence()[:-1] for _ in range(rows)]

        elif data_type == '<boolean>':
            return [bool(_random.getrandbits(1)) for _ in range(rows)]

        elif _re.match(r'^\<int(\(\d+-\d+\))?\>$', data_type):
            # Match <int(1-10)> -> where (1-10) sets the range
            try:
                int_range = _re.findall('\((\d+-\d+)\)', data_type)[0].split("-")
                int_range = [int(val) for val in int_range]
            except:
                int_range = [1, 100]
            return [_random.randint(int_range[0], int_range[1]) for _ in range(rows)]

        elif _re.match(r'^\<number(\(\d+(\.\d+)?-\d+(\.\d+)?\))?\>$', data_type):
            # Match <number(2.718-3.141)> -> where (2.718-3.141) sets the range and number of decimal places
            try:
                num_range = _re.findall('\((\d+(\.\d+)?-\d+(\.\d+)?)\)', data_type)[0][0].split("-")
                try:
                    num_decimals = len(num_range[0].split('.')[1])
                except:
                    num_decimals = 0
            except:
                num_range = [0, 1]
                num_decimals = 2
            return [round(_random.uniform(float(num_range[0]), float(num_range[1])), num_decimals) for _ in range(rows)]

        elif _re.match('^\<code(\(\d+\))?\>$', data_type):
            # Match <code> or <code(8)> -> where (8) sets the length, default 8
            try:
                length = int(_re.findall('\((\d+)\)', data_type)[0])
            except:
                length = 8
            return [''.join(_random.choice(_string.ascii_uppercase + _string.digits) for _ in range(length)) for _ in range(rows)]

        else:
            return [data_type for _ in range(rows)]
    else:
        return [data_type for _ in range(rows)]


def read(rows: int, values: dict = {}) -> _pd.DataFrame:
    """
    Create a test dataframe

    >>> from wrangles.connectors import test
    >>> df = test.read(rows=5, values={'header1':'a','header2':'b'})

    Special inputs to generate random data:
    <code> or <code(10)> : Random alphanumeric codes (10) sets the length. e.g. J1RSB7X9 
    <char> : Random letters
    <word> : Random nonsense words
    <sentence> : Random nonsense sentences
    <boolean> : Randomly True or False
    <number(2.718-3.141)> : Random numbers (2.718-3.141) sets the range and decimal places
    <int(1-10)> : Random integers (1-10) sets the range

    :param rows: Number of rows to include in the created dataframe
    :param values: Dictionary of header and values
    :return: Pandas Dataframe of the created data
    """
    _logging.info(f": Generating test data :: {rows} row{'s' if rows > 1 else ''}")

    data = {}
    for key, val in values.items():
        data[key] = _generate_cell_values(val, rows)

    df = _pd.DataFrame(data)
    return df


_schema['read'] = """
type: object
description: Create a test dataframe
required:
  - rows
  - values
properties:
  rows:
    type: integer
    description: Number of rows to include in the generated dataframe
    minimum: 1
  values:
    type: object
    description: Dictionary of columns and values
    patternProperties:
      ".*":
        type:
          - object
          - string
          - array
        description: Dictionary of headers and data type to randomly generate
        additionProperties: true
"""