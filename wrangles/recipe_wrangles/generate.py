
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
    **kwargs
)
    
    try:
       
        exploded_df = _pd.json_normalize(results, max_level=0).fillna('').set_index(df.index)

        for col in target_columns:
            if col not in exploded_df.columns:
                exploded_df[col] = ""

        if 'source' in exploded_df.columns and 'source' not in df.columns:
            df['source'] = exploded_df['source']
            
        df[target_columns] = exploded_df[target_columns]

    except Exception as e:
        raise RuntimeError(f"Unable to parse the response from the AI model. Error: {e}")

    return df    