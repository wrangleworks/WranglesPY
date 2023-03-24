import wrangles
import pandas as pd
import pytest


# Files
## CSV
def test_import_csv():
    """
    Test a basic .csv import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.csv
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_txt():
    """
    Test a basic .txt import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.txt
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_csv_columns():
    """
    Test a csv import where user has selected only a subset of the columns
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.csv
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find']


## JSON
def test_import_json():
    """
    Test a basic .json import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.json
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_json_columns():
    """
    Test a json import where user has selected a subset of columns
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.json
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find']


## Excel
def test_import_excel():
    """
    Test a basic .xlsx import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.xlsx
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_excel_columns():
    """
    Test a basic .xlsx import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.xlsx
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find']   
    
## JSON Lines
def test_read_jsonl_file():
    recipe = """
    read:
      file:
        name: tests/samples/data.jsonl
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

# Write using index
def test_write_file_indexed():
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            case: lower
    write:
        file:
          name: tests/temp/write_data.xlsx
          index: true
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']
    
# Write using index
def test_write_file_indexed():
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            case: lower
    write:
        file:
          name: tests/temp/write_data.xlsx
          index: true
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']
    
# Write a json lines file
def test_write_file_jsonl():
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            case: lower
    write:
        file:
          name: tests/temp/write_data.jsonl
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']
    
# Testing recipe file input
def test_recipe_file_input():
  recipe = "tests/samples/recipe_sample.wrgl.yaml"
  config = {
    "inputFile": 'tests/samples/data.csv',
    "outputFile": 'tests/temp/write_data.xlsx'
  }
  df = wrangles.recipe.run(recipe, config)
  assert df.columns.tolist() == ['ID', 'Find2']
  
  
# Testing Union of multiple sources
def test_union_files():
    recipe = """
    read:
        - union:
            sources:
                - file:
                    name: tests/samples/data.xlsx
                - file:
                    name: tests/samples/data.csv
    write:
        - dataframe:
            columns:
                - Find
                - Replace
    """
    df = wrangles.recipe.run(recipe)
    assert len(df) == 6
    
# Testing Concatenate of multiple sources
def test_concatenate_files():
    recipe = """
    read:
        - concatenate:
            sources:
                - file:
                    name: tests/samples/data.xlsx
                - file:
                    name: tests/samples/data.csv
    write:
        - dataframe:
            columns:
                - Find
                - Replace
    """
    df = wrangles.recipe.run(recipe)
    assert len(df.columns.to_list()) == 4

# Testing join of multiple sources
def test_join_files():
    recipe = """
    read:
        - join:
            how: inner
            left_on: Find
            right_on: Find2
            sources:
                - file:
                    name: tests/samples/data.xlsx
                - file:
                    name: tests/samples/data2.xlsx
    """
    df = wrangles.recipe.run(recipe)
    assert len(df.columns.to_list()) == 4
    
# Custom Function
def test_custom_function_1():
    data = pd.DataFrame({
        'Col1': ['Hello One', 'Hello Two'],
    })
    def custom_func(df, input, output):
        second_token = []
        for x in range(len(df)):
            second_token.append(df[input][x].split()[1])
        df[output] = second_token
        return df
    recipe = """
    wrangle:
        - custom.custom_func:
            input: Col1
            output: Col2
            
        - convert.case:
            input: Col2
            output: Col3
    write:
        dataframe:
            columns:
                - Col1
                - Col2
    """
    df = wrangles.recipe.run(recipe, functions=[custom_func], dataframe=data)
    assert df.iloc[1]['Col2'] == 'Two'

# Custom Function no output specified
def test_custom_function_2():
    data = pd.DataFrame({
        'Col1': ['Hello One', 'Hello Two'],
    })
    def custom_func(df, input):
        second_token = []
        for x in range(len(df)):
            second_token.append(df[input][x].split()[1])
        df[input] = second_token
        return df
    recipe = """
    wrangles:
        - custom.custom_func:
            input: Col1
    write:
        dataframe:
            columns:
                - Col1
    """
    df = wrangles.recipe.run(recipe, functions=[custom_func], dataframe=data)
    assert df.iloc[1]['Col1'] == 'Two'
    

# Custom Function before wrangles
def test_custom_function_2():
    
    def custom_func():
        df = pd.DataFrame({
            'Col1': ['Hello One', 'Hello Two'],
        })
        return df
        
    recipe = """
    read:
        - custom.custom_func: {}
        
    wrangles:
        - convert.case:
            input: Col1
            case: upper
    write:
        dataframe:
            columns:
                - Col1
    """
    df = wrangles.recipe.run(recipe, functions=[custom_func])
    assert df.iloc[0]['Col1'] == 'HELLO ONE'


# If they've entered a list, get the first key and value from the first element
def test_input_is_list():
    recipe = """
    read:
        - file:
            name: tests/samples/data.xlsx
        
    """
    df = wrangles.recipe.run(recipe)
    assert len(df.columns.to_list()) == 2
    
# file not supported error message
def test_read_file_no_supported():
    recipe = """
    read:
      - file:
          name: data.jason
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert info.typename == 'ValueError' and info.value.args[0] == "File type 'jason' is not supported by the file connector."