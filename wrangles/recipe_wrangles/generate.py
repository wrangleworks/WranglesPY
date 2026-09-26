
from typing import Union as _Union, Dict as _Dict, List as _List, Optional as _Optional
import logging as _logging
import pandas as _pd
import wrangles.generate as _generate
from .. import ai_config as _ai_config



def ai(
    df: _pd.DataFrame,
    api_key: str,
    output: _Union[_Dict, str, _List],
    input: _Union[str, _List] = None,
    model: str = None,
    threads: int = None,
    timeout: int = None,
    retries: int = None,
    messages: _Optional[_List[dict]] = None,
    url: str = None,
    strict: bool = None,
    web_search: bool = False,
    reasoning: _Dict[str, str] = None,
    previous_response: bool = False,
    summary: bool = False,
    **kwargs
) -> _pd.DataFrame:
    """
    type: object
    description: Generate structured AI output for each recipe row.
    additionalProperties: false
    required:
      - api_key
      - output
    properties:
      api_key:
        type: string
        description: OpenAI-compatible API key.
      input:
        type:
          - string
          - array
        description: Column(s) to concatenate into the prompt (defaults to all columns).
      output:
        type:
          - string
          - object
          - array
        description: Target schema; string/array shorthands are expanded automatically.
      model:
        type: string
        description: Responses model name. Defaults to the generate.ai role in the AI configuration.
      threads:
        type: integer
        description: Maximum concurrent requests; defaults to the AI configuration.
      timeout:
        type: integer
        description: Per-request timeout in seconds.
      retries:
        type: integer
        description: Number of retry attempts on failure.
      messages:
        type: array
        description: The first message's content overrides the generation instructions.
      url:
        type: string
        description: Override for the OpenAI-compatible endpoint.
      strict:
        type: boolean
        description: Enforce JSON-schema validation on the response.
      web_search:
        type: boolean
        description: Enable DuckDuckGo context lookup per row.
      reasoning:
        type: object
        description: Responses API reasoning options, checked against configured model capabilities.
      examples:
        type: array
        description: Few-shot examples with input, output, and optional notes.
      previous_response:
        type: boolean
        description: Chain responses by reusing previous_response_id for field-by-field calls.
      summary:
        type: boolean
        description: Request summary text to be merged into the output.
    """
    if strict is None:
        strict = _ai_config.resolve("generate.ai", model=model)["recipe_strict"]
    _logging.info(f": Generating AI output :: model :: {model}, thread_count :: {threads}")
    if input is not None:
        if not isinstance(input, list):
            input = [input]
        df_temp = df[input]
    else:
        df_temp = df

    output_schema = output
    if isinstance(output_schema, str):
        output_schema = {output_schema: {"description": f"Generated content for {output_schema}"}}
    elif isinstance(output_schema, list):
        temp_dict = {}
        for item in output_schema:
            temp_dict[str(item)] = {"description": f"Generated content for {str(item)}"}
        output_schema = temp_dict

    target_columns = list(output_schema.keys())

    final_schema = {
        "type": "object",
        "properties": output_schema,
        "required": target_columns,
        "additionalProperties": False
    }



    recipe_examples = None
    example_alias = None
    for key in ("Example", "Examples", "example", "examples"):
        if key in kwargs:
            if example_alias is not None:
                raise ValueError("generate.ai accepts one examples argument; use the canonical 'examples' name.")
            example_alias = key
            recipe_examples = kwargs.pop(key)

    results = _generate.ai(
        input=df_temp.to_dict(orient='records'),
        api_key=api_key,
        output=final_schema,
        model=model,
        threads=threads,
        timeout=timeout,
        retries=retries,
        messages=messages,
        url=url,
        strict=strict,
        web_search=web_search,
        reasoning=reasoning,
        previous_response=previous_response,
        examples=recipe_examples,
        summary=summary,
        
        **kwargs
    )

    try:

        exploded_df = _pd.json_normalize(results, max_level=0).fillna('').set_index(df.index)

        for col in target_columns:
            if col not in exploded_df.columns:
                exploded_df[col] = ""

        if 'source' in exploded_df.columns and 'source' not in df.columns:
            df['source'] = exploded_df['source']

        if summary and 'summary' in exploded_df.columns:
            df["summary"] = exploded_df['summary']

        df[target_columns] = exploded_df[target_columns]

    except Exception as e:
        raise RuntimeError(f"Unable to parse the response from the AI model. Error: {e}")

    return df
