"""
Manage mutable runtime recipe variables.
"""
import logging as _logging
from typing import Union as _Union
from .. import recipe as _recipe


_schema = {}


def run(
    variables: dict = None,
    inspect: _Union[str, list] = None,
    max_items: int = 20
):
    """
    type: object
    description: Manage mutable runtime variables during recipe execution.
    properties:
      set:
        type: object
        description: Set one or more runtime variables atomically.
      update:
        type: object
        description: Deep-merge dictionary patches into existing runtime variables.
      mark_secret:
        type:
          - string
          - array
        description: Mark runtime variable names as sensitive for redaction.
      inspect:
        type:
          - string
          - array
        description: Variable name(s) or dotted paths to log in redacted form.
      max_items:
        type: integer
        minimum: 1
        description: Maximum list/dictionary entries to include during inspection.
    """
    if variables is None:
        variables = {}

    if inspect:
        snapshot = _recipe.inspect_runtime_variables(
            variables=variables,
            include=inspect,
            max_items=max_items
        )
        if snapshot:
            _logging.info(f": Runtime Variables :: {snapshot}")
        return snapshot

    return None


_schema['run'] = run.__doc__
