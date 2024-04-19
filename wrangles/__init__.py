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

from . import connectors
from . import recipe

from .classify import classify
from . import extract
from .lookup import lookup
from .translate import translate
from .standardize import standardize
from . import format
from . import openai

from . import data
from .train import train
from . import select




