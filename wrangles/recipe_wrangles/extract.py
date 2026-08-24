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
    "concatenate": "concatenate",
    "concat": "concatenate",
}
_WEB_SEARCH_SOURCES_KEY = "web_search_sources"


def _normalize_output_format(output_format, default):
    if output_format is None:
        return default

    output_format = _OUTPUT_FORMAT_ALIASES.get(
        str(output_format).strip().lower().replace("-", "_"),
        output_format
    )

    if output_format == "json":
        return default

    if output_format not in ("json_list", "json_dictionary", "columns", "concatenate"):
        raise ValueError(
            "output_format must be one of list, dictionary, columns, or concatenate"
        )

    return output_format


def _ensure_list(value):
    return value if isinstance(value, list) else [value]


def _is_columns_target(output, output_format, output_is_list=False):
    """
    Whether results should be split across explicit output columns.

    An explicit output_format always wins. Otherwise, providing output
    as a list of one or more column names implies Columns format.
    """
    if output_format is not None:
        return _normalize_output_format(output_format, "json_list") == "columns"
    return output_is_list or (isinstance(output, list) and len(output) > 1)


def _resolve_output_format(output, output_format, default_format, output_is_list=False):
    if output_format is None and (output_is_list or (isinstance(output, list) and len(output) > 1)):
        return "columns"
    return _normalize_output_format(output_format, default_format)


def _stringify_list(value, char):
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return char.join([str(item) for item in value])
    return str(value)


def _write_list_output(
    df,
    output,
    results,
    output_format,
    char=", ",
    default_format="json_list",
    output_is_list=False
):
    output_format = _resolve_output_format(output, output_format, default_format, output_is_list)

    if output_format == "json_dictionary":
        raise ValueError("output_format dictionary is only valid for dictionary-producing extracts")

    if output_format == "concatenate":
        df[output[0]] = [_stringify_list(row, char) for row in results]
        return

    if output_format == "columns":
        # A scalar (non-list) result counts as a single match.
        # Always create at least one column, even if no rows
        # produced any results
        max_result_len = max(
            [len(row) if isinstance(row, list) else 1 for row in results] + [1]
        )
        if len(output) > 1 or output_is_list:
            # Cap the number of columns created to however many
            # output column names were explicitly provided, dropping
            # any results beyond that even if more were found
            output_columns = output[:min(len(output), max_result_len)]
        else:
            # No explicit column names given (a bare string output)
            # with Columns format requested - auto-number columns
            # for however many results were found
            output_columns = [f"{output[0]} {i + 1}" for i in range(max_result_len)]
        for i, output_column in enumerate(output_columns):
            df[output_column] = [
                (row[i] if len(row) > i else "") if isinstance(row, list)
                else (row if i == 0 else "")
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


def _write_dict_output(df, output, results, output_format, default_format="json_dictionary", output_is_list=False):
    output_format = _resolve_output_format(output, output_format, default_format, output_is_list)

    if output_format in ("json_list", "concatenate"):
        raise ValueError("output_format list or concatenate is only valid for list-producing extracts")

    if output_format == "columns":
        output_columns = (
            output
            if len(output) > 1 or output_is_list
            else (_dict_keys(results) or output)
        )
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
    char=", ",
    default_format="json_list",
    output_is_list=False
):
    if default_format == "json_dictionary":
        _write_dict_output(df, output, results, output_format, default_format, output_is_list)
    else:
        _write_list_output(
            df,
            output,
            results,
            output_format,
            char,
            default_format,
            output_is_list
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
    char: str = ", ",
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
          - list
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list):
        results = _extract.address(
            df[input[0]].astype(str).tolist(),
            dataType,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, char, output_is_list=output_is_list)
    elif len(output) == 1 and len(input) > 1:
        results = _extract.address(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            dataType,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, char, output_is_list=output_is_list)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.address(
                df[input_column].astype(str).tolist(),
                dataType,
                **kwargs
            )
            _write_list_output(df, [output_column], results, output_format, char)

    return df


