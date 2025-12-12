"""
Connector to read & write JSON and JSONL files

This connector provides explicit parameter handling for JSON formats,
avoiding argument compatibility issues with pandas read_json/to_json.

Key differences from the file connector:
- Explicit parameters for JSON vs JSONL formats
- nrows only available for JSONL (lines=True)
- Clear documentation of valid parameters for each format
"""
import logging as _logging
import os as _os
import re as _re
from io import BytesIO as _BytesIO
from typing import Union as _Union

import pandas as _pd

from ..utils import wildcard_expansion as _wildcard_expansion

_schema = {}


def read(
    name: str,
    columns: _Union[str, list] = None,
    orient: str = None,
    typ: str = 'frame',
    dtype: _Union[dict, bool] = None,
    convert_axes: bool = None,
    convert_dates: _Union[bool, list] = True,
    keep_default_dates: bool = True,
    precise_float: bool = False,
    date_unit: str = None,
    encoding: str = None,
    encoding_errors: str = 'strict',
    lines: bool = None,
    chunksize: int = None,
    compression: str = 'infer',
    nrows: int = None,
    **kwargs
):
    """
    Import a JSON or JSONL file with explicit parameter handling.
    
    This connector provides clear parameter validation to avoid issues
    with incompatible arguments being passed to pandas.
    
    >>> df = wrangles.connectors.json.read('myfile.json')
    >>> df = wrangles.connectors.json.read('myfile.jsonl')
    >>> # Read in chunks for large files
    >>> for chunk in wrangles.connectors.json.read('large.jsonl', chunksize=1000):
    >>>     process(chunk)
    
    :param name: Path to the JSON or JSONL file
    :param columns: (Optional) Subset of columns to read. If not provided, all columns will be included
    :param orient: Format of the JSON string. Valid values: 'split', 'records', 'index', 'columns', 'values'. Default varies by file type
    :param typ: Type of object to recover. Default 'frame' (DataFrame)
    :param dtype: If True, infer dtypes; if a dict, specify column dtypes; if False, don't infer dtypes
    :param convert_axes: Try to convert the axes to proper dtypes
    :param convert_dates: List of columns to parse as dates or True to try parsing all
    :param keep_default_dates: If parsing dates, parse the default datelike columns
    :param precise_float: Use higher precision (strtod) for decoding floating point values
    :param date_unit: Timestamp unit for conversion ('s', 'ms', 'us', 'ns')
    :param encoding: Encoding to use for UTF when reading/writing. Default 'utf-8'
    :param encoding_errors: How to handle encoding errors. Default 'strict'
    :param lines: Read file as line-delimited JSON (JSONL format). Auto-detected based on extension
    :param chunksize: Return an iterator yielding DataFrames with this many records per chunk
    :param compression: Compression to use. Options: 'infer', 'gzip', 'bz2', 'zip', 'xz', None
    :param nrows: Number of lines to read. Only valid when lines=True (JSONL format)
    :return: A Pandas DataFrame of the imported data, or an iterator of DataFrames if chunksize is specified
    """
    _logging.info(f": Reading data from JSON file :: {name}")
    
    if lines is None:
        if name.split('.')[-1] == 'jsonl' or '.'.join(name.split('.')[-2:]) == 'jsonl.gz':
            lines = True
        else:
            lines = False
    
    # Add parameter validation for JSONL (lines=True)
    if nrows is not None and not lines:
        raise ValueError(
            "Parameter 'nrows' is only supported for JSONL files (lines=True). "
            "For regular JSON files, read the entire file and use DataFrame slicing instead."
        )
    

    pandas_kwargs = {}
    
    if orient is not None:
        pandas_kwargs['orient'] = orient
    elif lines:
        pandas_kwargs['orient'] = 'records'
    
    if typ != 'frame':
        pandas_kwargs['typ'] = typ
    
    if dtype is not None:
        pandas_kwargs['dtype'] = dtype
    
    if convert_axes is not None:
        pandas_kwargs['convert_axes'] = convert_axes
    
    if convert_dates is not True:
        pandas_kwargs['convert_dates'] = convert_dates
    
    if not keep_default_dates:
        pandas_kwargs['keep_default_dates'] = keep_default_dates
    
    if precise_float:
        pandas_kwargs['precise_float'] = precise_float
    
    if date_unit is not None:
        pandas_kwargs['date_unit'] = date_unit
    
    if encoding is not None:
        pandas_kwargs['encoding'] = encoding
    
    if encoding_errors != 'strict':
        pandas_kwargs['encoding_errors'] = encoding_errors
    
    if lines:
        pandas_kwargs['lines'] = True
    
    if chunksize is not None:
        pandas_kwargs['chunksize'] = chunksize
    
    if compression != 'infer':
        pandas_kwargs['compression'] = compression
    
    if nrows is not None:
        pandas_kwargs['nrows'] = nrows
    
    pandas_kwargs.update(kwargs)
    
    try:
        result = _pd.read_json(name, **pandas_kwargs)
    except TypeError as e:
        raise TypeError(
            f"Error reading JSON file: {e}\n"
            "This may be due to incompatible parameters. "
            "Note: 'nrows' is only valid for JSONL files."
        ) from e
    
    # If chunksize is specified, result is a JsonReader (iterator)
    # We need to wrap it to apply fillna and column filtering to each chunk
    if chunksize is not None:
        def process_chunks(reader):
            """Generator that processes each chunk with fillna and column filtering"""
            for chunk in reader:
                chunk = chunk.fillna('')
                if columns is not None:
                    chunk_columns = _wildcard_expansion(chunk.columns, columns)
                    chunk = chunk[chunk_columns]
                yield chunk
        
        return process_chunks(result)
    
    # For regular (non-chunked) reads, process the DataFrame directly
    df = result.fillna('')
    
    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]
    
    return df


