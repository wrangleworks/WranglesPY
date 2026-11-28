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
from .standardize import case as _standardize_case
from .standardize import data_type as _standardize_data_type
from .standardize import fraction_to_decimal as _standardize_fraction_to_decimal
from .standardize import remove_words as _standardize_remove_words
from .standardize import round as _standardize_round
from .standardize import clean as _standardize_clean
from .standardize import custom as _standardize_custom
from .standardize import replace as _standardize_replace
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
standardize.case = _standardize_case
standardize.data_type = _standardize_data_type
standardize.fraction_to_decimal = _standardize_fraction_to_decimal
standardize.remove_words = _standardize_remove_words
standardize.round = _standardize_round
standardize.clean = _standardize_clean
standardize.custom = _standardize_custom
standardize.replace = _standardize_replace

lookup.key = _lookup_key
lookup.semantic = _lookup_semantic
