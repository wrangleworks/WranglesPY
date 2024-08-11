"""
Functions to run extraction wrangles
"""
from typing import Union as _Union
import re as _re
import concurrent.futures as _futures
from collections import OrderedDict as _OrderedDict
import pandas as _pd
from .. import extract as _extract
from .. import format as _format
from .. import openai as _openai


def address(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list],
    dataType: str,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Extract parts of addresses. Requires WrangleWorks Account.
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

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(output) == 1 and len(input) > 1:
        df[output[0]] = _extract.address(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            dataType,
            **kwargs
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.address(
                df[input_column].astype(str).tolist(),
                dataType,
                **kwargs
            )
  
    return df


def ai(
    df: _pd.DataFrame,
    output: list,
    api_key: str,
    input: list = None,
    model: str = "gpt-3.5-turbo",
    threads: int = 10,
    timeout: int = 25,
    retries: int = 0,
    messages: list = [],
    url: str = "https://api.openai.com/v1/chat/completions",
    **kwargs
):
    """
    type: object
    description: Extract data using an AI model.
    additionalProperties: false
    required:
      - output
      - api_key
    properties:
      input:
        type:
          - string
          - array
        description: |-
          Name or list of input columns to give to the AI
          to use to determine the output. If not specified, all
          columns will be used.
      output:
        type: object
        description: List and description of the output you want
        patternProperties:
          "^[a-zA-Z0-9]+$":
            type: object
            properties:
              type:
                type: string
                description: The type of data you'd like the model to return.
                enum:
                  - string
                  - number
                  - integer
                  - boolean
                  - "null"
                  - object
                  - array
              description:
                type: string
                description: Description of the output you'd like the model to return.
              enum:
                type: array
                description: List of possible values for the output.
              default:
                type:
                  - string
                  - number
                  - integer
                  - boolean
                  - "null"
                  - object
                  - array
                description: A default value to return.
              examples:
                type: array
                description: Provide examples of typical values to return.
      api_key:
        type: string
        description: API Key for the model
      model:
        type: string
        description: The name of the model
      threads:
        type: integer
        description: The number of requests to send in parallel
      timeout:
        type: integer
        description: The number of seconds to wait for a response before timing out
      retries:
        type: integer
        description: >-
          The number of times to retry if the request fails.
          This will apply exponential backoff to help with rate limiting.
      url:
        type: string
        description: |-
          Override the default url for the AI endpoint.
          Must use the OpenAI chat completions API.
      messages:
        type:
          - string
          - array
        description: Optional. Provide additional overall instructions for the AI.
    """
    if input is not None:
        if not isinstance(input, list):
            input = [input]
        df_temp = df[input]
    else:
        df_temp = df

    # Add a default for type array if not already specified.
    # ChatGPT appears to need this to function correctly.
    for k, v in output.items():
        if v.get("type") == "array" and "items" not in v:
            output[k]["items"] = {"type": "string"}

    # Format any user submitted header messages
    if not isinstance(messages, list): messages = [messages]
    messages = [
        {
            "role": "user",
            "content": message
        }
        for message in messages
    ]

    system_messages = [
        {
            "role": "system",
            "content": " ".join([
                "You are a data analyst.",
                "Your job is to extract and standardize information as provided by the user.",
                "The data may be provided as a single value or as YAML syntax with keys and values."
            ])
        },
        {
            "role": "system",
            "content": " ".join([
                "Use the function parse_output to return the data to be submitted.",
                "Only use the functions you have been provided with.",
            ])
        },
    ] + messages

    settings = {
        "model": model,
        "messages": system_messages,
        "temperature": 0,
        "tools": [{
            "type": "function",
            "function": {
                "name": "parse_output",
                "description": "Submit the output corresponding to the extracted data in the form the user requires.",
                "parameters": {
                    "type": "object",
                    "properties": output,
                    "required": list(output.keys())
                }
            }
        }],
        "tool_choice": {"type": "function", "function": {"name": "parse_output"}},
        **kwargs
    }

    with _futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = list(executor.map(
            _openai.chatGPT,
            df_temp.to_dict(orient='records'), 
            [api_key] * len(df),
            [settings] * len(df),
            [url] * len(df),
            [timeout] * len(df),
            [retries] * len(df),
        ))

    try:
      exploded_df = _pd.json_normalize(results, max_level=0).fillna('').set_index(df.index)
    except:
      raise RuntimeError("Unable to parse response from AI model")

    # Ensure all the required keys are included in the output,
    # even if chatGPT doesn't preserve them
    for col in output.keys():
        if col not in exploded_df.columns:
            exploded_df[col] = ""
    df[list(output.keys())] = exploded_df[list(output.keys())]
    return df


def attributes(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list],
    responseContent: str = 'span',
    attribute_type: str = None,
    desired_unit: str = None,
    bound: str = 'mid',
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Extract numeric attributes from the input such as weights or lengths. Requires WrangleWorks Account.
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
      desired_unit:
        type: string
        description: Convert the extracted unit to the desired unit
    $ref: "#/$defs/misc/unit_entity_map"
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')
    
    if len(output) == 1 and len(input) > 1:
        # df[output[0]] = _extract.attributes(df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist())
        df[output[0]] = _extract.attributes(
            df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist(),
            responseContent,
            attribute_type,
            desired_unit,
            bound,
            **kwargs
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.attributes(
                df[input_column].astype(str).tolist(),
                responseContent,
                attribute_type,
                desired_unit,
                bound,
                **kwargs
            )
        
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

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(output) == 1 and len(input) > 1:
        df[output[0]] = _extract.brackets(df[input].astype(str).aggregate(' '.join, axis=1).tolist())
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.brackets(df[input_column].astype(str).tolist())

    return df


def codes(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list],
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Extract alphanumeric codes from the input. Requires WrangleWorks Account.
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

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(output) == 1 and len(input) > 1:
        df[output[0]] = _extract.codes(
            df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist(),
            **kwargs
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.codes(
                df[input_column].astype(str).tolist(),
                **kwargs
            )

    return df


def custom(
    df: _pd.DataFrame,
    input: _Union[str, list],
    model_id: _Union[str, list],
    output: _Union[str, list] = None,
    use_labels: bool = False,
    first_element: bool = False,
    case_sensitive: bool = False,
    extract_raw: bool = False,
    use_spellcheck: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Extract data from the input using a DIY or bespoke extraction wrangle. Requires WrangleWorks Account and Subscription.
    required:
      - input
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
        type: boolean
        description: "Use Labels in the extract output {label: value}"
      first_element:
        type: boolean
        description: Get the first element from results
      case_sensitive:
        type: boolean
        description: Allows the wrangle to be case sensitive if set to True, default is False.
      extract_raw:
        type: boolean
        description: Extract the raw data from the wrangle
      use_spellcheck:
        type: boolean
        description: Use spellcheck to also find minor mispellings compared to the reference data
    """
    if output is None: output = input
    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    if not isinstance(model_id, list): model_id = [model_id]
    
    if len(input) == len(output) and len(model_id) == 1:
        # if one model_id, then use that model for all columns inputs and outputs
        model_id = [model_id[0] for _ in range(len(input))]
        for in_col, out_col, model in zip(input, output, model_id):
            df[out_col] = _extract.custom(
                df[in_col].astype(str).tolist(),
                model_id=model,
                first_element=first_element,
                use_labels=use_labels,
                case_sensitive=case_sensitive,
                extract_raw=extract_raw,
                use_spellcheck=use_spellcheck,
                **kwargs
            )
    
    elif len(input) > 1 and len(output) == 1 and len(model_id) == 1:
        # if there are multiple inputs and one output and one model_id. concatenate the inputs
        df[output[0]] = _extract.custom(
            _format.concatenate(df[input].astype(str).values.tolist(), ' '),
            model_id=model_id[0],
            first_element=first_element,
            use_labels=use_labels,
            case_sensitive=case_sensitive,
            extract_raw=extract_raw,
            use_spellcheck=use_spellcheck,
            **kwargs
        )
    
    else:
        # Iterate through the inputs, outputs and model_ids
        for in_col, out_col, model in zip(input, output, model_id):
            df[out_col] = _extract.custom(
                df[in_col].astype(str).tolist(),
                model_id=model,
                first_element=first_element,
                use_labels=use_labels,
                case_sensitive=case_sensitive,
                extract_raw=extract_raw,
                use_spellcheck=use_spellcheck,
                **kwargs
            )

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

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')
    
    if len(output) == 1 and len(input) > 1:
        output = [output[0] for i in range(len(input))]
        # df_temp = df[input].apply(_pd.to_datetime)
        temp = []
        # for i in range(len(input)):
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
            
            if property in properties_object.keys() and temp == []:
                temp.append([properties_object[property][0]])

            elif property in properties_object.keys() and temp != []:
                for j in range(len(df)):
                    temp[j].append(properties_object[property][0])

            else:
                raise ValueError(f"\"{property}\" not a valid date property.")
        df[output[0]] = temp
    else:
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
      - range
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


def html(
    df: _pd.DataFrame,
    input: _Union[str, list],
    data_type: str,
    output: _Union[str, list] = None,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Extract elements from strings containing html. Requires WrangleWorks Account.
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
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = _extract.html(
            df[input_column].astype(str).tolist(),
            dataType=data_type,
            **kwargs
        )
            
    return df


def properties(
    df: _pd.DataFrame,
    input: _Union[str, list],
    output: _Union[str, list],
    property_type: str = None,
    return_data_type: str = 'list',
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Extract text properties from the input. Requires WrangleWorks Account.
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
        enum:
          - Colours
          - Materials
          - Shapes
          - Standards
      return_data_type:
        type: string
        description: The format to return the data, as a list or as a string
        enum:
          - list
          - string
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(output) == 1 and len(input) > 1:
        df[output[0]] = _extract.properties(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            type=property_type,
            return_data_type=return_data_type,
            **kwargs
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            df[output_column] = _extract.properties(
                df[input_column].astype(str).tolist(),
                type=property_type,
                return_data_type=return_data_type,
                **kwargs
            )
    
    return df


def regex(df: _pd.DataFrame, input: _Union[str, list], find: str, output: _Union[str, list]) -> _pd.DataFrame:
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
        type: 
          - string
          - array
        description: Name of the input column(s).
      output:
        type:
          - string
          - array
        description: Name of the output column(s).
      find:
        type: string
        description: Pattern to find using regex
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1:
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')
    
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = df[input_column].apply(lambda x: _re.findall(find, x))
    
    return df
