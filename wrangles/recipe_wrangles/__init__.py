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
from .main import *
from .pandas import *
from . import convert
from . import create
from . import extract
from . import format
from . import merge
from . import select
from . import split
from . import compare
from . import generate
from . import compute
from . import search


# The legacy recipe function stays callable while also exposing the new dotted
# standardize namespace to recipe resolution and schema discovery.
standardize.clean = _standardize_clean
standardize.custom = _standardize_custom
