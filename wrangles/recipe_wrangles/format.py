"""Formatting recipe wrappers and compatible standardization names."""
import logging as _logging
import pandas as _pd
from .. import format as _format
from .standardize import (
    dates,
    pad,
    prefix,
    remove_duplicates,
    significant_figures,
    suffix,
    trim,
)


# Undocumented
def price_breaks(df: _pd.DataFrame, input: list, categoryLabel: str, valueLabel: str) -> _pd.DataFrame: # pragma: no cover
    """
    Rearrange price breaks
    """
    _logging.info(f": Processing price breaks :: input :: {input}")
    df = _pd.concat([df, _format.price_breaks(df[input], categoryLabel, valueLabel)], axis=1)
    return df
