"""Dataframe wrappers for standardization wrangles."""

import builtins as _builtins
import logging as _logging
import re as _re
from typing import Union as _Union
from fractions import Fraction as _Fraction

from numpy import nan as _nan

import pandas as _pd
import wrangles as _wrangles

from ..standardize import clean as _clean
from .. import extract as _extract


# Pre-compiled regex for sentence case: matches the first non-whitespace character
# at the start of the string or immediately after punctuation (. ! ?) + optional
# whitespace. Using (\S) rather than ([a-zA-Z]) preserves the original char-by-char
# behaviour where a digit after punctuation "consumes" the capitalize flag
# (e.g. "13.5mm" stays lowercase because the `5` consumes the flag before `m` is
# reached), while \s* preserves handling of newlines and other Unicode whitespace.
_SENTENCE_CASE_RE = _re.compile(r'(^\s*|[.!?]\s*)(\S)')


def _is_missing(value) -> bool:
    """Return whether a scalar value should be skipped during concatenation."""
    try:
        result = _pd.isna(value)
    except (TypeError, ValueError):
        return False

    # pandas returns an array for list-like cells; those are values, not a
    # scalar missing marker.
    if hasattr(result, '__len__'):
        return False
    return bool(result)


def _concatenate_row(values, separator: str) -> str:
    """Join non-missing row values as text."""
    return separator.join(
        str(value)
        for value in values
        if (
            not _is_missing(value)
            and (not isinstance(value, str) or value != '')
        )
    )


