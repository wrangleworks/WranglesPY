"""
Functions to run extraction wrangles
"""
from typing import Union as _Union
import re as _re
import logging as _logging
import pandas as _pd
from .. import extract as _extract
from .. import data as _data


_OUTPUT_FORMAT_ALIASES = {
    "json": "json",
    "json list": "json_list",
    "json_list": "json_list",
    "list": "json_list",
    "array": "json_list",
    "json dictionary": "json_dictionary",
    "json dict": "json_dictionary",
    "json_dictionary": "json_dictionary",
    "json_dict": "json_dictionary",
    "dict": "json_dictionary",
    "dictionary": "json_dictionary",
    "columns": "columns",
    "column": "columns",
    "string": "string",
    "text": "string",
}


def _normalize_output_format(output_format, default):
    if output_format is None:
        return default

    output_format = _OUTPUT_FORMAT_ALIASES.get(
        str(output_format).strip().lower().replace("-", "_"),
        output_format
    )

    if output_format == "json":
        return default

    if output_format not in ("json_list", "json_dictionary", "columns", "string"):
        raise ValueError(
            "output_format must be one of List, Dictionary, Columns, or String"
        )

    return output_format


def _ensure_list(value):
    return value if isinstance(value, list) else [value]


def _is_columns_format(output_format):
    return _normalize_output_format(output_format, "json_list") == "columns"


def _stringify_list(value, delimiter):
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return delimiter.join([str(item) for item in value])
    return str(value)


def _write_list_output(
    df,
    output,
    results,
    output_format,
    delimiter=", ",
    default_format="json_list",
    output_column_name=None
):
    output_format = _normalize_output_format(output_format, default_format)

    if output_format == "json_dictionary":
        raise ValueError("output_format Dictionary is only valid for dictionary-producing extracts")

    if output_format == "string":
        df[output[0]] = [_stringify_list(row, delimiter) for row in results]
        return

    if output_format == "columns":
        output_count = len(output) if len(output) > 1 else max(
            [len(row) for row in results if isinstance(row, list)] or [1]
        )
        output_columns = (
            output
            if len(output) > 1
            else [f"{output_column_name or output[0]} {i + 1}" for i in range(output_count)]
        )
        for i, output_column in enumerate(output_columns):
            df[output_column] = [
                row[i] if isinstance(row, list) and len(row) > i else ""
                for row in results
            ]
        return

    df[output[0]] = results


def _dict_keys(results):
    keys = []
    for row in results:
        if isinstance(row, dict):
            for key in row:
                if key not in keys:
                    keys.append(key)
    return keys


def _write_dict_output(df, output, results, output_format, default_format="json_dictionary"):
    output_format = _normalize_output_format(output_format, default_format)

    if output_format in ("json_list", "string"):
        raise ValueError("output_format List or String is only valid for list-producing extracts")

    if output_format == "columns":
        output_columns = output if len(output) > 1 else (_dict_keys(results) or output)
        for output_column in output_columns:
            df[output_column] = [
                row.get(output_column, "") if isinstance(row, dict) else ""
                for row in results
            ]
        return

    df[output[0]] = results


def _write_results(
    df,
    output,
    results,
    output_format,
    delimiter=", ",
    default_format="json_list",
    output_column_name=None
):
    if default_format == "json_dictionary":
        _write_dict_output(df, output, results, output_format)
    else:
        _write_list_output(
            df,
            output,
            results,
            output_format,
            delimiter,
            default_format,
            output_column_name
        )


def _combine_list_rows(rows):
    combined = []
    for row in rows:
        if isinstance(row, list):
            combined.extend(row)
        elif row not in ("", None):
            combined.append(row)
    return list(dict.fromkeys(combined))


def _combine_dict_rows(rows):
    combined = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            values = value if isinstance(value, list) else [value]
            combined[key] = _combine_list_rows([combined.get(key, []), values])
    return combined


def address(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list],
    dataType: str,
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", ",
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
          - integer
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
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_format(output_format):
        results = _extract.address(
            df[input[0]].astype(str).tolist(),
            dataType,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, delimiter, output_column_name=output_column_name)
    elif len(output) == 1 and len(input) > 1:
        results = _extract.address(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            dataType,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, delimiter, output_column_name=output_column_name)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.address(
                df[input_column].astype(str).tolist(),
                dataType,
                **kwargs
            )
            _write_list_output(df, [output_column], results, output_format, delimiter, output_column_name=output_column_name)
  
    return df