def ai(
    df: _pd.DataFrame,
    api_key: str,
    input: list = None,
    output: _Union[dict, str, list] = None,
    model_id: str = None,
    record_examples: _Union[dict, list] = None,
    output_format: str = None,
    char: str = ", ",
    web_search: bool = False,
    **kwargs
):
    """
    type: object
    description: >-
      Extract structured data from each input row using an AI model. Define
      the desired fields with output, or reuse a saved definition with model_id.
    additionalProperties: false
    required:
      - api_key
    anyOf:
      - required:
          - output
      - required:
          - model_id
    properties:
      input:
        type:
          - string
          - integer
          - array
        description: >-
          Input column name, column index, or list of columns supplied together
          as DATA for each row. If omitted, all dataframe columns are supplied.
        items:
          type: [string, integer]
      output:
        type: [object, string, array]
        description: >-
          Desired extraction. Use an object keyed by output column name for
          structured fields, a string for one prompted value, or an array of
          field names/definitions. Each field may use the schema options below.
        patternProperties:
          "^[a-zA-Z0-9 _-]+$":
            type: [object, string]
            properties:
              type:
                type: string
                description: >-
                  JSON data type required for this field. If omitted, common
                  scalar types are accepted. Fields allow null by default.
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
                description: >-
                  Plain-language definition of the value to extract, including
                  any selection, normalization, unit, or evidence rules.
              enum:
                type: array
                description: >-
                  Allowed output values. The model must choose one of these
                  values; null is also allowed unless nullable is false.
              default:
                type:
                  - string
                  - number
                  - integer
                  - boolean
                  - "null"
                  - object
                  - array
                description: >-
                  JSON Schema annotation for a preferred default. extract.ai
                  does not substitute this value when evidence is missing;
                  describe fallback behavior explicitly or allow null.
              examples:
                title: Field examples
                type:
                  - array
                  - object
                  - string
                  - number
                  - integer
                  - boolean
                  - "null"
                description: >-
                  Field-specific examples. The backward-compatible form is a
                  scalar or list of typical output values. A paired example may
                  instead use input and output, with optional name and notes.
                  Paired examples apply only to this output field; use
                  record_examples for complete output records.
                properties:
                  name:
                    type: string
                    description: Optional label included with this paired field example.
                  notes:
                    type: string
                    description: Optional explanatory guidance included with this paired field example.
                  input:
                    description: Source value or record for this paired field example.
                  output:
                    description: Expected value for this output field only.
                items:
                  anyOf:
                    - type: object
                      required:
                        - input
                        - output
                      properties:
                        name:
                          type: string
                          description: Optional label included with this paired field example.
                        notes:
                          type: string
                          description: Optional explanatory guidance included with this paired field example.
                        input:
                          description: Source value or record for this paired field example.
                        output:
                          description: Expected value for this output field only.
                    - description: Backward-compatible output-only example value.
              properties:
                type:
                  - object
                  - array
                  - string
                description: >-
                  Child fields when type is object. Use an object to define a
                  schema for each child. A list or comma-separated string is a
                  shortcut that creates fixed child names.
              additionalProperties:
                type:
                  - boolean
                  - object
                description: >-
                  Controls keys beyond properties when type is object. Set false
                  for fixed keys, true for arbitrary values, or provide one
                  schema applied to every dynamic value. Dynamic dictionaries
                  use non-strict provider mode plus local validation.
              items:
                type: object
                description: >-
                  Schema applied to every element when this field's type is array.
              nullable:
                type: boolean
                description: >-
                  Whether the field may return null. Defaults to true while
                  the field key remains required. Set false to opt out.
      record_examples:
        title: Record examples
        type:
          - array
          - object
        description: >-
          Whole-record examples. Each example has a separate input value or
          record and the complete expected output record. Optional name and
          notes provide model-visible context. Use {name: ..., notes: ...,
          input: ..., output: ...}. Omitted output fields are completed with
          null. This differs from examples nested under one output field, which
          teach only that field.
        required:
          - input
          - output
        properties:
          name:
            type: string
            description: Optional label used to identify this example in the prompt.
          notes:
            type: string
            description: Optional explanatory guidance included with this example.
          input:
            description: Source value or record the example should match.
          output:
            description: Expected result using the field names defined by output.
        items:
          type: object
          required:
            - input
            - output
          properties:
            name:
              type: string
              description: Optional label used to identify this example in the prompt.
            notes:
              type: string
              description: Optional explanatory guidance included with this example.
            input:
              description: Source value or record the example should match.
            output:
              description: Expected result using the field names defined by output.
      api_key:
        type: string
        description: OpenAI API key used for this wrangle, normally supplied through a recipe variable.
      model:
        type: string
        description: >-
          OpenAI model ID for this call. If omitted, uses the configured
          extract.ai default; a saved model definition may supply its own model.
      threads:
        type: integer
        minimum: 1
        description: Maximum number of row-level requests sent in parallel. The configured default is 32.
      timeout:
        type: number
        exclusiveMinimum: 0
        description: >-
          Maximum seconds for one HTTP attempt. The configured default is 12;
          deadline can end the overall call sooner.
      retries:
        type: integer
        minimum: 0
        description: >-
          Number of additional attempts after a retryable failure. The configured
          default is 1. Backoff and request timeouts remain bounded by deadline.
      url:
        type: string
        description: |-
          Override the endpoint for the selected protocol. A chat/completions URL
          selects the legacy protocol only when protocol is omitted; new recipes
          should use the configured Responses endpoint.
      provider:
        type: string
        description: AI service provider. Currently only OpenAI is supported.
        enum:
          - openai
      protocol:
        type: string
        description: >-
          OpenAI API protocol. Responses is the configured default and is required
          for web_search; chat_completions remains available for legacy definitions.
        enum:
          - responses
          - chat_completions
      deadline:
        type: number
        exclusiveMinimum: 0
        description: >-
          Total seconds allowed for the entire wrangle call, including queued
          work, retries, and backoff. The configured default is 15.
      store:
        type: boolean
        description: Whether OpenAI may store Responses API results. Defaults to false.
      cache:
        type: boolean
        description: >-
          Reuse identical successful results from the bounded warm-instance cache.
          Defaults to true. Set false when fresh model or web results are required.
      cache_ttl:
        type: number
        exclusiveMinimum: 0
        description: >-
          Maximum age in seconds for a cached result used by this call. Applies
          to extracted values and web_search_sources together.
      messages:
        type:
          - string
          - array
        description: >-
          Additional overall instruction or list of instructions applied to
          every row after the configured extraction prompt and examples.
        items:
          type: string
      model_id:
        type: string
        description: >-
          ID of a saved extract.ai definition. Use it instead of defining an
          output schema. When output is also supplied with model_id in a recipe,
          output names the destination column or columns for the saved fields.
      strict:
        type: boolean
        description: >-
          Require OpenAI structured-output strict mode. Defaults to true.
          Definitions with dynamic dictionary keys automatically switch to
          non-strict provider mode and are still validated locally.
      output_format:
        type: string
        description: >-
          How extracted fields are written. columns writes one dataframe column
          per field (default); dictionary keeps one object; concatenate joins
          fields into one string using char.
        enum:
          - dictionary
          - columns
          - concatenate
      char:
        type: string
        description: Separator used only when output_format is concatenate. Defaults to comma-space.
      reasoning:
        type: object
        description: >-
          Responses API reasoning controls. Set effort for reasoning-capable
          models. The configured default is none when that model supports it;
          otherwise the provider default applies.
        properties:
          effort:
            type: string
            description: Amount of reasoning work requested from a compatible model.
            enum:
              - none
              - minimal
              - low
              - medium
              - high
              - xhigh
      verbosity:
        type: string
        description: >-
          Responses API text verbosity for compatible models. Defaults to low
          when supported; ignored with a warning for incompatible models.
        enum:
          - low
          - medium
          - high
      web_search:
        type: boolean
        description: >-
          Enable OpenAI Responses web search; the model decides when searching
          helps. When true, every row also receives web_search_sources: a
          deduplicated list of {title, url} objects in source order, or an empty
          list when no source was used. This reserved column is automatic.
          Requires protocol responses. Defaults to false.
    """
    output_format_normalized = _normalize_output_format(output_format, "columns")
    if not isinstance(web_search, bool):
        raise ValueError("web_search must be true or false.")
    if web_search and _WEB_SEARCH_SOURCES_KEY in df.columns:
        raise ValueError(
            f"Column {_WEB_SEARCH_SOURCES_KEY!r} is reserved when web_search is enabled."
        )

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
    if web_search and target_columns and _WEB_SEARCH_SOURCES_KEY in target_columns:
        raise ValueError(
            f"Output column {_WEB_SEARCH_SOURCES_KEY!r} is reserved when web_search is enabled."
        )

    results = _extract.ai(
        df_temp.to_dict(orient='records'),
        api_key=api_key,
        output=output,
        model_id=model_id,
        record_examples=record_examples,
        web_search=web_search,
        **kwargs
    )

    web_search_sources = None
    if web_search:
        web_search_sources = []
        extraction_results = []
        for result in results:
            if not isinstance(result, dict):
                web_search_sources.append([])
                extraction_results.append(result)
                continue
            result = dict(result)
            sources = result.pop(_WEB_SEARCH_SOURCES_KEY, [])
            web_search_sources.append(sources if isinstance(sources, list) else [])
            extraction_results.append(result)
        results = extraction_results

    try:
        exploded_df = _pd.json_normalize(results, max_level=0).fillna('').set_index(df.index)

        if output_format_normalized == "json_dictionary":
            output_column_name = target_columns[0] if target_columns and len(target_columns) == 1 else "output"
            df[output_column_name] = results
        elif output_format_normalized == "concatenate":
            if target_columns and len(target_columns) != 1:
                raise ValueError("output_format concatenate can only be used with a single output column")
            output_column = target_columns[0] if target_columns else "output"
            if len(exploded_df.columns) == 1:
                df[output_column] = [
                    _stringify_list(row, char)
                    for row in exploded_df[exploded_df.columns[0]].tolist()
                ]
            else:
                df[output_column] = [
                    char.join([_stringify_list(value, char) for value in row.values()])
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

    if web_search_sources is not None:
        df[_WEB_SEARCH_SOURCES_KEY] = _pd.Series(
            web_search_sources,
            index=df.index,
            dtype=object,
        )

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
    char: str = ", ",
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
          - list
          - dictionary
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
    $ref: "#/$defs/misc/unit_entity_map"
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list):
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
            char,
            "json_list" if attribute_type else "json_dictionary",
            output_is_list
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
            char,
            "json_list" if attribute_type else "json_dictionary",
            output_is_list
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
                char,
                "json_list" if attribute_type else "json_dictionary"
            )

    return df