def case(df: _pd.DataFrame, input: _Union[str, int, list], output: _Union[str, list] = None, case: str = 'lower') -> _pd.DataFrame:
    """
    type: object
    description: Change the case of the input.
    additionalProperties: false
    required:
      - input
      - case
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      case:
        type: string
        description: The case to convert to. lower, upper, title or sentence
        enum:
          - lower
          - upper
          - title
          - sentence
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Get the requested case, default lower
    desired_case = case.lower()

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Return early for empty dataframe
    if df.empty:
        df[output] = None
        return df

    warnings = {
        "invalid_data": {
            "logged": False,
            "message": 'Found invalid values when using convert.case. Non-string values will be skipped.'
        }
    }

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        if desired_case != 'sentence':
            source = df[input_column]
            # .str accessor raises AttributeError on non-object/non-string dtypes (e.g. int64).
            # For those columns, preserve originals and warn once — matching prior behaviour.
            if _pd.api.types.is_string_dtype(source.dtype) or _pd.api.types.is_object_dtype(source.dtype):
                # Use vectorized pandas str methods (C-level, much faster than row-wise apply).
                # Non-string values (lists, ints, etc.) become NaN after str operations;
                # detect those and restore the originals so behaviour is unchanged.
                transformed = getattr(source.str, desired_case)()
                non_string_mask = source.notna() & transformed.isna()
                if non_string_mask.any():
                    if not warnings["invalid_data"]["logged"]:
                        _logging.warning(warnings['invalid_data']['message'])
                        warnings["invalid_data"]['logged'] = True
                    transformed = transformed.where(~non_string_mask, source)
                df[output_column] = transformed
            else:
                if not warnings["invalid_data"]["logged"]:
                    _logging.warning(warnings['invalid_data']['message'])
                    warnings["invalid_data"]['logged'] = True
                df[output_column] = source

        else:
            # Sentence case: lowercase everything with the vectorized str method, then
            # use a pre-compiled regex to re-capitalise sentence starts.  This avoids
            # the slow character-by-character Python loop of the previous implementation.
            def _getSentenceCase(source, warnings=warnings):
                if isinstance(source, str):
                    return _SENTENCE_CASE_RE.sub(
                        lambda m: m.group(1) + m.group(2).upper(),
                        source.lower()
                    )
                else:
                    if not warnings["invalid_data"]["logged"]:
                        _logging.warning(warnings['invalid_data']['message'])
                        warnings["invalid_data"]['logged'] = True
                    return source

            df[output_column] = df[input_column].apply(_getSentenceCase)

    return df


def data_type(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list] = None,
    data_type: str = 'str',
    default: any = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Change the data type of the input.
    additionalProperties: false
    required:
      - input
      - data_type
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      data_type:
        type: string
        description: The new data type
        enum:
          - str
          - float
          - int
          - bool
          - datetime
      default:
        type:
          - string
          - number
          - array
          - boolean
          - datetime
        description: |-
          Set the default value to return if the input data
          cannot be converted to the specified data_type.
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # If the datatype is datetime
    if data_type == 'datetime':
        for input_column, output_column in zip(input, output):
            recursion_stop = kwargs.pop('stop', False)
            temp = _pd.to_datetime(df[input_column], errors="coerce", **kwargs)
            # Recipe to handle defaults, does not run when converting the default value
            if not recursion_stop:
                df['tempadfsgadg'] = temp
                df = _wrangles.recipe.run(
                    recipe = """
                        wrangles:
                        - replace:
                            input: tempadfsgadg
                            find: NaT
                            replace: ''
                            where: tempadfsgadg IS NULL

                        - create.column:
                            output: defaultzdbdfzmngz
                            value: ${default}

                        - convert.data_type:
                            input: defaultzdbdfzmngz
                            data_type: datetime
                            stop: true
                            if: ${default} is not None

                        - merge.coalesce:
                            input:
                            - tempadfsgadg
                            - defaultzdbdfzmngz
                            - ${input_col}
                            output: ${output_col}

                        - drop:
                            columns:
                            - defaultzdbdfzmngz
                            - tempadfsgadg
                        """,
                    dataframe = df,
                    variables = {
                        'input_col': input_column,
                        'output_col': output_column,
                        'default': default
                        }
                    )

            else:
                df[input_column] = temp

    else:
        dtype_dict = {
            'int': int,
            'float': float,
            'str': str,
            'bool': bool
            }

        # Raise an error if the datatype is not supported
        if data_type not in dtype_dict:
            raise TypeError(f"data_type {data_type} is not supported. Supported types are: {list(dtype_dict.keys()) + ['datetime']}")
        else:
            data_type = dtype_dict.get(data_type)

        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):

            # Function that converts data using dtype() and logs a warning only once when the conversion fails
            def _safe_convert(x, dtype, default, row):
                try:
                    return dtype(x)
                except Exception as e:
                    if not getattr(_safe_convert, "_warning_logged", False):
                        _logging.warning(
                            f"Found invalid values at row {row} when converting to {data_type} using convert.datatype."
                            )
                        _safe_convert._warning_logged = True  # mark as logged

                    # Return default if provided, otherwise return original value
                    if default is not None:
                        return default
                    else:
                        return x

            df[output_column] = df.apply(lambda row: _safe_convert(row[input_column], data_type, default, row.name), axis=1)

    return df


def fraction_to_decimal(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    decimals: int = 4,
    output: _Union[str, list] = None
) -> _pd.DataFrame:
    """
    type: object
    description: Convert fractions to decimals
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output colum
      decimals:
        type:
          - number
        description: Number of decimals to round fraction
    """
    # Set the output column as input if not provided
    if output is None: output = input

    # Ensure input and outputs are lists
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    for in_col, out_col in zip(input, output):
        results = []
        for item in df[in_col].astype(str):
            fractions = fractions = _re.finditer(r'\b(\d+[\s-])?\d+/\d+\b', item)
            replacement_list = []
            for match in fractions:
                fraction_str = match.group()

                # Get only the fraction part with or without whole number
                fraction = _Fraction(_re.findall(r'\d+\/\d+', fraction_str)[0])
                decimal = _builtins.round(float(fraction), decimals)

                # try to see if there is a whole number
                if _re.findall(r'(\d+[\s-])', fraction_str):
                    # remove the "-" from the whole number
                    whole_number = _re.findall(r'(\d+[\s-])', fraction_str)[0].strip()
                    whole_number = _re.sub(r'-', "", whole_number)
                    whole_number = int(whole_number)
                    decimal = whole_number + decimal

                replacement_list.append((fraction_str, str(decimal)))
            for fraction, dec in replacement_list:
                item = item.replace(fraction, dec)


            results.append(item)

        df[out_col] = results

    return df


def remove_words(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    to_remove: str,
    output: _Union[str, list] = None,
    tokenize_to_remove: bool = False,
    ignore_case: bool = True
    ) -> _pd.DataFrame:
    """
    type: object
    description: Remove all the elements that occur in one list from another.
    additionalProperties: false
    required:
      - input
      - to_remove
      - output
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of column to remove words from
      to_remove:
        type: array
        description: Column or list of columns with a list of words to be removed
      output:
        type:
          - string
          - array
        description: Name of the output columns
      tokenize_to_remove:
        type: boolean
        description: Tokenize all to_remove inputs
      ignore_case:
        type: boolean
        description: Ignore input and to_remove case
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Early return for empty df
    if df.empty:
        df[output] = None
        return df

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.remove_words(df[input_column].values.tolist(), df[to_remove].values.tolist(), tokenize_to_remove, ignore_case)

    return df