def ai(
    df: _pd.DataFrame,
    api_key: str,
    input: list = None,
    output: _Union[dict, str, list] = None,
    model_id: str = None,
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", ",
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
          - integer
          - array
        description: |-
          Name or list of input columns to give to the AI
          to use to determine the output. If not specified, all
          columns will be used.
      output:
        type: [object, string, array]
        description: List and description of the output you want
        patternProperties:
          "^[a-zA-Z0-9 _-]+$":
            type: [object, string]
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
        description: The name of the AI model to use
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
      model_id:
        type: string
        description: Use a saved definition from an extract ai wrangle.
      strict:
        type: boolean
        description: >-
          Enable strict mode. Default False.
          If True, the function will be required to match the schema,
          but may be more limited in the schema it can return.
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - Dictionary
          - Columns
          - String
      output_column_name:
        type: string
        description: Column name to use when output_format is Dictionary
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
    """
    output_format_normalized = _normalize_output_format(output_format, "columns")

    # If input is provided, extract only those columns
    # Otherwise, provide the whole dataframe
    if input is not None:
        if not isinstance(input, list):
            input = [input]
        df_temp = df[input]
    else:
        df_temp = df
    
    # Target columns will contain a list of column names
    # to insert to created results into
    target_columns = None

    if model_id is not None and output is not None:
        # If user provided a model_id and output then
        # output sets the columns for the results

        # Ensure output is a list
        if isinstance(output, list):
            target_columns = output
        else:
            target_columns = [output]

        output = None

        # If more than one column is expected to be output
        # check that matches the length of the model defined
        if len(target_columns) > 1:
            metadata = {
                str(k).lower(): v
                for k, v in _data.model_content(model_id).items()
            }
            if len(target_columns) != len(metadata['data']):
                raise ValueError(
                  f"The number of columns does not match the number defined in model_id {model_id}. ",
                  f"Expected {len(metadata['data'])}"
                )

    # Otherwise output defines the schema the AI is expected to produce

    # If a single value is provided, convert to an
    # empty dictionary for compatibility with JSON schema
    elif output is not None and not isinstance(output, (dict, list)):
        output = {str(output): {}}

    # If output was provided as a list
    # then merge to a single dict
    elif isinstance(output, list):
        temp_dict = {}
        for item in output:
            if isinstance(item, dict):
                temp_dict.update(item)
            else:
                temp_dict.update({str(item): {}})
        output = temp_dict

    # If a schema has been provided, define the target columns
    if not target_columns and output is not None:
        target_columns = list(output.keys())

    results = _extract.ai(
        df_temp.to_dict(orient='records'),
        api_key=api_key,
        output=output,
        model_id=model_id,
        **kwargs
    )

    try:
        exploded_df = _pd.json_normalize(results, max_level=0).fillna('').set_index(df.index)

        if output_format_normalized == "json_dictionary":
            if output_column_name is None:
                output_column_name = target_columns[0] if target_columns and len(target_columns) == 1 else "output"
            df[output_column_name] = results
        elif output_format_normalized == "string":
            if target_columns and len(target_columns) != 1:
                raise ValueError("output_format String can only be used with a single output column")
            output_column = (
                target_columns[0]
                if target_columns
                else output_column_name or "output"
            )
            if len(exploded_df.columns) == 1:
                df[output_column] = [
                    _stringify_list(row, delimiter)
                    for row in exploded_df[exploded_df.columns[0]].tolist()
                ]
            else:
                df[output_column] = [
                    delimiter.join([_stringify_list(value, delimiter) for value in row.values()])
                    for row in results
                ]
        elif target_columns and len(target_columns) == 1:
            if len(exploded_df.columns) == 1:
                # If the AI model only returns a single column
                # then use the contents of that columns as the output
                df[target_columns[0]] = exploded_df[exploded_df.columns[0]]
            else:
                # Else insert as a dict to the target column
                df[target_columns[0]] = results
        else:
            if not target_columns:
                target_columns = exploded_df.columns
            else:
                # Ensure all the required keys are included in the output,
                # even if chatGPT doesn't preserve them
                for col in target_columns:
                  if col not in exploded_df.columns:
                      exploded_df[col] = ""

            # Merge back into the original dataframe
            df[target_columns] = exploded_df[target_columns]
    except:
      raise RuntimeError("Unable to parse response from AI model")

    return df


def attributes(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list],
    responseContent: str = 'span',
    attribute_type: str = None,
    desired_unit: str = None,
    bound: str = 'mid',
    first_element: bool = False,
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", ",
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
          - integer
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
      first_element:
        type: boolean
        description: Get the first element from results
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Dictionary
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
    $ref: "#/$defs/misc/unit_entity_map"
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_format(output_format):
        results = _extract.attributes(
            df[input[0]].astype(str).tolist(),
            responseContent,
            attribute_type,
            desired_unit,
            bound,
            False,
            **kwargs
        )
        _write_results(
            df,
            output,
            results,
            output_format,
            delimiter,
            "json_list" if attribute_type else "json_dictionary",
            output_column_name
        )
    elif len(output) == 1 and len(input) > 1:
        # df[output[0]] = _extract.attributes(df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist())
        results = _extract.attributes(
            df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist(),
            responseContent,
            attribute_type,
            desired_unit,
            bound,
            first_element if output_format is None else False,
            **kwargs
        )
        _write_results(
            df,
            output,
            results,
            output_format,
            delimiter,
            "json_list" if attribute_type else "json_dictionary",
            output_column_name
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.attributes(
                df[input_column].astype(str).tolist(),
                responseContent,
                attribute_type,
                desired_unit,
                bound,
                first_element if output_format is None else False,
                **kwargs
            )
            _write_results(
                df,
                [output_column],
                results,
                output_format,
                delimiter,
                "json_list" if attribute_type else "json_dictionary",
                output_column_name
            )
        
    return df


def brackets(
    df: _pd.DataFrame, 
    input: _Union[str, int, list],
    output: _Union[str, list],
    find: _Union[str, list] = 'all',
    include_brackets: bool = False,
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", "
) -> _pd.DataFrame:
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
          - integer
          - array
        description: Name of the input column
      output:
        type:
          - string
          - array
        description: Name of the output columns
      find:
        type: 
          - string
          - array
        description: (Optional) The type of brackets to find (round '()', square '[]', curly '{}', angled '<>'). Default is all brackets.
      include_brackets:
        type: boolean
        description: (Optional) Include the brackets in the output
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    _logging.debug(f": Extracting from brackets :: input :: {input}")
    # Ensure find is a list
    if not isinstance(find, list): find = [find]

    # Ensure find only contains the elements: round, square, curly, angled
    bracket_types = ['round', 'square', 'curly', 'angled', 'all']

    if not all(element in bracket_types for element in find):
        raise ValueError("find must only contain the elements: round, square, curly, angled")

    # If only only one output and multiple inputs, concatenate the inputs
    return_data_type = "string" if output_format is None else "list"

    if len(input) == 1 and _is_columns_format(output_format):
        results = _extract.brackets(
            df[input[0]].astype(str).tolist(),
            find,
            include_brackets,
            return_data_type=return_data_type
        )
        _write_list_output(
            df,
            output,
            results,
            output_format,
            delimiter,
            default_format="string",
            output_column_name=output_column_name
        )
    elif len(output) == 1 and len(input) > 1:
        results = _extract.brackets(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            find,
            include_brackets,
            return_data_type=return_data_type
        )
        _write_list_output(
            df,
            output,
            results,
            output_format,
            delimiter,
            default_format="string",
            output_column_name=output_column_name
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.brackets(
                df[input_column].astype(str).tolist(),
                find,
                include_brackets,
                return_data_type=return_data_type
            )
            _write_list_output(
                df,
                [output_column],
                results,
                output_format,
                delimiter,
                default_format="string",
                output_column_name=output_column_name
            )

    return df


def codes(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list],
    first_element: bool = False,
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", ",
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
          - integer
          - array
        description: Name or list of input columns.
      output:
        type:
          - string
          - array
        description: Name or list of output columns
      first_element:
        type: boolean
        description: Get the first element from results
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
      min_length:
        type:
          - integer
          - string
        description: Minimum length of allowed results
      max_length:
        type:
          - integer
          - string
        description: Maximum length of allowed results
      strategy:
        type: string
        description: How aggressive to be at removing false positives such as measurements.
        enum:
          - lenient
          - balanced
          - strict
      sort_order:
        type: string
        description: Default is as found in the input. Also allows longest or shortest.
        enum:
          - longest
          - shortest
      disallowed_patterns:
        type: string
        description: A pattern or JSON array of regex patterns to not include in the found codes
      include_multi_part_tokens:
        type: boolean
        description: Whether to include multi-part tokens that have a space. Default True.
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_format(output_format):
        results = _extract.codes(
            df[input[0]].astype(str).tolist(),
            False,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, delimiter, output_column_name=output_column_name)
    elif len(output) == 1 and len(input) > 1:
        results = _extract.codes(
            df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist(),
            first_element if output_format is None else False,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, delimiter, output_column_name=output_column_name)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.codes(
                df[input_column].astype(str).tolist(),
                first_element if output_format is None else False,
                **kwargs
            )
            _write_list_output(df, [output_column], results, output_format, delimiter, output_column_name=output_column_name)

    return df


def custom(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    model_id: _Union[str, list],
    output: _Union[str, list] = None,
    use_labels: bool = False,
    first_element: bool = False,
    case_sensitive: bool = False,
    extract_raw: bool = False,
    use_spellcheck: bool = False,
    sort: str = 'training_order',
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", ",
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
          - integer
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
      sort:
        type: string
        description: Sort the results
        enum:
          - training_order
          - input_order
          - longest
          - shortest
          - alphabetical
          - reverse_alphabetical
          - ascending
          - descending
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Dictionary
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
    """
    if output is None: output = input
    
    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    if not isinstance(model_id, list): model_id = [model_id]

    default_format = "json_dictionary" if use_labels else "json_list"
    
    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_format(output_format) and len(model_id) == 1:
        results = _extract.custom(
            df[input[0]].astype(str).tolist(),
            model_id=model_id[0],
            first_element=False,
            use_labels=use_labels,
            case_sensitive=case_sensitive,
            extract_raw=extract_raw,
            use_spellcheck=use_spellcheck,
            sort=sort,
            **kwargs
        )
        _write_results(df, output, results, output_format, delimiter, default_format, output_column_name)

    elif len(input) == len(output) and len(model_id) == 1:
        # if one model_id, then use that model for all columns inputs and outputs
        model_id = [model_id[0] for _ in range(len(input))]
        for in_col, out_col, model in zip(input, output, model_id):
            results = _extract.custom(
                df[in_col].astype(str).tolist(),
                model_id=model,
                first_element=first_element if output_format is None else False,
                use_labels=use_labels,
                case_sensitive=case_sensitive,
                extract_raw=extract_raw,
                use_spellcheck=use_spellcheck,
                sort=sort,
                **kwargs
            )
            _write_results(df, [out_col], results, output_format, delimiter, default_format, output_column_name)
    
    elif len(input) > 1 and len(output) == 1 and len(model_id) == 1:
        model_id = [model_id[0] for _ in range(len(input))]
        output = output[0]
        single_model_id = model_id[0]
        df_temp = _pd.DataFrame(index=range(len(df)))
        for i, in_col in enumerate(input):
            df_temp[output + str(i)] = _extract.custom(
                df[in_col].astype(str).tolist(),
                model_id=single_model_id,
                first_element=first_element if output_format is None else False,
                use_labels=use_labels,
                case_sensitive=case_sensitive,
                extract_raw=extract_raw,
                use_spellcheck=use_spellcheck,
                sort=sort,
                **kwargs
            )

        if use_labels:
            results = [_combine_dict_rows(row) for row in df_temp.values.tolist()]
        else:
            results = [_combine_list_rows(row) for row in df_temp.values.tolist()]
        _write_results(df, [output], results, output_format, delimiter, default_format, output_column_name)

    else:
        # Iterate through the inputs, outputs and model_ids
        for in_col, out_col, model in zip(input, output, model_id):
            results = _extract.custom(
                df[in_col].astype(str).tolist(),
                model_id=model,
                first_element=first_element if output_format is None else False,
                use_labels=use_labels,
                case_sensitive=case_sensitive,
                extract_raw=extract_raw,
                use_spellcheck=use_spellcheck,
                sort=sort,
                **kwargs
            )
            _write_results(df, [out_col], results, output_format, delimiter, default_format, output_column_name)

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
          - integer
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

    _logging.debug(f": Extracting date property :: {property} from {input}")
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
    _logging.debug(f": Generating date range :: output :: {output}")
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
    input: _Union[str, int, list],
    data_type: str,
    output: _Union[str, list] = None,
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", ",
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
          - integer
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
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    _logging.debug(f": Extracting from HTML :: input :: {input}")

    if len(input) == 1 and _is_columns_format(output_format):
        results = _extract.html(
            df[input[0]].astype(str).tolist(),
            dataType=data_type,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, delimiter, output_column_name=output_column_name)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.html(
                df[input_column].astype(str).tolist(),
                dataType=data_type,
                **kwargs
            )
            _write_list_output(df, [output_column], results, output_format, delimiter, output_column_name=output_column_name)
            
    return df


def properties(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list],
    property_type: str = None,
    return_data_type: str = 'list',
    first_element: bool = False,
    output_format: str = None,
    output_column_name: str = None,
    delimiter: str = ", ",
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
          - integer
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
        description: Legacy format option. Prefer output_format.
        enum:
          - list
          - string
      first_element:
        type: boolean
        description: Get the first element from results
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Dictionary
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if output_format is None and return_data_type == "string":
        output_format = "string"

    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_format(output_format):
        results = _extract.properties(
            df[input[0]].astype(str).tolist(),
            type=property_type,
            return_data_type='list',
            first_element=False,
            **kwargs
        )
        _write_results(
            df,
            output,
            results,
            output_format,
            delimiter,
            "json_list" if property_type else "json_dictionary",
            output_column_name
        )
    elif len(output) == 1 and len(input) > 1:
        results = _extract.properties(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            type=property_type,
            return_data_type='list' if output_format is not None else return_data_type,
            first_element=first_element if output_format is None else False,
            **kwargs
        )
        _write_results(
            df,
            output,
            results,
            output_format,
            delimiter,
            "json_list" if property_type else "json_dictionary",
            output_column_name
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.properties(
                df[input_column].astype(str).tolist(),
                type=property_type,
                return_data_type='list' if output_format is not None else return_data_type,
                first_element=first_element if output_format is None else False,
                **kwargs
            )
            _write_results(
                df,
                [output_column],
                results,
                output_format,
                delimiter,
                "json_list" if property_type else "json_dictionary",
                output_column_name
            )
    
    return df

def regex(
  df: _pd.DataFrame,
  input: _Union[str, int, list],
  find: str,
  output: _Union[str, list],
  output_pattern: str = None,
  first_element: bool = False,
  output_format: str = None,
  output_column_name: str = None,
  delimiter: str = ", "
  ) -> _pd.DataFrame:
    r"""
    type: object
    description: Extract matches or specific capture groups using regex
    additionalProperties: false
    required:
      - input
      - output
      - find
    properties:
      input:
        type: 
          - string
          - integer
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
      output_pattern:
        type: string
        description: |
          Specifies the format to output matches and specific capture groups using backreferences (e.g., `\1`, `\2`). Default is to return entire matches.

          **Example**: For a regex pattern `r'(\d+)\s(\w+)'` and `output_pattern = '\2 \1'`, with input `'120 volt'`, the output would be `'volt 120'`.
      first_element:
        type: boolean
        description: Get the first element from results
      output_format:
        type: string
        description: Format of the extract output
        enum:
          - List
          - Columns
          - String
      delimiter:
        type: string
        description: Delimiter to use when output_format is String
      output_column_name:
        type: string
        description: Base output column name to use when output_format is Columns
    """
    # If output is not specified, overwrite input columns in place
    if output is None: 
        output = input

    # If a string is provided, convert to list
    if not isinstance(input, list): 
        input = [input]
    if not isinstance(output, list): 
        output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not _is_columns_format(output_format):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')
    
    _logging.debug(f": Extracting regex patterns :: input :: {input}")
    find_pattern = _re.compile(find)

    def _matches(value):
        value = str(value) if value is not None else ""
        matches = [match.group(0) for match in _re.finditer(find_pattern, value)]
        if output_pattern:
            matches = [find_pattern.sub(output_pattern, match) for match in matches]
        return matches

    def _write_regex(input_column, output_columns):
        results = df[input_column].apply(_matches).tolist()
        if output_format is None and first_element:
            df[output_columns[0]] = [row[0] if len(row) >= 1 else "" for row in results]
        else:
            _write_list_output(df, output_columns, results, output_format, delimiter, output_column_name=output_column_name)

    if len(input) == 1 and _is_columns_format(output_format):
        _write_regex(input[0], output)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            _write_regex(input_column, [output_column])

    return df

