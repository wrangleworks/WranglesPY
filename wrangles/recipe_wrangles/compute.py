import pandas as _pd

_UNSET = object()


def case_when(
    df: _pd.DataFrame,
    output: str,
    cases: list,
    default=_UNSET
):
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
        description: >
          Value to assign where no conditions are met. If omitted, existing
          column values are preserved (or NaN for new columns).

    """

    df_temp = df.copy()
    df_temp.columns = df_temp.columns.str.replace(
        r'[^a-zA-Z0-9_]', '_', regex=True)

    caselist = [
        (df_temp.eval(case['condition'], engine='python'), case['value'])
        for case in cases
    ]

    # Determine the base series — what unmatched rows will hold
    if default is not _UNSET:
        base = _pd.Series(default, index=df.index, dtype=object)
    elif output in df.columns:
        base = df[output].copy().astype(object)
    else:
        base = _pd.Series(_pd.NA, index=df.index, dtype=object)

    df[output] = base.case_when(caselist)

    return df
