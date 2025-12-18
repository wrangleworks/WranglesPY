import pandas as _pd
import numpy as _np
import re as _re


def case_when(df: _pd.DataFrame, output: str, cases: list, default=None):
    """
    type: object
    description: Assign values to a column based on conditional logic
    additionalProperties: false
    required:
      - output
      - cases
    properties:
      output:
        type: string
        description: Name of the output column
      cases:
        type: array
        description: List of conditions and corresponding values
        minItems: 1
        items:
          type: object
          required:
            - condition
            - value
          properties:
            condition:
              type: string
              description: Condition to evaluate (e.g., "Score > 0.84")
            value:
              type: [string, number, integer, boolean]
              description: Value to assign if condition is true
      default:
        type: [string, number, integer, boolean, "null"]
        description: Value to assign if no conditions are met. Default None.
    """

    df_temp = df.copy()
    df_temp.columns = df_temp.columns.str.replace(r"[^a-zA-Z0-9_]", "_", regex=True)

    # Evaluate conditions using the renamed columns
    conditions = [df_temp.eval(case["condition"]) for case in cases]
    choices = [case["value"] for case in cases]

    # Use numpy.select to evaluate conditions and assign values
    df[output] = _np.select(conditions, choices, default=default)

    return df
