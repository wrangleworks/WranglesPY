"""  
Connector to read & write Binary Excel (.xlsb) files  
  
Binary Excel format provides smaller file sizes and faster performance  
compared to standard .xlsx format.  
"""  
  
import logging as _logging  
import os as _os   
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
    chunk_size: int = None,  
    max_memory_mb: int = 1000,  
    **kwargs,  
) -> _pd.DataFrame:  
    """  
    Import a Binary Excel (.xlsb) file.  
  
    >>> df = wrangles.connectors.xlsb.read('myfile.xlsb')  
  
    :param name: Name of the file to import  
    :param columns: (Optional) Subset of the columns to be read  
    :param file_object: (Optional) File object to read instead of from file system  
    :param sheet_name: Name or index of sheet to read. Default 0 (first sheet).  
                      If None, reads all sheets and concatenates them.  
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
    :param chunk_size: (Optional) Number of rows to read at a time for large files  
    :param max_memory_mb: (Optional) Maximum memory usage in MB before switching to chunked mode  
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
  
    # File existence validation  
    if file_object is None:  
        # Check if file exists  
        if not _os.path.exists(name):  
            raise FileNotFoundError(f"File not found: {name}")  
          
        # Check if it's actually a file (not a directory)  
        if not _os.path.isfile(name):  
            raise ValueError(f"Path is not a file: {name}")  
          
        # Check file extension  
        if not str(name).lower().endswith('.xlsb'):  
            raise ValueError(f"File must have .xlsb extension: {name}")  
          
        # Check file size and warn if large  
        file_size_mb = _os.path.getsize(name) / (1024 * 1024)  
        if file_size_mb > max_memory_mb and chunk_size is None:  
            _logging.warning(  
                f"Large file detected ({file_size_mb:.1f}MB). "  
                f"Consider using chunk_size parameter to avoid memory errors."  
            )  
            # Auto-enable chunked mode for very large files  
            chunk_size = min(10000, max(1000, int(max_memory_mb * 100 / file_size_mb)))  
          
        file_object = name  
  
    # Early column validation if columns specified  
    if columns is not None and file_object == name:  
        try:  
            # Read just the header to get column names  
            header_df = _pd.read_excel(  
                file_object,  
                engine='pyxlsb',  
                sheet_name=sheet_name if sheet_name not in [0, None] else 0,  
                header=header,  
                nrows=0,  # Only read header  
                **{k: v for k, v in kwargs.items() if k in ['dtype']}  
            )  
              
            # Validate columns exist before reading full data  
            try:  
                _wildcard_expansion(header_df.columns, columns)  
            except KeyError as e:  
                # Provide context about available columns  
                available_cols = list(header_df.columns)  
                raise KeyError(  
                    f"Column validation failed for file {name}. "  
                    f"{str(e)}. Available columns: {available_cols}"  
                ) from e  
                  
        except Exception as e:  
            # If we can't read just the header, fall back to validation after full read  
            _logging.warning(f"Could not validate columns early: {e}. Will validate after reading.")  
  
    # Sheet existence validation (only for file paths, not file objects)  
    if file_object == name and sheet_name not in [0, None]:  
        try:  
            with pyxlsb.open_workbook(name) as wb:  
                sheet_names = [sheet.name for sheet in wb.sheets]  
                  
                # Check if sheet_name is a string (sheet name)  
                if isinstance(sheet_name, str):  
                    if sheet_name not in sheet_names:  
                        raise ValueError(f"Sheet '{sheet_name}' not found in workbook. Available sheets: {sheet_names}")  
                  
                # Check if sheet_name is an integer (sheet index)  
                elif isinstance(sheet_name, int):  
                    if sheet_name < 0 or sheet_name >= len(sheet_names):  
                        raise ValueError(f"Sheet index {sheet_name} out of range. Workbook has {len(sheet_names)} sheets (0-{len(sheet_names)-1}). Available sheets: {sheet_names}")  
                  
                # Check if sheet_name is a list  
                elif isinstance(sheet_name, list):  
                    for s in sheet_name:  
                        if isinstance(s, str) and s not in sheet_names:  
                            raise ValueError(f"Sheet '{s}' not found in workbook. Available sheets: {sheet_names}")  
                        elif isinstance(s, int) and (s < 0 or s >= len(sheet_names)):  
                            raise ValueError(f"Sheet index {s} out of range. Workbook has {len(sheet_names)} sheets (0-{len(sheet_names)-1}). Available sheets: {sheet_names}")  
        except Exception as e:  
            if "not found" in str(e) or "out of range" in str(e):  
                raise e  
            # If there's an error opening the workbook, we'll let pandas handle it  
  
    # Handle chunked reading for large files  
    if chunk_size is not None:  
        return _read_chunked(file_object, {  
            "engine": "pyxlsb",  
            "sheet_name": sheet_name if sheet_name not in [0, None] else 0,  
            "header": header,  
            "names": names,  
            "index_col": index_col,  
            "usecols": usecols,  
            "dtype": dtype if dtype is not None else "object",  
            "converters": converters,  
            "true_values": true_values,  
            "false_values": false_values,  
            "skiprows": skiprows,  
            "na_values": na_values,  
            "keep_default_na": keep_default_na,  
            "na_filter": na_filter,  
            "verbose": verbose,  
            "parse_dates": parse_dates,  
            "date_format": date_format,  
            "thousands": thousands,  
            "decimal": decimal,  
            "comment": comment,  
            **kwargs  
        }, chunk_size, columns)  
  
    # Build pandas_kwargs dictionary explicitly  
    pandas_kwargs = {}  
  
    # Engine is fixed for XLSB  
    pandas_kwargs["engine"] = "pyxlsb"  
  
    # Handle key parameters  
    if sheet_name not in [0, None]:  
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
  
    # Fixed boolean parameter checks  
    if not keep_default_na:  
        pandas_kwargs["keep_default_na"] = keep_default_na  
  
    if not na_filter:  
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
  
    try:  
        # Read the xlsb file with explicit parameters  
        result = _pd.read_excel(file_object, **pandas_kwargs)  
          
        # Handle case where sheet_name=None returns a dict  
        if isinstance(result, dict):  
            # Add a column to track the source sheet  
            dfs = []  
            for sheet_name_key, df in result.items():  
                df = df.fillna("")  
                # Add sheet name as a column if not already present  
                if '_sheet_name' not in df.columns:  
                    df = df.copy()  
                    df['_sheet_name'] = sheet_name_key  
                dfs.append(df)  
              
            # Concatenate all sheets  
            if dfs:  
                df = _pd.concat(dfs, ignore_index=True)  
            else:  
                df = _pd.DataFrame()  
        else:  
            # Single sheet case  
            df = result.fillna("")  
              
    except MemoryError as e:  
        raise MemoryError(  
            f"Memory error while reading {name}. "  
            f"Try using chunk_size parameter to read the file in smaller chunks. "  
            f"Example: chunk_size=10000"  
        ) from e  
    except Exception as e:  
        if "not a valid zip file" in str(e).lower():  
            raise ValueError(f"File is not a valid .xlsb file or is corrupted: {name}")  
        elif "sheet" in str(e).lower():  
            raise ValueError(f"Invalid sheet name or index: {sheet_name}")  
        else:  
            raise e  
  
    # If the user specifies only certain columns, only include those  
    # (This is now a fallback if early validation wasn't possible)  
    if columns is not None:  
        try:  
            columns = _wildcard_expansion(df.columns, columns)  
            df = df[columns]  
        except KeyError as e:  
            # Provide context about available columns  
            available_cols = list(df.columns)  
            raise KeyError(  
                f"Column selection failed for file {name}. "  
                f"{str(e)}. Available columns: {available_cols}"  
            ) from e  
  
    return df  
  
  
def _read_chunked(  
    file_object,  
    pandas_kwargs: dict,  
    chunk_size: int,  
    columns: _Union[str, list] = None  
) -> _pd.DataFrame:  
    """  
    Read xlsb file in chunks to handle large files  
      
    :param file_object: File path or object to read  
    :param pandas_kwargs: Arguments to pass to pandas  
    :param chunk_size: Number of rows per chunk  
    :param columns: Columns to select after reading  
    :return: Concatenated DataFrame  
    """  
    _logging.info(f": Reading large file in chunks of {chunk_size} rows")  
      
    chunks = []  
    skip_rows = 0  
      
    # Store original skiprows if present  
    original_skiprows = pandas_kwargs.get('skiprows', 0)  
      
    while True:  
        try:  
            # Update skiprows for this chunk  
            chunk_kwargs = pandas_kwargs.copy()  
            chunk_kwargs['skiprows'] = skip_rows + original_skiprows  
            chunk_kwargs['nrows'] = chunk_size  
              
            # Read chunk  
            chunk_df = _pd.read_excel(file_object, **chunk_kwargs)  
              
            # Handle dict return for sheet_name=None  
            if isinstance(chunk_df, dict):  
                dfs = []  
                for sheet_name_key, df in chunk_df.items():  
                    df = df.fillna("")  
                    if '_sheet_name' not in df.columns:  
                        df = df.copy()  
                        df['_sheet_name'] = sheet_name_key  
                    dfs.append(df)  
                chunk_df = _pd.concat(dfs, ignore_index=True) if dfs else _pd.DataFrame()  
            else:  
                chunk_df = chunk_df.fillna("")  
              
            # If chunk is empty, we're done  
            if len(chunk_df) == 0:  
                break  
                  
            chunks.append(chunk_df)  
            skip_rows += chunk_size  
              
            _logging.info(f": Read chunk {len(chunks)}: {len(chunk_df)} rows")  
              
        except Exception as e:  
            if "Empty DataFrame" in str(e) or len(chunks) == 0:  
                break  
            else:  
                raise e  
      
    if not chunks:  
        return _pd.DataFrame()  
      
    # Concatenate all chunks  
    result = _pd.concat(chunks, ignore_index=True)  
      
    # Apply column selection if specified  
    if columns is not None:  
        columns = _wildcard_expansion(result.columns, columns)  
        result = result[columns]  
      
    _logging.info(f": Completed reading {len(result)} total rows from {len(chunks)} chunks")  
    return result  
  
  
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