def brackets(
    df: _pd.DataFrame, 
    input: _Union[str, int, list],
    output: _Union[str, list],
    find: _Union[str, list] = 'all',
    include_brackets: bool = False,
    output_format: str = None,
    char: str = ", "
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
          - list
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    _logging.debug(f": Extracting from brackets :: input :: {input}")
    # Ensure find is a list
    if not isinstance(find, list): find = [find]

    # Ensure find only contains the elements: round, square, curly, angled
    bracket_types = ['round', 'square', 'curly', 'angled', 'all']

    if not all(element in bracket_types for element in find):
        raise ValueError("find must only contain the elements: round, square, curly, angled")

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list):
        results = _extract.brackets(
            df[input[0]].astype(str).tolist(),
            find,
            include_brackets,
            return_data_type="list"
        )
        _write_list_output(
            df,
            output,
            results,
            output_format,
            char,
            output_is_list=output_is_list
        )
    elif len(output) == 1 and len(input) > 1:
        results = _extract.brackets(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            find,
            include_brackets,
            return_data_type="list"
        )
        _write_list_output(
            df,
            output,
            results,
            output_format,
            char,
            output_is_list=output_is_list
        )
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.brackets(
                df[input_column].astype(str).tolist(),
                find,
                include_brackets,
                return_data_type="list"
            )
            _write_list_output(
                df,
                [output_column],
                results,
                output_format,
                char
            )

    return df


