"""
Functions to run extraction wrangles
"""
import pandas as _pd
from typing import Union as _Union
from .. import extract as _extract
from .. import format as _format
import re as _re


def address(df: _pd.DataFrame, input: str, output: str, dataType: str) -> _pd.DataFrame:
    """
    type: object
    description: Extract parts of addresses. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the input column.
      output:
        type: string
        description: Name of the output column.
    """
    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _extract.address(df[input].astype(str).tolist(), dataType)
    
    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = _extract.address(df[in_col].astype(str).tolist(), dataType)
            
    # If the input and output are not the same type    
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')
            
    return df


def attributes(df: _pd.DataFrame, input: str, output: str, responseContent: str = 'span', attribute_type: str = None, desired_unit: str = None, bound: str = 'mid') -> _pd.DataFrame:
    """
    type: object
    description: Extract numeric attributes from the input such as weights or lengths. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the input column.
      output:
        type: string
        description: Name of the output column.
      attribute_type:
        type: string
        description: Request only a specific type of attribute
        enum:
          - angle
          - area
          - capacitance
          - charge
          - current
          - data transfer rate
          - electric potential
          - electrical conductance
          - electrical resistance
          - energy
          - force
          - frequency
          - inductance
          - instance frequency
          - length
          - mass
          - power
          - pressure
          - speed
          - temperature
          - time
          - volume
          - volumetric flow
      responseContent:
        type: string
        description: span - returns the text found. object - returns an object with the value and unit
        enum:
          - span
          - object
      bound:
        type: string
        description: When returning an object, if the input is a range (e.g. 10-20mm) set the value to return. min, mid or max. Default mid.
        enum:
          - min
          - mid
          - max
    """
    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _extract.attributes(df[input].astype(str).tolist(), responseContent, attribute_type, desired_unit, bound)
        
    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = _extract.attributes(df[in_col].astype(str).tolist(), responseContent, attribute_type, desired_unit, bound)
    
    # If the input and output are not the same type    
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')
        
    return df