_schema['read'] = """
type: object
description: Import a JSON or JSONL file with explicit parameter validation
required:
  - name
properties:
  name:
    type: string
    description: The path to the JSON or JSONL file to import
  columns:
    type: array
    description: Subset of columns to select. Supports wildcard patterns.
    items:
      type: string
  orient:
    type: string
    description: |
      Format of the JSON string.
      - 'split': dict like {index -> [index], columns -> [columns], data -> [values]}
      - 'records': list like [{column -> value}, ... , {column -> value}]
      - 'index': dict like {index -> {column -> value}}
      - 'columns': dict like {column -> {index -> value}}
      - 'values': just the values array
      For JSONL files, only 'records' orientation is valid (and is set automatically)
    enum:
      - split
      - records
      - index
      - columns
      - values
  typ:
    type: string
    description: Type of object to recover (default is 'frame' for DataFrame)
    enum:
      - frame
      - series
  dtype:
    oneOf:
      - type: boolean
        description: If True, infer dtypes; if False, don't infer dtypes
      - type: object
        description: Dict specifying dtype for columns
  convert_dates:
    oneOf:
      - type: boolean
        description: If True, try parsing all datelike columns
      - type: array
        description: List of column names to parse as dates
        items:
          type: string
  keep_default_dates:
    type: boolean
    description: If parsing dates, parse the default datelike columns (default True)
  precise_float:
    type: boolean
    description: Use higher precision (strtod) for decoding floating point values (default False)
  date_unit:
    type: string
    description: Timestamp unit for conversion
    enum:
      - s
      - ms
      - us
      - ns
  encoding:
    type: string
    description: Encoding to use for UTF when reading. Default utf-8
  encoding_errors:
    type: string
    description: How to handle encoding errors (default 'strict')
    enum:
      - strict
      - ignore
      - replace
  lines:
    type: boolean
    description: |
      Read file as line-delimited JSON (JSONL format).
      Auto-detected: true for .jsonl files, false for .json files.
      When true, enables 'nrows' parameter.
  chunksize:
    type: integer
    description: |
      Return an iterator yielding DataFrames with this many records per chunk.
      When specified, the function returns an iterator instead of a single DataFrame.
      Each chunk will have fillna('') and column filtering applied.
    minimum: 1
  compression:
    type: string
    description: Compression type to use (default 'infer' from file extension)
    enum:
      - infer
      - gzip
      - bz2
      - zip
      - xz
  nrows:
    type: integer
    description: |
      Number of lines to read.
      IMPORTANT: Only valid for JSONL files (lines=True).
      For regular JSON files, this parameter will cause an error.
    minimum: 1
"""