def codes(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list],
    first_element: bool = False,
    output_format: str = None,
    char: str = ", ",
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
          - list
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
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
        description: Controls filtering of likely false positives such as measurements. Lenient skips this filter; balanced and strict currently apply the same filter. Default is balanced. Unless min_length is provided, minimum lengths default to 3 for lenient, 4 for balanced, and 5 for strict.
        enum:
          - lenient
          - balanced
          - strict
      sort_order:
        type: string
        description: Default is input order. Also allows longest or shortest.
        enum:
          - input
          - longest
          - shortest
      disallowed_patterns:
        type: string
        description: A pattern or JSON array of regex patterns to not include in the found codes
      include_multi_part_tokens:
        type: boolean
        description: Whether to include multi-part tokens that have a space. Default True.
      extract_raw:
        type: boolean
        description: Whether to return tokens with their adjacent non-whitespace characters included, rather than the cleaned token. Default False.
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list):
        results = _extract.codes(
            df[input[0]].astype(str).tolist(),
            False,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, char, output_is_list=output_is_list)
    elif len(output) == 1 and len(input) > 1:
        results = _extract.codes(
            df[input].astype(str).aggregate(' AAA '.join, axis=1).tolist(),
            first_element if output_format is None else False,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, char, output_is_list=output_is_list)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.codes(
                df[input_column].astype(str).tolist(),
                first_element if output_format is None else False,
                **kwargs
            )
            _write_list_output(df, [output_column], results, output_format, char)

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
    include_empty_labels: bool = True,
    sort: str = 'training_order',
    output_format: str = None,
    char: str = ", ",
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
          - list
          - dictionary
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
      include_empty_labels:
        type: boolean
        description: Include labels with no found values in the output when using use_labels=True
    """
    if output is None: output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]
    if not isinstance(model_id, list): model_id = [model_id]

    default_format = "json_dictionary" if use_labels else "json_list"

    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list) and len(model_id) == 1:
        results = _extract.custom(
            df[input[0]].astype(str).tolist(),
            model_id=model_id[0],
            first_element=False,
            use_labels=use_labels,
            case_sensitive=case_sensitive,
            extract_raw=extract_raw,
            use_spellcheck=use_spellcheck,
            include_empty_labels=include_empty_labels,
            sort=sort,
            **kwargs
        )
        _write_results(df, output, results, output_format, char, default_format, output_is_list)

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
                include_empty_labels=include_empty_labels,
                sort=sort,
                **kwargs
            )
            _write_results(df, [out_col], results, output_format, char, default_format)

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
                include_empty_labels=include_empty_labels,
                sort=sort,
                **kwargs
            )

        if use_labels:
            results = [_combine_dict_rows(row) for row in df_temp.values.tolist()]
        else:
            results = [_combine_list_rows(row) for row in df_temp.values.tolist()]
        _write_results(df, [output], results, output_format, char, default_format, output_is_list)

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
                include_empty_labels=include_empty_labels,
                sort=sort,
                **kwargs
            )
            _write_results(df, [out_col], results, output_format, char, default_format)

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
        'years': 'YE',
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
    char: str = ", ",
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
          - list
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    _logging.debug(f": Extracting from HTML :: input :: {input}")

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list):
        results = _extract.html(
            df[input[0]].astype(str).tolist(),
            dataType=data_type,
            **kwargs
        )
        _write_list_output(df, output, results, output_format, char, output_is_list=output_is_list)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            results = _extract.html(
                df[input_column].astype(str).tolist(),
                dataType=data_type,
                **kwargs
            )
            _write_list_output(df, [output_column], results, output_format, char)

    return df


def properties(
    df: _pd.DataFrame,
    input: _Union[str, int, list],
    output: _Union[str, list],
    property_type: str = None,
    return_data_type: str = 'list',
    first_element: bool = False,
    output_format: str = None,
    char: str = ", ",
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
          - list
          - dictionary
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
    """
    # If output is not specified, overwrite input columns in place
    if output is None: output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string provided, convert to list
    if not isinstance(input, list): input = [input]
    if not isinstance(output, list): output = [output]

    # Ensure input and output lengths are compatible
    if output_format is None and return_data_type == "string":
        output_format = "concatenate"

    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list):
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
            char,
            "json_list" if property_type else "json_dictionary",
            output_is_list
        )
    elif len(output) == 1 and len(input) > 1:
        results = _extract.properties(
            df[input].astype(str).aggregate(' '.join, axis=1).tolist(),
            type=property_type,
            return_data_type='list' if (output_format is not None or output_is_list) else return_data_type,
            first_element=first_element if (output_format is None and not output_is_list) else False,
            **kwargs
        )
        _write_results(
            df,
            output,
            results,
            output_format,
            char,
            "json_list" if property_type else "json_dictionary",
            output_is_list
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
                char,
                "json_list" if property_type else "json_dictionary"
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
  char: str = ", "
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
          - list
          - columns
          - concatenate
      char:
        type: string
        description: Character to use when output_format is concatenate
    """
    # If output is not specified, overwrite input columns in place
    if output is None:
        output = input

    # Whether output was explicitly given as a list of column names
    output_is_list = isinstance(output, list) and len(output) > 1

    # If a string is provided, convert to list
    if not isinstance(input, list):
        input = [input]
    if not isinstance(output, list):
        output = [output]

    # Ensure input and output lengths are compatible
    if len(input) != len(output) and len(output) > 1 and not (len(input) == 1 and _is_columns_target(output, output_format, output_is_list)):
        raise ValueError('Extract must output to a single column or equal amount of columns as input.')

    _logging.debug(f": Extracting regex patterns :: input :: {input}")
    find_pattern = _re.compile(find)

    def _matches(value):
        value = str(value) if value is not None else ""
        matches = [match.group(0) for match in _re.finditer(find_pattern, value)]
        if output_pattern:
            matches = [find_pattern.sub(output_pattern, match) for match in matches]
        return matches

    def _write_regex(input_column, output_columns, columns_is_list=False):
        results = df[input_column].apply(_matches).tolist()
        if output_format is None and first_element and len(output_columns) == 1 and not columns_is_list:
            df[output_columns[0]] = [row[0] if len(row) >= 1 else "" for row in results]
        else:
            _write_list_output(df, output_columns, results, output_format, char, output_is_list=columns_is_list)

    if len(input) == 1 and _is_columns_target(output, output_format, output_is_list):
        _write_regex(input[0], output, output_is_list)
    else:
        # Loop through and apply for all columns
        for input_column, output_column in zip(input, output):
            _write_regex(input_column, [output_column])

    return df
