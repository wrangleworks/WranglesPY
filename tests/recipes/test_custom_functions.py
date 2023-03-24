"""
Test custom functions that are passed to recipes
"""
import wrangles
import pandas as pd
import pytest


def test_function_not_found():
    """
    Test that if a custom function isn't found
    that the user gets a relevant error message
    """
    data = pd.DataFrame({
        'col':['Hello World']
    })
    recipe = """
    wrangles:
      - custom.does_not_exists:
          input: col
          output: out
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Custom Wrangle function: "custom.does_not_exists" not found'


def test_run():
    """
    Test passing custom function to the run section
    """
    def fail_func(input):
        better_data = pd.DataFrame({
            'col111': [input],
        })
        return better_data

    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    recipe = """
    run:
      on_success:
        custom.fail_func:
          input: Hello Wrangles
        
      wrangles:
        - convert.case:
            input: col1
            output: out
            case: upper
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[fail_func])
    assert df.iloc[0]['col1'] == 'hello world'


def test_read():
    """
    Test passing a custom function to the read section
    """
    def func():
        return pd.DataFrame({'col1': ['hello world']})

    recipe = """
      read:
        - custom.func: {}
    """
    df = wrangles.recipe.run(recipe, functions=[func])

    assert df.iloc[0]['col1'] == 'hello world'


def test_wrangle():
    """
    Test passing a custom function to the wrangles section
    """
    def func(df):
        df = df.head(5)
        return df

    recipe = """
      read:
        - test:
            rows: 10
            values:
              header1: test
      wrangles:
        - custom.func: {}
    """
    df = wrangles.recipe.run(recipe, functions=[func])

    assert len(df) == 5


def test_no_parameters():
    """
    Test passing a custom function that does not include parameters
    e.g. custom.func: {}
    """
    def func():
        return pd.DataFrame({'col1': ['hello world']})

    recipe = """
      read:
        - custom.func: {}
    """
    df = wrangles.recipe.run(recipe, functions=[func])

    assert df.iloc[0]['col1'] == 'hello world'

def test_with_parameters():
    """
    Test passing a custom function that does include parameters
    e.g. custom.func:
           value: hello world
    """
    def func(value):
        return pd.DataFrame({'col1': [value]})

    recipe = """
      read:
        - custom.func:
            value: hello world
    """
    df = wrangles.recipe.run(recipe, functions=[func])

    assert df.iloc[0]['col1'] == 'hello world'

def test_custom_function():
    def my_function(df, input, output):
        df[output] = df[input].apply(lambda x: x[::-1])
        return df

    data = pd.DataFrame({'col1': ['Reverse Reverse']})
    recipe = """
    wrangles:
        - custom.my_function:
            input: col1
            output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[my_function])

    assert df.iloc[0]['out1'] == 'esreveR esreveR'
    

def test_custom_function_cell():
    # using cell as args[0]
    def my_function(cell):    
        return str(cell) + ' xyz'

    data = pd.DataFrame({'col1': ['Reverse Reverse']})
    recipe = """
    wrangles:
        - custom.my_function:
            input: col1
            output: out1
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[my_function])

    assert df.iloc[0]['out1'] == 'Reverse Reverse xyz'
    
def test_custom_function_cell_2():
    # not mentioning output ->  using cell as args[0]
    def my_function(cell):    
        return str(cell) + ' xyz'

    data = pd.DataFrame({'col1': ['Reverse Reverse']})
    recipe = """
    wrangles:
        - custom.my_function:
            input: col1
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[my_function])

    assert df.iloc[0]['col1'] == 'Reverse Reverse xyz'