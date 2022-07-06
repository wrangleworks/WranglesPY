import wrangles
import pandas as pd


#
# CASE
#
# Default value -> no case specified
def test_case_1():
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Data1'] == 'a string'

# Input is a list
def test_case_2():
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

# Specifying output column
def test_case_3():
    data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          output: Column
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Column'] == 'a string'

# Output and input are a multi columns
def test_case_4():
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

# Testing Lower case
def test_case_lower():
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
# To JSON
#
def test_to_json_array():
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