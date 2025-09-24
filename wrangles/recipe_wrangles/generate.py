
from typing import Union as _Union, Dict as _Dict, List as _List, Optional as _Optional
import pandas as _pd
import wrangles.generate as _generate



def ai(
    df: _pd.DataFrame,
    api_key: str,
    output: _Union[_Dict, str, _List],
    input: _Union[str, _List] = None,
    model: str = "gpt-5",
    threads: int = 20,
    timeout: int = 90,
    retries: int = 0,
    messages: _Optional[_List[dict]] = None,
    url: str = "https://api.openai.com/v1/responses",
    strict: bool = False,
    web_search: bool = False,
    reasoning: _Dict[str, str] = {"effort": "low"},
    **kwargs
) -> _pd.DataFrame:

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