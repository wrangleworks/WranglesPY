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
from . import data
from . import extract
from .translate import translate