def write(
    df: _pd.DataFrame,
    name: str,
    columns: _Union[str, list] = None,
    orient: str = None,
    date_format: str = None,
    double_precision: int = 10,
    force_ascii: bool = True,
    date_unit: str = 'ms',
    default_handler: callable = None,
    lines: bool = None,
    compression: str = 'infer',
    index: bool = None,
    indent: int = None,
    **kwargs
) -> None:
    """
    Export a DataFrame to a JSON or JSONL file with explicit parameter handling.
    
    >>> wrangles.connectors.json.write(df, 'output.json')
    >>> wrangles.connectors.json.write(df, 'output.jsonl')
    
    :param df: DataFrame to be written
    :param name: Path to the output JSON or JSONL file
    :param columns: (Optional) Subset of columns to write. If not provided, all columns will be written
    :param orient: Format of the JSON string. Valid values: 'split', 'records', 'index', 'columns', 'values', 'table'. Default 'records' for JSONL, varies for JSON
    :param date_format: Type of date conversion ('epoch' or 'iso'). Default 'epoch'
    :param double_precision: Number of decimal places for encoding floating point values. Default 10
    :param force_ascii: Force encoded string to be ASCII. Default True
    :param date_unit: Time unit to encode timestamps ('s', 'ms', 'us', 'ns'). Default 'ms'
    :param default_handler: Handler to call if object cannot be converted to JSON
    :param lines: Write as line-delimited JSON (JSONL format). Auto-detected based on extension
    :param compression: Compression to use. Options: 'infer', 'gzip', 'bz2', 'zip', 'xz', None
    :param index: Whether to include the index in the output. Default False for JSONL, True for JSON
    :param indent: Number of spaces for indentation. Not compatible with lines=True
    """
    _logging.info(f": Writing data to JSON file :: {name}")
    
    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]
    

    path_matched = _re.search(r'^.+(?=\/\w+\.\w+)', name)
    if path_matched:
        _os.makedirs(path_matched[0], exist_ok=True)
    
    if lines is None:
        if name.split('.')[-1] == 'jsonl' or '.'.join(name.split('.')[-2:]) == 'jsonl.gz':
            lines = True
        else:
            lines = False
    
    pandas_kwargs = {}
    
    if orient is not None:
        pandas_kwargs['orient'] = orient
    elif lines:
        pandas_kwargs['orient'] = 'records'
    else:
        pandas_kwargs['orient'] = 'records'
    
    if date_format is not None:
        pandas_kwargs['date_format'] = date_format
    
    if double_precision != 10:
        pandas_kwargs['double_precision'] = double_precision
    
    if not force_ascii:
        pandas_kwargs['force_ascii'] = force_ascii
    
    if date_unit != 'ms':
        pandas_kwargs['date_unit'] = date_unit
    
    if default_handler is not None:
        pandas_kwargs['default_handler'] = default_handler
    
    if lines:
        pandas_kwargs['lines'] = True
        if indent is not None:
            _logging.warning("Parameter 'indent' is ignored for JSONL files (lines=True)")
    else:
        if indent is not None:
            pandas_kwargs['indent'] = indent
    
    if compression != 'infer':
        pandas_kwargs['compression'] = compression
    
    if index is not None:
        pandas_kwargs['index'] = index
    elif lines:
        pandas_kwargs['index'] = False

    pandas_kwargs.update(kwargs)
    
    try:
        df.to_json(name, **pandas_kwargs)
    except TypeError as e:
        raise TypeError(
            f"Error writing JSON file: {e}\n"
            "This may be due to incompatible parameters. "
            "Note: 'indent' is not compatible with JSONL format (lines=True)."
        ) from e


_schema['write'] = """
type: object
description: Export data to a JSON or JSONL file with explicit parameter validation
required:
  - name
properties:
  name:
    type: string
    description: The path to the JSON or JSONL file to write
  columns:
    type: array
    description: List of columns to write. If omitted, all columns will be written. Supports wildcard patterns.
    items:
      type: string
  orient:
    type: string
    description: |
      Format of the JSON output.
      - 'split': dict like {index -> [index], columns -> [columns], data -> [values]}
      - 'records': list like [{column -> value}, ... , {column -> value}]
      - 'index': dict like {index -> {column -> value}}
      - 'columns': dict like {column -> {index -> value}}
      - 'values': just the values array
      - 'table': dict like {'schema': {schema}, 'data': {data}}
      For JSONL files, only 'records' orientation is valid (and is set automatically)
      Default: 'records' for both JSON and JSONL
    enum:
      - split
      - records
      - index
      - columns
      - values
      - table
  date_format:
    type: string
    description: Type of date conversion ('epoch' for timestamps or 'iso' for ISO8601)
    enum:
      - epoch
      - iso
  double_precision:
    type: integer
    description: Number of decimal places for encoding floating point values (default 10)
    minimum: 0
  force_ascii:
    type: boolean
    description: Force encoded string to be ASCII (default True)
  date_unit:
    type: string
    description: Time unit to encode timestamps (default 'ms')
    enum:
      - s
      - ms
      - us
      - ns
  lines:
    type: boolean
    description: |
      Write as line-delimited JSON (JSONL format).
      Auto-detected: true for .jsonl files, false for .json files.
      When true, 'indent' parameter is not allowed.
  compression:
    type: string
    description: Compression type to use (default 'infer' from file extension)
    enum:
      - infer
      - gzip
      - bz2
      - zip
      - xz
  index:
    type: boolean
    description: |
      Whether to include the index in the output.
      Default: False for JSONL files, follows pandas default for JSON files
  indent:
    type: integer
    description: |
      Number of spaces for indentation (for pretty-printing).
      Not compatible with JSONL format (lines=True).
    minimum: 0
"""