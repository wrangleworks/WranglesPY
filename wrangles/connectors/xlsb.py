"""
Connector to read & write Binary Excel (.xlsb) files

Binary Excel format provides smaller file sizes and faster performance
compared to standard .xlsx format.
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
    file_object=None,
    sheet_name=0,
    header=0,
    names=None,
    index_col=None,
    usecols=None,
    dtype=None,
    converters=None,
    true_values=None,
    false_values=None,
    skiprows=None,
    nrows=None,
    na_values=None,
    keep_default_na=True,
    na_filter=True,
    verbose=False,
    parse_dates=False,
    date_format=None,
    thousands=None,
    decimal=".",
    comment=None,
    skipfooter=0,
    **kwargs,
) -> _pd.DataFrame:
    """
    Import a Binary Excel (.xlsb) file.

    >>> df = wrangles.connectors.xlsb.read('myfile.xlsb')

    :param name: Name of the file to import
    :param columns: (Optional) Subset of the columns to be read
    :param file_object: (Optional) File object to read instead of from file system
    :param sheet_name: Name or index of sheet to read. Default 0 (first sheet)
    :param header: Row(s) to use as column names. Default 0
    :param names: List of column names to use
    :param index_col: Column(s) to use as row labels
    :param usecols: Columns to parse
    :param dtype: Data type for columns
    :param converters: Functions for converting values
    :param true_values: Values to consider as True
    :param false_values: Values to consider as False
    :param skiprows: Rows to skip at beginning
    :param nrows: Number of rows to read
    :param na_values: Additional strings to recognize as NA/NaN
    :param keep_default_na: Whether to keep default NA values
    :param na_filter: Detect missing value markers
    :param verbose: Print number of NA values replaced
    :param parse_dates: Parse date columns
    :param date_format: Format to use for parsing dates
    :param thousands: Thousands separator
    :param decimal: Decimal separator
    :param comment: Comment character
    :param skipfooter: Rows to skip at end
    :param kwargs: Additional arguments to pass to pandas
    :return: A Pandas dataframe of the imported data
    """
    _logging.info(f": Reading data from Binary Excel :: {name}")

    # Import pyxlsb only when needed
    try:
        import pyxlsb
    except ImportError:
        raise ImportError(
            "pyxlsb library is required. Install with: pip install pyxlsb"
        )

    # If user does not pass a file object then use name
    if file_object is None:
        file_object = name

    # Build pandas_kwargs dictionary explicitly
    pandas_kwargs = {}

    # Engine is fixed for XLSB
    pandas_kwargs["engine"] = "pyxlsb"

    # Handle key parameters
    if sheet_name != 0:
        pandas_kwargs["sheet_name"] = sheet_name

    if header != 0:
        pandas_kwargs["header"] = header

    if names is not None:
        pandas_kwargs["names"] = names

    if index_col is not None:
        pandas_kwargs["index_col"] = index_col

    if usecols is not None:
        pandas_kwargs["usecols"] = usecols

    # Default dtype to object if not specified
    if dtype is None:
        pandas_kwargs["dtype"] = "object"
    else:
        pandas_kwargs["dtype"] = dtype

    if converters is not None:
        pandas_kwargs["converters"] = converters

    if true_values is not None:
        pandas_kwargs["true_values"] = true_values

    if false_values is not None:
        pandas_kwargs["false_values"] = false_values

    if skiprows is not None:
        pandas_kwargs["skiprows"] = skiprows

    if nrows is not None:
        pandas_kwargs["nrows"] = nrows

    if na_values is not None:
        pandas_kwargs["na_values"] = na_values

    if keep_default_na != True:
        pandas_kwargs["keep_default_na"] = keep_default_na

    if na_filter != True:
        pandas_kwargs["na_filter"] = na_filter

    if verbose:
        pandas_kwargs["verbose"] = verbose

    if parse_dates:
        pandas_kwargs["parse_dates"] = parse_dates

    if date_format is not None:
        pandas_kwargs["date_format"] = date_format

    if thousands is not None:
        pandas_kwargs["thousands"] = thousands

    if decimal != ".":
        pandas_kwargs["decimal"] = decimal

    if comment is not None:
        pandas_kwargs["comment"] = comment

    if skipfooter != 0:
        pandas_kwargs["skipfooter"] = skipfooter

    # Add any additional kwargs
    pandas_kwargs.update(kwargs)

    # Read the xlsb file with explicit parameters
    df = _pd.read_excel(file_object, **pandas_kwargs).fillna("")

    # If the user specifies only certain columns, only include those
    if columns is not None:
        columns = _wildcard_expansion(df.columns, columns)
        df = df[columns]

    return df


_schema[
    "read"
] = """  
type: object  
description: Import data from a Binary Excel (.xlsb) file  
required:  
  - name  
properties:  
  name:  
    type: string  
    description: Name of the file to import  
  columns:  
    type: array  
    description: Subset of the columns to be read  
  nrows:  
    type: integer  
    description: Number of rows to read  
    minimum: 1  
  sheet_name:  
    type:  
      - string  
      - integer  
      - array  
    description: Name or index of sheet to read. Default 0 (first sheet)  
  header:  
    type:  
      - integer  
      - array  
    description: Row(s) to use as column names. Default 0  
  names:  
    type: array  
    description: List of column names to use  
  index_col:  
    type:  
      - integer  
      - string  
      - array  
    description: Column(s) to use as row labels  
  usecols:  
    type:  
      - array  
      - string  
      - callable  
    description: Columns to parse  
  dtype:  
    type: object  
    description: Data type for columns  
  skiprows:  
    type:  
      - integer  
      - array  
      - callable  
    description: Rows to skip at beginning  
  na_values:  
    type: array  
    description: Additional strings to recognize as NA/NaN  
  keep_default_na:  
    type: boolean  
    description: Whether to keep default NA values  
    default: true  
  na_filter:  
    type: boolean  
    description: Detect missing value markers  
    default: true  
  verbose:  
    type: boolean  
    description: Print number of NA values replaced  
  parse_dates:  
    type:  
      - boolean  
      - array  
      - object  
    description: Parse date columns  
  date_format:  
    type: string  
    description: Format to use for parsing dates  
  thousands:  
    type: string  
    description: Thousands separator  
  decimal:  
    type: string  
    description: Decimal separator  
    default: '.'  
  comment:  
    type: string  
    description: Comment character  
  skipfooter:  
    type: integer  
    description: Rows to skip at end  
    minimum: 0  
"""
