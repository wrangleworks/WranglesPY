"""
Wrangles
~~~~~~~~~~~~~~~~~~~~~

Wrangle your data into shape with machine learning.

   >>> import wrangles
   >>> wrangles.authenticate('user', 'password')
   >>> wrangles.extract.codes('buried within a description ABC123ZZ')
   ['ABC123ZZ']
"""

from .config import authenticate
from .classify import classify
from . import data
from . import extract
from .train import train
from .translate import translate
from .standardize import standardize