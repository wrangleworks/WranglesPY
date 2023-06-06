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
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(
            """
            wrangles:
              - custom.does_not_exists:
                  input: col
                  output: out
            """,
            dataframe = pd.DataFrame({
                'col':['Hello World']
            })
        )
    assert (
        info.typename == 'ValueError' and
        info.value.args[0] == 'Custom Wrangle function: "custom.does_not_exists" not found'
    )


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

def test_write():
    """
    Test using a custom function for write
    """
    def custom_funct_write(df, end_str):
        df['out1'] = df['out1'].apply(lambda x: x + end_str)
        return df

    data = pd.DataFrame({
        'col1': ['Hello', 'Wrangles']
    })
    recipe = """
    wrangles:
      - convert.case:
          input: col1
          output: out1
          case: upper
    write:
      - custom.custom_funct_write:
          end_str: ' Ending'
    """
    df = wrangles.recipe.run(recipe, dataframe=data, functions=[custom_funct_write])
    assert df.iloc[0]['out1'] == 'HELLO Ending'

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


def test_row_function():
    """
    Test a custom function that applies to an individual row
    """
    def add_numbers(val1, val2):
        return val1 + val2
    
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                val1: 1
                val2: 2
        wrangles:
          - custom.add_numbers:
              output: val3
        """,
        functions=[add_numbers]
    )
    assert df['val3'][0] == 3

def test_row_function_list_out():
    """
    Test a custom function that applies to an individual row with multi column outputs
    """
    def add_three(val1, val2):
        return [val1 + 3, val2 + 3]
    
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                val1: 1
                val2: 2
        wrangles:
          - custom.add_three:
              output:
                - val3
                - val4
        """,
        functions=[add_three]
    )
    assert df['val3'][0] == 4 and df['val4'][0] == 5

def test_pass_error():
    """
    Test using error argument for a custom run function
    to get access to the Exception when an error occurs
    """
    global test_var_pass_error
    test_var_pass_error = False

    def handle_error(error):
        if (type(error).__name__ == 'TypeError' and
            str(error) == "data type 'andksankdl' not understood"
        ):
            global test_var_pass_error
            test_var_pass_error = True

    with pytest.raises(Exception) as err:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: value

            wrangles:
            - convert.data_type:
                input: header
                data_type: andksankdl
            
            run:
              on_failure:
                - custom.handle_error: {}
            """,
            functions=[handle_error]
        )

    assert test_var_pass_error

def test_pass_error_with_params():
    """
    Test using error argument for a custom run function
    to get access to the Exception when an error occurs
    Also including user defined parameters.
    """
    global test_var_pass_error_params
    test_var_pass_error_params = False

    def handle_error(error, param):
        if (type(error).__name__ == 'TypeError' and
            str(error) == "data type 'andksankdl' not understood" and
            param == "value"
        ):
            global test_var_pass_error_params
            test_var_pass_error_params = True

    with pytest.raises(Exception) as err:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: value

            wrangles:
            - convert.data_type:
                input: header
                data_type: andksankdl
            
            run:
              on_failure:
                - custom.handle_error:
                    param: value
            """,
            functions=[handle_error]
        )

    assert test_var_pass_error_params

def test_error_not_passed():
    """
    Test that if a user doesn't request the error
    this is handled correctly.
    """
    global test_var_error_not_passed
    test_var_error_not_passed = False

    def handle_error():
        global test_var_error_not_passed
        test_var_error_not_passed = True

    with pytest.raises(Exception) as err:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: value

            wrangles:
            - convert.data_type:
                input: header
                data_type: andksankdl
            
            run:
              on_failure:
                - custom.handle_error: {}
            """,
            functions=[handle_error]
        )

    assert test_var_error_not_passed

def test_error_not_passed_with_params():
    """
    Test that if a user doesn't request the error
    this is handled correctly.
    Also including user defined parameters.
    """
    global test_var_error_not_passed_params
    test_var_error_not_passed_params = False

    def handle_error(param):
        if param == "value":
            global test_var_error_not_passed_params
            test_var_error_not_passed_params = True

    with pytest.raises(Exception) as err:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: value

            wrangles:
            - convert.data_type:
                input: header
                data_type: andksankdl
            
            run:
              on_failure:
                - custom.handle_error:
                    param: value
            """,
            functions=[handle_error]
        )

    assert test_var_error_not_passed_params

df_test_kwargs = pd.DataFrame({'ID': [1, 2, 3, 4, 5], 'Products': ['Hammer', 'Hex Nut', 'Pliers', 'Machine Screw', 'Socket'], 'Category': ['Tools', 'Hardware', 'Tools', 'Hardware', 'Tools']})

def test_empty_kwargs():
    """
    Test functionality when kwargs are empty
    """
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(Products, string, **kwargs):
        return Products + ' ' + string

    df = wrangles.recipe.run(recipe, dataframe=df_test_kwargs, functions=function)
    assert df.iloc[0]['Stuff'] == 'Hammer this is a string' and df.iloc[4]['Stuff'] == 'Socket this is a string'

def test_single_kwarg():
    """
    Test functionality with single kwarg
    """
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(Products, **kwargs):
        output = ''
        for value in kwargs.values():
            output += Products + ' ' + value
        return output
    df = wrangles.recipe.run(recipe=recipe, dataframe=df_test_kwargs, functions=function)
    assert df.iloc[0]['Stuff'] == 'Hammer this is a string' and df.iloc[4]['Stuff'] == 'Socket this is a string'

def test_multiple_kwargs():
    """
    Test functionality with multiple kwargs
    """
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string1: this
          string2: is
          string3: a
          string4: string
          output: Stuff
    """
    def function(Products, **kwargs):
        output = Products
        for value in kwargs.values():
            output += ' ' + value
        return output
    df = wrangles.recipe.run(recipe=recipe, dataframe=df_test_kwargs, functions=function)
    assert df.iloc[0]['Stuff'] == 'Hammer this is a string' and df.iloc[4]['Stuff'] == 'Socket this is a string'

def test_kwargs_input_error():
    """
    Test error when using input key as a variable instead of the input value
    """
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(input, string, **kwargs):
        return input + ' ' + string

    with pytest.raises(KeyError) as info:
        raise wrangles.recipe.run(recipe, df_test_kwargs, functions = function)
    
    assert (
        info.typename == 'KeyError' and
        info.value.args[0] == 'Column Products does not exist'
    )

def test_kwargs_output_error():
    """
    Test error when using output in custom function
    """
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(output, string, **kwargs):
        return output + ' ' + string

    with pytest.raises(TypeError) as info:
        raise wrangles.recipe.run(recipe, dataframe = df_test_kwargs, functions = function)
    
    assert (
        info.typename == 'TypeError' and
        info.value.args[0] == "test_kwargs_output_error.<locals>.function() missing 1 required positional argument: 'output'"
    )

def test_kwargs_dictionary_error():
    """
    Test error when using output in custom function
    """
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(string, **kwargs):
        return kwargs + ' ' + string

    with pytest.raises(TypeError) as info:
        raise wrangles.recipe.run(recipe, dataframe = df_test_kwargs, functions = function)
    
    assert (
        info.typename == 'TypeError' and
        info.value.args[0] == "unsupported operand type(s) for +: 'dict' and 'str'"
    )

