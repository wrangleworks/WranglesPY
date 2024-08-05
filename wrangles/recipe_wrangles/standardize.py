"""
Functions to run standardize wrangles
"""
from typing import Union as _Union
import pandas as _pd
from .. import standardize as _standardize

def attributes(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list] = None,
    attribute_type: str = None,
    desiredUnit: str = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Standardize data by attribute type. Requires WrangleWorks Account and Subscription.
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      attribute_type:
        type: string
        description: The attribute type to be standardized. Default is all.
        enum:
          - angle
          - area
          - capacitance
          - charge
          - current
          - data transfer rate
          - electrical conductance
          - electrical resistance
          - energy
          - force
          - frequency
          - inductance
          - instance frequency
          - length
          - luminous flux
          - weight
          - power
          - pressure
          - speed
          - velocity
          - temperature
          - time
          - voltage
          - volume
          - volumetric flow 
      desired_unit:
        type: string
        description: Convert the extracted unit to the desired unit
    $ref: "#/$defs/misc/unit_entity_map"
    """
    # if output is not specified, overwrite the input
    if output is None: output = input

    # if input is a string, convert to a list for consistency
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    if len(output) == 1 and len(input) > 1:
        df[output[0]] = _standardize.attributes(
            df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist(),
            attribute_type,
            desiredUnit,
            **kwargs
        )
    else:
        # loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = _standardize.attributes(
                df[input_column].astype(str).tolist(),
                attribute_type,
                desiredUnit,
                **kwargs
            )
    
    return df


def custom(
    df: _pd.DataFrame,
    input: _Union[str, list],
    model_id: _Union[str, list],
    output: _Union[str, list] = None,
    case_sensitive: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Standardize data using a DIY or bespoke standardization wrangle. Requires WrangleWorks Account and Subscription.
    required:
      - input
    properties:
      input:
        type:
          - string
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      model_id:
        type:
          - string
          - array
        description: The ID of the wrangle to use (do not include 'find' and 'replace')
      case_sensitive:
        type: bool
        description: Allows the wrangle to be case sensitive if set to True, default is False.
    """
    # If user hasn't specified an output column, overwrite the input
    if output is None: output = input

    # If user provides a single string, convert all the arguments to lists for consistency
    if isinstance(input, str): input = [input]
    if isinstance(output, str): output = [output]
    if isinstance(model_id, str): model_id = [model_id]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # If Several model ids applied to a column in place
    if all(len(x) == 1 for x in [input, output]) and isinstance(model_id, list):
        tmp_output = input
        df_copy = df.loc[:, [input[0]]]
        for model in model_id:
            for input_column, output_column in zip(input, tmp_output):
                df_copy[output_column] = _standardize.custom(
                    df_copy[output_column].astype(str).tolist(),
                    model,
                    case_sensitive,
                    **kwargs
                )

        # Adding the result of the df_copy to the original dataframe
        df[output[0]] = df_copy[output_column]
        return df

    for model in model_id:
        for input_column, output_column in zip(input, output):
            df[output_column] = _standardize.custom(
                df[input_column].astype(str).tolist(),
                model,
                case_sensitive,
                **kwargs
            )

    return df