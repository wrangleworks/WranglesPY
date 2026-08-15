"""Dataframe wrappers for standardization wrangles."""

import logging as _logging
from typing import Union as _Union

import pandas as _pd

from ..standardize import clean as _clean


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
    for input_column, output_column in zip(input, output):
        values = df[input_column].tolist()
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
