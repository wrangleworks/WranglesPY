from asyncio import format_helpers
import wrangles
from datetime import date
import pandas as _pd
import json as _json
from typing import Union as _Union

# Custom Functions
# from functions import match_mro_parts
# from formatted_table import formatted_table

recipe = 'demoRecipe.wrgl.yml' # recipe file


def from_json(df: _pd.DataFrame, input: _Union[str, list], output: _Union[str, list] = None) -> _pd.DataFrame:
    """
    type: object
    description: Convert a JSON representation into an object
    additionalProperties: false
    required:
      - input
    properties:
      input:
        type: string
        description: Name of the input column.
      output:
        type: string
        description: Name of the output column. If omitted, the input column will be overwritten
    """
    # Set output column as input if not provided
    if output is None: output = input
    
    # If a string provided, convert to list
    if isinstance(input, str):
        input = [input]
        output = [output]
        
    # Loop through and apply for all columns
    for input_column, output_column in zip(input, output):
        df[output_column] = [_json.loads(x or "{}") for x in df[input_column]]
    
    return df

vars = {
    'inputFile': 'dewalt.xlsx',
    'inputSheet': 'data',
    'outputFile': 'dewalt wrangled.xlsx',
    'supplier': 'BOSCH',
 
    # MODELS
    'Remove Codes': 'b7ffd18f-0b96-48d6',
    'Item Extractor': '246aab17-32f1-4c00',
    'Family Classifier': '40949482-1baa-46d3',
    'Demo DIY Categories': '7241e660-ee32-436c',  
    'ObjectWrap': '1e63e3f0-f271-49ed',
    'Remove Brackets': '51ec7b7b-c01d-44a1',
    'Attributes': 'dbad4e67-f7ad-42d4',

    # Pricefx Connection
    'host': 'demo-us.demo1.pricefx.com',
    'partition': 'demofx-wrangleworks',
    'user': 'admin'
}

wrangles.recipe.run(recipe, variables=vars, functions= [from_json])