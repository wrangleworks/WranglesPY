"""
Wrangles
~~~~~~~~~~~~~~~~~~~~~

Wrangle your data into shape with machine learning.

   >>> import wrangles
   >>> wrangles.authenticate('user', 'password')
   >>> wrangles.extract.codes('buried within a description ABC123ZZ')
   ['ABC123ZZ']
"""

from . import extract
from .config import authenticate 
from .translate import translate
