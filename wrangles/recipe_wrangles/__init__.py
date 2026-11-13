"""
These are internal wrangles to be called as part of a recipe.

They are not expected to be called directly by a user.

Many call the respective wrangles, but deal with the interactions with the dataframe used by the recipe.

Functions in main are called directly, other functions are called by their module name.

e.g.

wrangles:
  - classify:

  - convert.case:

"""
from .standardize import clean as _standardize_clean
from .standardize import custom as _standardize_custom
from .standardize import replace as _standardize_replace
from .standardize import dates as _standardize_dates
from .standardize import pad as _standardize_pad
from .standardize import prefix as _standardize_prefix
from .standardize import remove_duplicates as _standardize_remove_duplicates
from .standardize import significant_figures as _standardize_significant_figures
from .standardize import suffix as _standardize_suffix
from .standardize import trim as _standardize_trim
from .lookup import key as _lookup_key
from .lookup import semantic as _lookup_semantic
from .main import *
from .pandas import *
from . import convert
from . import create
from . import extract
from . import ai
from . import format
from . import merge
from . import select
from . import split
from . import structure
from . import compare
from . import generate
from . import compute
from . import search


# The legacy recipe function stays callable while also exposing the new dotted
# standardize namespace to recipe resolution and schema discovery.
standardize.clean = _standardize_clean
standardize.custom = _standardize_custom
standardize.replace = _standardize_replace
standardize.dates = _standardize_dates
standardize.pad = _standardize_pad
standardize.prefix = _standardize_prefix
standardize.remove_duplicates = _standardize_remove_duplicates
standardize.significant_figures = _standardize_significant_figures
standardize.suffix = _standardize_suffix
standardize.trim = _standardize_trim

lookup.key = _lookup_key
lookup.semantic = _lookup_semantic