def codes(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Extract alphanumeric codes from the input. Requires WrangleWorks Account.
    additionalProperties: false
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
    """
    if isinstance(input, str):
        df[output] = _extract.codes(df[input].astype(str).tolist())
    elif isinstance(input, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            if isinstance(output, str):
                df[output] = _extract.codes(_format.concatenate(df[input].astype(str).values.tolist(), ' aaaaaaa '))
            else:
                raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        else:
            for input_column, output_column in zip(input, output):
                df[output_column] = _extract.codes(df[input_column].astype(str).tolist())

    return df


def custom(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], model_id: str = None, find: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract data from the input using a DIY or bespoke extraction wrangle. Requires WrangleWorks Account and Subscription.
    additionalProperties: false
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
      model_id:
        type: string
        description: The ID of the wrangle to use (do not include find)
      find:
        type:
          - string
        description: Pattern to find using regex (do not include model_id)
    """
    if model_id is not None and find is None:
    
        if isinstance(input, str):
            df[output] = _extract.custom(df[input].astype(str).tolist(), model_id=model_id)
        elif isinstance(input, list):
            # If a list of inputs is provided, ensure the list of outputs is the same length
            if len(input) != len(output):
                if isinstance(output, str):
                    df[output] = _extract.custom(_format.concatenate(df[input].astype(str).values.tolist(), ' '), model_id=model_id)
                else:
                    raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
            else:
                for input_column, output_column in zip(input, output):
                    df[output_column] = _extract.custom(df[input_column].astype(str).tolist(), model_id=model_id)
    
    elif find is not None and model_id is None:
        
        def mini_extract(string):
            new_string = _re.findall(find, string)
            return new_string
        
        df[output] = df[input].apply(lambda x: mini_extract(x))
        
    else:
        raise ValueError('Extract custom must have model_id or find as parameters')
          
    return df


def html(df: _pd.DataFrame, input: _Union[str, list], data_type: str, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract elements from strings containing html. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
      - output
      - data_type
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
      data_type:
        type: string
        description: The type of data to extract
        enum:
          - text
          - links
    """
    if isinstance(input, str): input = [input]
    if output is None: output = input

    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.html(df[input_column].astype(str).tolist(), dataType=data_type)
            
    return df


def properties(df: _pd.DataFrame, input: str, output: str, property_type: str = None, return_data_type: str = 'list') -> _pd.DataFrame:
    """
    type: object
    description: Extract text properties from the input. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the input column
      output:
        type: string
        description: Name of the output columns
      property_type:
        type: string
        description: The specific type of properties to extract
      return_data_type:
        type: string
        description: The format to return the data, as a list or as a string
    """
    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _extract.properties(df[input].astype(str).tolist(), type=property_type, return_data_type=return_data_type)
    
    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = _extract.properties(df[in_col].astype(str).tolist(), type=property_type, return_data_type=return_data_type)
    
    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')
    
    return df
    
def brackets(df: _pd.DataFrame, input: str, output: str) -> _pd.DataFrame:
    """
    type: object
    description: Extract text properties in brackets from the input
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type: string
        description: Name of the input column
      output:
        type: string
        description: Name of the output columns
    """
    # If the input is a string
    if isinstance(input, str) and isinstance(output, str):
        df[output] = _extract.brackets(df[input].astype(str).tolist())

    # If the input is multiple columns (a list)
    elif isinstance(input, list) and isinstance(output, list):
        for in_col, out_col in zip(input, output):
            df[out_col] = _extract.brackets(df[in_col].astype(str).tolist())
    
    # If the input and output are not the same type
    elif type(input) != type(output):
        raise ValueError('If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided.')

    return df

def date_properties(df: _pd.DataFrame, input: _pd.Timestamp, property: str, output: str = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract date properties from a date (day, month, year, etc...)
    additionalProperties: false
    required:
      - input
      - property
    properties:
      input:
        type: string
        description: Name of the input column
      output:
        type: string
        description: Name of the output columns
      property:
        type: string
        description: Property to extract from date
        enum:
          - day
          - day_of_year
          - month
          - month_name
          - weekday
          - week_day_name
          - week_year
          - quarter
    """
    if output is None: output = input
    
    properties_object = {
        'day': df[input].dt.day,
        'day_of_year': df[input].dt.day_of_year,
        'month': df[input].dt.month,
        'month_name': df[input].dt.month_name(),
        'weekday': df[input].dt.weekday,
        'week_day_name': df[input].dt.day_name(),
        'week_year': df[input].dt.isocalendar()['week'],
        'quarter': df[input].dt.quarter,
    }
    
    if property in properties_object.keys():
        df[output] = properties_object[property]
    else:
        raise ValueError(f"\"{property}\" not a valid date property.")
    
    return df
    
def date_frequency(df: _pd.DataFrame, start_time: _pd.Timestamp, end_time: _pd.Timestamp, output: str, frequency: str = 'day') -> _pd.DataFrame:
    """
    type: object
    description: Extract date range frequency from two dates
    additionalProperties: false
    required:
      - start_time
      - end_time
    properties:
      start_time:
        type: string
        description: Name of the start date column
      end_time:
        type: string
        description: Name of the end date column
      output:
        type: string
        description: Name of the output column
      frequency:
        type: string
        description: Type of frequency to count
        enum:
          - business days
          - days
          - weeks
          - months
          - semi months
          - business month ends
          - month starts
          - semi month starts
          - business month starts
          - quarters
          - quarter starts
          - years
          - business hours
          - hours
          - minutes
          - seconds
          - milliseconds
    """
    frequency_object = {
        'business days': 'B',
        'days': 'D',
        'weeks': 'W',
        'months':'M',
        'semi months': 'SM',
        'business month ends': 'BM',
        'month starts': 'MS',
        'semi month starts': 'SMS',
        'business month starts': 'BMS',
        'quarters': 'Q',
        'quarter starts': 'QS',
        'years': 'Y',
        'business hours': 'BH',
        'hours': 'H',
        'minutes': 'T',
        'seconds': 'S',
        'milliseconds': 'L',
    }
    
    # Checking if frequency is invalid
    if frequency not in frequency_object.keys():
        raise ValueError(f"\"{frequency}\" not a valid frequency")
        
    # Removing timezone information from columns before operation
    start_data = df[start_time].dt.tz_localize(None).copy()
    end_data = df[end_time].dt.tz_localize(None).copy()
    
    results = []
    for start, end in zip(start_data, end_data):
        results.append(len(_pd.date_range(start, end, freq=frequency_object[frequency])[1:]))
    
    df[output] = results
    
    return df
