import wrangles
import pandas as pd
import re as _re
from fractions import Fraction as _Fraction


#
# CASE
#
def test_case_default():
    """
    Default value -> no case specified
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'a string'

def test_case_list():
    """
    Input is a list
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input:
            - Data1
            - Data2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'a string' and df.iloc[0]['Data2'] == 'another string'


def test_case_output():
    """
    Specifying output column
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          output: Column
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Column'] == 'a string'

def test_case_list_to_list():
    """
    Output and input are a multi columns
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input:
            - Data1
            - Data2
          output:
            - Column1
            - Column2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Column1'] == 'a string' and df.iloc[0]['Column2'] == 'another string'


def test_case_lower():
    """
    Test converting to lower case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: lower
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'a string'

def test_case_upper():
    """
    Test converting to upper case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: upper
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'A STRING'
    
def test_case_title():
    """
    Test converting to title case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: title
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'A String'

def test_case_sentence():
    """
    Test converting to sentence case
    """
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: sentence
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'A string'

#
# Data Type
#
def test_data_type_str():
    """
    Test converting to string data type
    """
    data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.data_type:
          input: Data1
          data_type: str
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert isinstance(df.iloc[0]['Data1'], str)


#
# JSON
#
def test_to_json_array():
    """
    Test converting to a list to a JSON array
    """
    data = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])
    recipe = """
    wrangles:
        - merge.to_list:
            input:
              - header1
              - header2
            output: headers
        - convert.to_json:
            input: headers
            output: headers_json
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['headers_json'] == '["val1", "val2"]'

def test_from_json_array():
    """
    Test converting to a JSON array to a list
    """
    data = pd.DataFrame([['["val1", "val2"]']], columns=['header1'])
    recipe = """
    wrangles:
        - convert.from_json:
            input: header1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert isinstance(df.iloc[0]['header1'], list)

#
# Convert to datetime
#

def test_convert_to_datetime():
    data = pd.DataFrame({
        'date': ['12/25/2050'],
    })
    recipe = """
    wrangles:
      - convert.data_type:
          input: date
          output: date_type
          data_type: datetime
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['date_type'].week == 51
    
#
# Fractions
#
def test_fraction_to_decimal():
    data = pd.DataFrame({
    'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
    })
    recipe = """
    wrangles:
      - convert.fraction_to_decimal:
          input: col1
          output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high"
