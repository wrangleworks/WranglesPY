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


class train():
    def delete(df, model_id: str, confirm: str = None):
        """
        type: object
        description: Delete a trained model.
        additionalProperties: false
        required:
          - model_id
          - confirm
        properties:
          model_id:
            type: string
            description: The ID of the model to delete.
          confirm:
            type: string
            description: Must be set to 'delete' to confirm this destructive action.
            enum:
              - delete
        """
        from ..train import train as _train

        _train.delete(model_id, confirm=confirm)
        return df