def round(df: _pd.DataFrame, input: _Union[str, int, list], decimals: int = 0, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Round column(s) to the specified decimals
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name of the input column(s)
      output:
        type:
          - string
          - array
        description: Name of the output column(s)
      decimals:
        type: number
        description: Number of decimal places to round column
    """
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    _logging.debug(f": Rounding columns :: input :: {input}, decimals :: {decimals}")
    for input_column, output_column in zip(input, output):
        # coerce input column to floats (nan on error)
        # replace nan with empty string
        df[output_column] = _pd.to_numeric(df[input_column], errors='coerce').round(decimals=decimals).map(float).replace(_nan, '')

    return df


def clean(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, int, list] = None,
    fix_encoding: bool = True,
    unescape_html: _Union[str, bool] = 'auto',
    normalization: str = 'NFC',
    fix_character_width: bool = True,
    uncurl_quotes: bool = True,
    remove_control_chars: bool = True,
    collapse_whitespace: bool = True,
    preserve_line_breaks: bool = False,
    trim: bool = True,
    separator: str = ' ',
    unescape_unicode: bool = False,
    latex_to_text: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Repair common encoding, Unicode, HTML character reference, control character, and whitespace problems locally.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - integer
          - array
        description: Name or list of output columns. Defaults to overwriting input.
      fix_encoding:
        type: boolean
        default: true
        description: Repair mojibake and other reversible encoding errors.
      unescape_html:
        anyOf:
          - type: boolean
          - type: string
            enum:
              - auto
        default: auto
        description: Decode HTML character references. Auto avoids decoding text that appears to contain HTML markup.
      normalization:
        type:
          - string
          - "null"
        enum:
          - NFC
          - NFKC
          - NFD
          - NFKD
          - null
        default: NFC
        description: Unicode normalization form.
      fix_character_width:
        type: boolean
        default: true
        description: Normalize fullwidth and halfwidth characters.
      uncurl_quotes:
        type: boolean
        default: true
        description: Replace typographic quotes with straight quotes.
      remove_control_chars:
        type: boolean
        default: true
        description: Remove C0 and C1 control characters.
      collapse_whitespace:
        type: boolean
        default: true
        description: Collapse runs of Unicode whitespace.
      preserve_line_breaks:
        type: boolean
        default: false
        description: Preserve line breaks while collapsing other whitespace.
      trim:
        type: boolean
        default: true
        description: Remove leading and trailing whitespace.
      unescape_unicode:
        type: boolean
        default: false
        description: Decode literal printable Unicode escapes in prose, preserving code and Markdown link destinations.
      latex_to_text:
        type: boolean
        default: false
        description: Convert supported inline LaTeX units, symbols and numeric fractions to readable text. Preserve numeric dollar amounts, ranges and explicit price qualifiers; remove extra dollar signs from other supported inline math. Preserve unsupported formulas. Set collapse_whitespace and trim to false to retain Markdown layout.
      separator:
        type: string
        default: " "
        description: Text used to join multiple input columns into one output.
    """
    if output is None:
        output = input

    if not isinstance(input, list):
        input = [input]
    if not isinstance(output, list):
        output = [output]

    if not isinstance(separator, str):
        raise TypeError('separator must be a string.')

    clean_options = {
        'fix_encoding': fix_encoding,
        'unescape_html': unescape_html,
        'normalization': normalization,
        'fix_character_width': fix_character_width,
        'uncurl_quotes': uncurl_quotes,
        'remove_control_chars': remove_control_chars,
        'collapse_whitespace': collapse_whitespace,
        'preserve_line_breaks': preserve_line_breaks,
        'trim': trim,
        'unescape_unicode': unescape_unicode,
        'latex_to_text': latex_to_text,
        **kwargs
    }

    if len(input) > 1 and len(output) == 1:
        combined = [
            _concatenate_row(values, separator)
            for values in df[input].itertuples(index=False, name=None)
        ]
        df[output[0]] = _clean(combined, **clean_options)
        return df

    if len(input) != len(output):
        raise ValueError(
            'standardize.clean must output to a single column or the same '
            'number of columns as input.'
        )

    warned_for_non_strings = False
    source_values = [df[input_column].tolist() for input_column in input]
    for values, output_column in zip(source_values, output):
        if not warned_for_non_strings and any(
            not isinstance(value, str)
            for value in values
        ):
            _logging.warning(
                ': standardize.clean preserved non-string values in mapped input columns.'
            )
            warned_for_non_strings = True

        df[output_column] = _clean(values, **clean_options)

    return df


def custom(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    model_id: _Union[str, list],
    output: _Union[str, list] = None,
    case_sensitive: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Standardize data using a DIY or bespoke standardization wrangle. Requires WrangleWorks Account and Subscription.
    required:
      - input
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      model_id:
        type:
          - string
          - array
        description: The ID of the wrangle to use (do not include 'find' and 'replace')
      case_sensitive:
        type: boolean
        description: Allows the wrangle to be case sensitive if set to True, default is False.
    """
    # Import lazily to avoid a package initialization cycle. Delegating keeps
    # the existing recipe implementation as the single compatibility path.
    from .main import standardize as _legacy_standardize

    return _legacy_standardize(
        df=df,
        input=input,
        model_id=model_id,
        output=output,
        case_sensitive=case_sensitive,
        **kwargs
    )


def replace(df: _pd.DataFrame, input: _Union[str, int, list], find: str, replace: str, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Quick find and replace for simple values. Can use regex if 'input' in params and isinstance(params['input'], list):in the find field.
    additionalProperties: false
    required:
      - input
      - find
      - replace
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: Name or list of input column
      output:
        type:
          - string
          - array
        description: Name or list of output column
      find:
        type: string
        description: Pattern to find using regex
      replace:
        type: string
        description: Value to replace the pattern found
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    def custom_replacement(x, find, replace, row):
        if isinstance(x, (dict, list, bool)):  # Check if the input is an object
            # Raise warning
            if not getattr(custom_replacement, "_warning_logged", False):
                _logging.warning(
                    f"Found invalid values at row {row} when using replace. Dict, list and bool values will be skipped."
                )
                custom_replacement._warning_logged = True  # mark as logged
            return x  # Return the object as-is without modification

        try:
            return _re.sub(str(find), str(replace), str(x))  # Apply the regex substitution
        except:
            return x

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df.apply(lambda row: custom_replacement(row[input_column], find, replace, row=row.name), axis=1)

    return df
