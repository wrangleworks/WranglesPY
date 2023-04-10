"""
Functions to run extraction wrangles
"""
from typing import Union as _Union
import re as _re
from collections import OrderedDict as _OrderedDict
import pandas as _pd
from .. import extract as _extract
from .. import format as _format


def address(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], dataType: str) -> _pd.DataFrame:
    """
    type: object
    description: Extract parts of addresses. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
      - output
      - dataType
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
        description: Name of the output column.
      dataType:
        type: string
        description: Specific part of the address to extract
        enum:
          - streets
          - cities
          - regions
          - countries
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
  
    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.address(df[input_column].astype(str).tolist(), dataType)
  
    return df


def attributes(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], responseContent: str = 'span', attribute_type: str = None, desired_unit: str = None, bound: str = 'mid') -> _pd.DataFrame:
    """
    type: object
    description: Extract numeric attributes from the input such as weights or lengths. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column.
      output:
        type:
          - string
          - array
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
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.attributes(
            df[input_column].astype(str).tolist(),
            responseContent,
            attribute_type,
            desired_unit,
            bound
        )
        
    return df


def brackets(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list]) -> _pd.DataFrame:
    """
    type: object
    description: Extract text properties in brackets from the input
    additionalProperties: false
    required:
      - input
      - output
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output columns
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.brackets(df[input_column].astype(str).tolist())

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
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    if len(output) == 1 and len(input) > 1:
        df[output[0]] = _extract.codes(df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist())
    else:
        # Ensure input and output are equal lengths
        if len(input) != len(output) and len(output) > 1:
            raise ValueError('The lists for input and output must be the same length.')

        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.codes(df[input_column].astype(str).tolist())

    return df


def custom(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list], model_id: _Union[str, list], use_labels: bool = False) -> _pd.DataFrame:
    """
    type: object
    description: Extract data from the input using a DIY or bespoke extraction wrangle. Requires WrangleWorks Account and Subscription.
    additionalProperties: true
    required:
      - input
      - output
      - model_id
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
        description: The ID of the wrangle to use
      use_labels:
        type: bool
        description: Allows the use of key values pairs to output a dictionary
    """
    if not output:
        output = input

    if not isinstance(output, list):
        output = [output]

    if not isinstance(model_id, list):
        # If a list of inputs is provided, ensure the list of outputs is the same length
        if len(input) != len(output):
            if len(output) == 1:
                df[output[0]] = _extract.custom(_format.concatenate(df[input].astype(str).values.tolist(), ' '), model_id=model_id)
            else:
                raise ValueError('If providing a list of inputs, a corresponding list of outputs must also be provided.')
        else:
            for input_column, output_column in zip(input, output):
                df[output_column] = _extract.custom(df[input_column].astype(str).tolist(), model_id=model_id)
                
    # Multiple different custom wrangles at the same time
    else:
        for in_col, out_col, mod_id in zip(input, output, model_id):
            df[out_col] = _extract.custom(df[in_col].astype(str).tolist(),model_id=mod_id)
    
    if use_labels:
        if len(output) > 1:
            raise ValueError("'use_labels' can only be used with a single output")
        
        output = output[0]

        # Run the custom dictionary maker after normal operation from extract
        # This will be triggered only if a parameter is set
        result = []
        for out_row in df[output]:
        
            dict_output = {'Unlabeled': []}
            # Iterating over the results
            for item in out_row:
                
                try:
                    item = item.strip()
                    # Check if the item contains a colon
                    if (item.count(':') == 1 and item.split(':')[0] != ''):
                        dict_output[item.split(':')[0].strip()] = item.split(':')[1].strip()
                    else:
                        dict_output['Unlabeled'].append(item)
                except:
                    dict_output['Unlabeled'].append(item)
            
            # Make sure the unlabeled key gets added to the end of the dictionary (ordered dict)
            tmp_unlabeled = dict_output['Unlabeled']
            del dict_output['Unlabeled']
            output_dict = _OrderedDict(dict_output)
            output_dict['Unlabeled'] = tmp_unlabeled
            
            # check if the Unlabeled key is empty if yes, delete the key
            if len(output_dict['Unlabeled']) == 0:
                del output_dict['Unlabeled']
            
            result.append(dict(output_dict))
            
        df[output] = result
        
    return df


def date_properties(df: _pd.DataFrame, input: _pd.Timestamp, property: str, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract date properties from a date (day, month, year, etc...)
    additionalProperties: false
    required:
      - input
      - property
    properties:
      input:
        type:
          - string
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
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
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')

    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        # Converting data to datetime
        df_temp = _pd.to_datetime(df[input_column])
        
        properties_object = {
            'day': df_temp.dt.day,
            'day_of_year': df_temp.dt.day_of_year,
            'month': df_temp.dt.month,
            'month_name': df_temp.dt.month_name(),
            'weekday': df_temp.dt.weekday,
            'week_day_name': df_temp.dt.day_name(),
            'week_year': df_temp.dt.isocalendar()['week'],
            'quarter': df_temp.dt.quarter,
        }
        
        if property in properties_object.keys():
            df[output_column] = properties_object[property]
        else:
            raise ValueError(f"\"{property}\" not a valid date property.")
    
    return df


def date_range(df: _pd.DataFrame, start_time: _pd.Timestamp, end_time: _pd.Timestamp, output: str, range: str = 'day') -> _pd.DataFrame:
    """
    type: object
    description: Extract date range frequency from two dates
    additionalProperties: false
    required:
      - start_time
      - end_time
      - output
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
      range:
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
    range_object = {
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
    if range not in range_object.keys():
        raise ValueError(f"\"{range}\" not a valid frequency")
        
    # Converting data to datetime
    df[start_time] = _pd.to_datetime(df[start_time])
    df[end_time] = _pd.to_datetime(df[end_time])
        
    # Removing timezone information from columns before operation
    start_data = df[start_time].dt.tz_localize(None).copy()
    end_date = df[end_time].dt.tz_localize(None).copy()
    
    results = []
    for start, end in zip(start_data, end_date):
        results.append(len(_pd.date_range(start, end, freq=range_object[range])[1:]))
    
    df[output] = results
    
    return df


def html(df: _pd.DataFrame, input: _Union[str, list], data_type: str, output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Extract elements from strings containing html. Requires WrangleWorks Account.
    additionalProperties: false
    required:
      - input
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
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
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
        type:
          - string
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output columns
      property_type:
        type: string
        description: The specific type of properties to extract
      return_data_type:
        type: string
        description: The format to return the data, as a list or as a string
        enum:
          - Colours
          - Materials
          - Shapes
          - Standards
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.properties(df[input_column].astype(str).tolist(), type=property_type, return_data_type=return_data_type)
    
    return df


def regex(df: _pd.DataFrame, input: str, find: str, output: str) -> _pd.DataFrame:
    """
    type: object
    description: Extract single values using regex
    additionalProperties: false
    required:
      - input
      - output
      - find
    properties:
      input:
        type: string
        description: Name of the input column.
    output:
      type: string
      description: Name of the output column.
    find:
      type: string
      description: Pattern to find using regex
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output are equal lengths
    if len(input) != len(output):
        raise ValueError('The lists for input and output must be the same length.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].apply(lambda x: _re.findall(find, x))
    
    return df
