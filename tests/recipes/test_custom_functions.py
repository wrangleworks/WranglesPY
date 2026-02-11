"""
Test custom functions that are passed to recipes
"""
import wrangles
from wrangles.connectors import memory
import pandas as pd
import pytest


def test_function_not_found():
    """
    Test that if a custom function isn't found
    that the user gets a relevant error message
    """
    with pytest.raises(ValueError, match="does_not_exist not recognized"):
        wrangles.recipe.run(
            """
            wrangles:
              - custom.does_not_exist:
                  input: col
                  output: out
            """,
            dataframe = pd.DataFrame({
                'col':['Hello World']
            })
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
            "data_type andksankdl is not supported" in str(error)
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
            "data_type andksankdl is not supported" in str(error) and
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

def test_df_at_end_of_variables():
    """
    Test functionality when df is placed at the end of the function variables
    """
    recipe = """
    read:
      - test:
          rows: 2
          values:
            ID: 1
            Products: Hammer
            Category: Tools
    
    wrangles:
      - custom.function:
          input: Products
          output: Stuff
    """
    def function(input, output, df):
        df[output] = df[input] + ' sold out'
        return df

    dfNew = wrangles.recipe.run(recipe, functions=function)
    assert dfNew['Stuff'][0] == 'Hammer sold out'

def test_df_at_beginning_of_variables():
    """
    Test functionality when df is placed at the beginning of the function variables
    """
    recipe = """
    read:
      - test:
          rows: 2
          values:
            ID: 1
            Products: Hammer
            Category: Tools
    
    wrangles:
      - custom.function:
          input: Products
          output: Stuff
    """
    def function(df, input, output):
        df[output] = df[input] + ' sold out'
        return df

    dfNew = wrangles.recipe.run(recipe, functions=function)
    assert dfNew['Stuff'][0] == 'Hammer sold out'

def test_empty_kwargs():
    """
    Test functionality when kwargs are empty
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(Products, string, **kwargs):
        return Products + ' ' + string

    df = wrangles.recipe.run(recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer this is a string' and df.iloc[1]['Stuff'] == 'Hex Nut this is a string'

def test_single_kwarg():
    """
    Test functionality with single kwarg
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
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
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer this is a string'

def test_multiple_kwargs():
    """
    Test functionality with multiple kwargs
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
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
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer this is a string'

def test_kwargs_user_requires_input():
    """
    Test if the user requests input as a function parameter
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(input, string, **kwargs):
        return kwargs[input] + ' ' + string
    
    df = wrangles.recipe.run(recipe, dataframe = df, functions = function)
    assert df['Stuff'][0] == 'Hammer this is a string'

def test_kwargs_output_error():
    """
    Test error when using output in custom function
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(output, string, **kwargs):
        return output + ' ' + string
    
    df = wrangles.recipe.run(recipe, dataframe = df, functions = function)
    assert df['Stuff'][0] == 'Stuff this is a string'

def test_kwargs_dictionary_error():
    """
    Test error when using kwargs as a string instead of a dictionary
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
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
        raise wrangles.recipe.run(recipe, dataframe = df, functions = function)
    
    assert (
        info.typename == 'TypeError' and
        "unsupported operand type(s) for +: 'dict' and 'str'" in info.value.args[0]
    )

def test_kwargs_only():
    """
    Test functionality when using only kwargs
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(**kwargs):
        outputString = ''
        for value in kwargs.values():
            outputString += value
        return outputString

    df = wrangles.recipe.run(recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammerthis is a string' and df.iloc[1]['Stuff'] == 'Hex Nutthis is a string'

def test_not_kwargs():
    """
    Test functionality when using **notkwargs in place of **kwargs
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          output: Stuff
    """
    def function(**notkwargs):
        outputString = ''
        for value in notkwargs.values():
            outputString += value
        return outputString

    df = wrangles.recipe.run(recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammerthis is a string'

def test_kwargs_with_list():
    """
    Test functionality when using a list in kwargs
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          strings: 
            - this is a string
            - so is this
            - this is also a string
          output: Stuff
    """
    def function(**kwargs):
        outputString = ''
        for value in kwargs.values():
            for i in range(len(value)):
                outputString += value[i]
        return outputString

    df = wrangles.recipe.run(recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammerthis is a stringso is thisthis is also a string'

def test_regex_with_kwargs():
    """
    Test functionality using regex in the input
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: "regex:P[a-z]*s"
          string: this is a string
          output: Stuff
    """
    def function(Products, **kwargs):
        output = ''
        for value in kwargs.values():
            output += Products + ' ' + value
        return output
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer this is a string' and df.iloc[1]['Stuff'] == 'Hex Nut this is a string'

def test_wildcard_with_kwargs():
    """
    Test functionality using a wildcard
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Product*
          string: this is a string
          output: Stuff
    """
    def function(Products, **kwargs):
        output = ''
        for value in kwargs.values():
            output += Products + ' ' + value
        return output
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer this is a string'

def test_kwargs_no_input():
    """
    Test functionality without a specified input
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          string: this is a string
          output: Stuff
    """
    def function(**kwargs):
        output = ''
        for value in kwargs.values():
            output += str(value)
        return output
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == '1HammerToolsthis is a string'

def test_kwargs_with_parameters():
    """
    Test Functionality of kwargs with parameters
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          string: this is a string
          parameters: things
          output: Stuff
    """
    def function(parameters, **kwargs):
        output = ''
        for value in kwargs.values():
            output += str(value) + parameters
        return output
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammerthingsthis is a stringthings'

def test_parameters():
    """
    Test functionality using parameters 
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          parameters: parameter
          output: Stuff
    """
    def function(Products, parameters):
        string = Products
        string += ' ' + parameters
        return string
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer parameter'

def test_parameters_list():
    """
    Test functionality using a list of parameters 
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          parameters: 
            - parameter1
            - parameter2
          output: Stuff
    """
    def function(Products, parameters):
        string = Products
        for parameter in parameters:
            string += ' ' + parameter
        return string
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer parameter1 parameter2'

def test_parameters_not_in_function_args():
    """
    Test functionality using a list of parameters 
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products            
          parameter1: my_first_param
          parameter2: my_second_param
          parameter3: my_third_param 
          output: Stuff
    """
    def function(Products, parameter3):
        return Products + ' ' + parameter3
    df = wrangles.recipe.run(recipe=recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] == 'Hammer my_third_param'

def test_parameters_input_error():
    """
    Tests error when using input incorrectly
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          parameters: parameter
          output: Stuff
    """
    def function(input, parameters):
        return input + ' ' + parameters
    
    df = wrangles.recipe.run(recipe, dataframe = df, functions = function)
    assert df['Stuff'][0] == 'Products parameter'

def test_parameters_output_error():
    """
    Test error when using output incorrectly
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          input: Products
          parameters: this is a string
          output: Stuff
    """
    def function(output, parameters):
        return output + ' ' + parameters
    
    df = wrangles.recipe.run(recipe, dataframe = df, functions = function)
    assert df['Stuff'][0] == 'Stuff this is a string'

def test_parameters_only():
    """
    Test error when using only parameters
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          parameters: 
            - parameter1
            - parameter2
          output: Stuff
    """
    def function(parameters):
        outputString = ''
        for parameter in parameters:
            outputString += parameter
        return outputString

    df = wrangles.recipe.run(recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] =='parameter1parameter2'

def test_no_function_variables():
    """
    Test functionality when no variables are given to the function
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          output: Stuff
    """
    def function():
        outputString = 'Placeholder string'
        return outputString

    df = wrangles.recipe.run(recipe, dataframe=df, functions=function)
    assert df['Stuff'][0] =='Placeholder string'

def test_no_function_variables_output_list():
    """
    Test functionality when no variables are given to the function
    """
    df = pd.DataFrame({'ID': [1, 2], 'Products': ['Hammer', 'Hex Nut'], 'Category': ['Tools', 'Hardware']})
    recipe = """
    wrangles:
      - custom.function:
          output: 
            - Stuff1
            - Stuff2
    """
    def function():
        outputString = 'Placeholder string'
        return outputString

    df = wrangles.recipe.run(recipe, dataframe=df, functions=function)
    assert df['Stuff1'][0] =='Placeholder string' and df['Stuff2'][0] =='Placeholder string'

def test_kwargs_with_input():
    """
    Test functionality of kwargs when a function is given an input
    """
    recipe = '''
    read:
    - test:
        rows: 5
        values:
            id: 1
            description: my desc
            heading1: value1
            heading2: value2
            heading3: value3

    wrangles:
    - custom.test_fn:
        output: results
        input:
            - id
            - heading*
        my_parameter: my_value
    '''

    def test_fn(my_parameter, id, heading1, **kwargs):
        my_string = str(id) + heading1
        for kwarg in kwargs:
            my_string += kwarg
        return my_string
    
    df = wrangles.recipe.run(recipe, functions=test_fn)
    assert df['results'][0] =='1value1heading2heading3'

def test_kwargs_with_output_list_single_column():
    """
    Test functionality of kwargs when outputting a list to a single column
    """
    recipe = '''
    read:
    - test:
        rows: 5
        values:
            id: 1
            description: my desc
            heading1: value1
            heading2: value2
            heading3: value3

    wrangles:
    - custom.test_fn:
        output: results
        input:
            - id
            - heading*
        my_parameter: my_value
    '''

    def test_fn(my_parameter, id, heading1, **kwargs):
        # return my_parameter + heading1
        my_list = list(kwargs.values()) + [my_parameter]
        return my_list

    df = wrangles.recipe.run(recipe, functions=test_fn)
    assert df['results'][0] == ['value2', 'value3', 'my_value']

def test_kwargs_with_output_list_multiple_columns():
    """
    Test functionality of kwargs when outputting a list multiple columns
    """
    recipe = '''
    read:
    - test:
        rows: 5
        values:
            id: 1
            description: my desc
            heading1: value1
            heading2: value2
            heading3: value3

    wrangles:
    - custom.test_fn:
        output: 
          - results1
          - results2
          - results3
        input:
            - id
            - heading*
        my_parameter: my_value
    '''

    def test_fn(my_parameter, id, heading1, **kwargs):
        my_list = list(kwargs.values()) + [my_parameter]
        return my_list
    
    df = wrangles.recipe.run(recipe, functions=test_fn)
    assert df['results1'][0] == 'value2' and df['results2'][0] == 'value3' and df['results3'][0] == 'my_value'

def test_output_list_single_column_without_kwargs():
    """
    Test functionality of kwargs when outputting a list to a single column
    """
    recipe = '''
    read:
    - test:
        rows: 5
        values:
            id: 1
            description: my desc
            heading1: value1
            heading2: value2
            heading3: value3

    wrangles:
    - custom.test_fn:
        output: results
        input:
            - id
            - heading*
        my_parameter: my_value
    '''

    def test_fn(my_parameter, id, heading1):
        return [my_parameter, id, heading1]
    
    df = wrangles.recipe.run(recipe, functions=test_fn)
    assert df['results'][0] == ['my_value', 1, 'value1']

def test_output_list_multiple_columns_without_kwargs():
    """
    Test functionality of kwargs when outputting a list to a single column
    """
    recipe = '''
    read:
    - test:
        rows: 5
        values:
            id: 1
            description: my desc
            heading1: value1
            heading2: value2
            heading3: value3

    wrangles:
    - custom.test_fn:
        output: 
          - results1
          - results2
          - results3
        input:
            - id
            - heading*
        my_parameter: my_value
    '''

    def test_fn(my_parameter, id, heading1):
        return [my_parameter, id, heading1]
    
    df = wrangles.recipe.run(recipe, functions=test_fn)
    assert df['results1'][0] == 'my_value' and df['results2'][0] == 1 and df['results3'][0] == 'value1'

def test_column_spaces():
    """
    Test functionality when passing column names with spaces
    """
    recipe = '''
    read:
      - test:
          rows: 5
          values:
            id: 123
            my description: this is a

    wrangles:
      - custom.space_function:
          suffix: description
          output: New Description
    '''
    
    def space_function(my_description, suffix):
        return my_description + ' ' + suffix
    
    df = wrangles.recipe.run(recipe, functions=space_function)
    assert df['New Description'][0] == 'this is a description'

def test_column_spaces_in_kwargs():
    """
    Test functionality when passing a column with a space through kwargs
    """
    recipe = '''
    read:
      - test:
          rows: 5
          values:
            id: 123
            my description: this is a

    wrangles:
      - custom.space_function:
          suffix: description
          output: New Description
    '''
    def space_function(**kwargs):
        return kwargs['my description'] + ' ' + kwargs['suffix']
    
    df = wrangles.recipe.run(recipe, functions=space_function)
    assert df['New Description'][0] == 'this is a description'

def test_row_function_where():
    """
    Test a custom function that applies to an
    individual row using where
    """
    def add_numbers(val1, val2):
        return val1 + val2
    
    df = wrangles.recipe.run(
        """
        wrangles:
          - custom.add_numbers:
              output: val3
              where: val1 >= 3
        """,
        functions=[add_numbers],
        dataframe=pd.DataFrame({
            "val1": [1,2,3],
            "val2": [2,4,6]
        })
    )
    assert df['val3'][0] == "" and df['val3'][2] == 9

def test_row_function_double_where():
    """
    Test a custom function that applies to an
    individual row using two where conditions
    for different rows
    """
    def add_numbers(val1, val2):
        return val1 + val2
    def subtract_numbers(val1, val2):
        return val2 - val1
    df = wrangles.recipe.run(
        """
        wrangles:
          - custom.add_numbers:
              output: val3
              where: val1 >= 3

          - custom.subtract_numbers:
              output: val3
              where: val1 = 1
        """,
        functions=[add_numbers, subtract_numbers],
        dataframe=pd.DataFrame({
            "val1": [1,2,3],
            "val2": [2,4,6]
        })
    )
    assert (
        df['val3'][0] == 1 and
        df['val3'][1] == "" and
        df['val3'][2] == 9
    )

def test_user_not_returned_dataframe_wrangle():
    """
    Check error returned if a user's custom function
    does not return a dataframe correctly
    """
    def wrangle_stuff(df):
        pass

    with pytest.raises(RuntimeError) as info:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1

            wrangles:
            - custom.wrangle_stuff: {}
            """,
            functions=wrangle_stuff
        )
    assert (
        info.typename == 'RuntimeError' and
        "did not return a dataframe" in info.value.args[0]
    )

def test_user_not_returned_dataframe_read():
    """
    Check error returned if a user's custom function
    does not return a dataframe correctly
    """
    def wrangle_stuff():
        pass

    with pytest.raises(RuntimeError) as info:
        raise wrangles.recipe.run(
            """
            read:
            - custom.wrangle_stuff: {}
            """,
            functions=wrangle_stuff
        )
    assert (
        info.typename == 'RuntimeError' and
        "did not return a dataframe" in info.value.args[0]
    )

def test_model_with_custom_functions():
    """
    Test a model that includes custom functions
    """
    df = wrangles.recipe.run("42f319a8-0849-4177")
    assert (
        df['header1'][0] == "value1" and
        df['header2'][0] == "value2" and
        df['header3'][0] == "VALUE2"
    )

def test_local_takes_priority():
    """
    Ensure a locally passed custom function overrides
    a remote function of the same name
    """
    def convert_case(header2: str):
        return header2.title()

    df = wrangles.recipe.run(
        "42f319a8-0849-4177",
        functions=convert_case
    )
    assert (
        df['header1'][0] == "value1" and
        df['header2'][0] == "value2" and
        df['header3'][0] == "Value2"
    )

def test_from_file():
    """
    Test getting custom functions from a file path
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
        
        wrangles:
          - custom.convert_to_upper:
              input: header1
              output: header2
        """,
        functions="tests/samples/custom_functions.py"
    )
    assert df['header2'][0] == "VALUE1"

class TestVariableFunctions:
    """
    Test using custom functions to define variables
    """
    def test_variable_function(self):
        """
        Test a function that does not have any arguments
        """
        def func():
            return 5

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: ${key}
                values:
                    header1: value1
            """,
            variables={
                "key": "custom.func"
            },
            functions=func
        )

        assert len(df) == 5

    def test_kwargs(self):
        """
        Test a function that uses kwargs
        """
        def func(key1, **kwargs):
            if key1 != 5:
                raise ValueError("Invalid key1")
            if kwargs["key2"] != 6:
                raise ValueError("Invalid key2")
            if "key1" in kwargs:
                raise ValueError("key2 should not be in kwargs")
            return 5

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: ${key}
                values:
                    header1: value1
            """,
            variables={
                "key": "custom.func",
                "key1": 5,
                "key2": 6
            },
            functions=func
        )
        assert len(df) == 5

    def test_arg_default(self):
        """
        Test a function that has a default
        value for an argument
        """
        def func(key1, key2 = 1):
            return key1 + key2

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: ${key}
                values:
                    header1: value1
            """,
            variables={
                "key": "custom.func",
                "key1": 5
            },
            functions=func
        )
        assert len(df) == 6

    def test_arg_default_only(self):
        """
        Test a function that only has
        an argument with a default
        """
        def func(key1 = 5):
            return key1

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: ${key}
                values:
                    header1: value1
            """,
            variables={
                "key": "custom.func"
            },
            functions=func
        )
        assert len(df) == 5

    def test_nested_function(self):
        """
        Test referencing a nested custom function
        """
        class nested:
            def func():
                return 5

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: ${key}
                values:
                    header1: value1
            """,
            variables={
                "key": "custom.nested.func"
            },
            functions=nested
        )
        assert len(df) == 5

    def test_named_variable(self):
        """
        Test referencing a variable as a named parameter
        """
        def func(named_var):
            return named_var + 1

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: ${key}
                values:
                    header1: value1
            """,
            variables={
                "key": "custom.func",
                "named_var": 5
            },
            functions=func
        )
        assert len(df) == 6

    def test_variable_arg(self):
        """
        Test a function that uses
        the variables argument
        """
        def func(variables):
            return variables["var"] + 1

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: ${key}
                values:
                    header1: value1
            """,
            variables={
                "var": 5,
                "key": "custom.func"
            },
            functions=func
        )
        assert len(df) == 6

    def test_variable_function_invalid_args(self):
        """
        Test a custom function for variables
        that does not have the correct arguments
        gives a clear error message
        """
        def func(a, b):
            return 5

        with pytest.raises(ValueError, match="requires arguments"):
            raise wrangles.recipe.run(
                """
                read:
                - test:
                    rows: ${key}
                    values:
                        header1: value1
                """,
                variables={
                    "key": "custom.func"
                },
                functions=func
            )


def test_clear_errors_df():
    """
    Test a dataframe level custom function raises a clear error message
    """
    def raise_error(df):
        raise RuntimeError("This is an error")

    with pytest.raises(RuntimeError, match="custom.raise_error - at line 8 - This is an error"):
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 5
                  values:
                    header1: value1
            wrangles:
                - custom.raise_error: {}
            """,
            functions=raise_error
        )

def test_clear_errors_row_output_missing():
    """
    Test a row level custom function raises a clear error message
    """
    def raise_error(header1):
        raise RuntimeError("This is an error")

    with pytest.raises(ValueError, match="Must set 1 or more output columns"):
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 5
                  values:
                    header1: value1
            wrangles:
                - custom.raise_error: {}
            """,
            functions=raise_error
        )

def test_clear_errors_row():
    """
    Test a row level custom function raises a clear error message
    """
    def raise_error(header1):
        raise RuntimeError("This is an error")

    with pytest.raises(RuntimeError, match="This is an error"):
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 5
                  values:
                    header1: value1
            wrangles:
                - custom.raise_error:
                    output: temp
            """,
            functions=raise_error
        )

def test_clear_errors_read():
    """
    Test a row level custom function raises a clear error message
    """
    def raise_error():
        raise RuntimeError("This is an error")

    with pytest.raises(RuntimeError, match="custom.raise_error - at line 3 - This is an error"):
        wrangles.recipe.run(
            """
            read:
              - custom.raise_error: {}
            """,
            functions=raise_error
        )

def test_clear_errors_write():
    """
    Test a row level custom function raises a clear error message
    """
    def raise_error(df):
        raise RuntimeError("This is an error")

    with pytest.raises(RuntimeError, match="custom.raise_error - at line 3 - This is an error"):
        wrangles.recipe.run(
            """
            write:
              - custom.raise_error: {}
            """,
            functions=raise_error
        )

class nested:
    def read():
        return pd.DataFrame({
            "header": ["value"]
        })
    
    def wrangle(df, input):
        df[input] = df[input] + "1"
        return df

    def write(df, id):
        memory.dataframes[id] = df

    def run(id, value):
        memory.variables[id] = value

def test_nested_read():
    """
    Test a nested custom function for read
    """
    df = wrangles.recipe.run(
        """
        read:
          - custom.nested.read: {}
        """,
        functions=nested
    )
    assert df['header'][0] == "value"

def test_nested_wrangle():
    """
    Test a nested custom function for wrangles
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        wrangles:
          - custom.nested.wrangle:
              input: header
        """,
        functions=nested
    )
    assert df['header'][0] == "value1"

def test_nested_write():
    """
    Test a nested custom function for write
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        write:
          - custom.nested.write:
              id: test_nested_write
        """,
        functions=nested
    )
    assert memory.dataframes["test_nested_write"]["header"][0] == "value"

def test_nested_run():
    """
    Test a nested custom function for run
    """
    df = wrangles.recipe.run(
        """
        run:
          on_start:
            - custom.nested.run:
                id: test_nested_run
                value: value
        """,
        functions=nested
    )
    assert memory.variables["test_nested_run"] == "value"

def test_common_param_access():
    """
    Test that a custom function can access common parameters
    """
    def common_param_access(df, input, where):
        if len(df) != 2:
            raise ValueError("Dataframe not the correct length")
        if where != "header > 3":
            raise ValueError("Where condition not met")
        if input != "header":
            raise ValueError("Input not correct")
        df[input] = df[input] * 2
        return df

    df = wrangles.recipe.run(
        """
        wrangles:
          - custom.common_param_access:
              input: header
              where: header > 3
        """,
        functions=common_param_access,
        dataframe=pd.DataFrame({"header": [1,2,3,4,5], "header2": [5,4,3,2,1]})
    )
    assert df['header'][4] == 10 and df["header"][0] == 1

def test_wrangle_position_error():  
    """  
    Test that error messages include wrangle position number  
    when multiple identical wrangles exist  
    """  
    def raise_error(df):  
        raise RuntimeError("This is an error")  
      
    with pytest.raises(RuntimeError, match="ERROR IN WRANGLE #1 custom.raise_error - at line 8 - This is an error"):  
        wrangles.recipe.run(  
            """  
            read:  
              - test:  
                  rows: 5  
                  values:  
                    header1: value1  
            wrangles:  
                - custom.raise_error: {}  
                - convert.case:  
                    input: header1  
                    output: temp  
                    case: upper  
                - custom.raise_error: {}  
            """,  
            functions=raise_error  
        )  

def test_wrangle_position_error_2():  
    """  
    Test that error messages include wrangle position number  
    when multiple identical wrangles exist  
    """  
    def raise_error(df):  
        raise RuntimeError("This is an error")  
      
    with pytest.raises(RuntimeError, match="ERROR IN WRANGLE #2 custom.raise_error - at line 17 - This is an error"):  
        wrangles.recipe.run(  
            """  
            read:  
              - test:  
                  rows: 5  
                  values:  
                    header1: value1  
            wrangles:  
                - convert.case:  
                    input: header1  
                    output: temp  
                    case: upper  
                - custom.raise_error: {}  
                - convert.case:  
                    input: header1  
                    output: temp  
                    case: lower  
                - custom.raise_error: {}  
            """,  
            functions=raise_error  
        )  
  
def test_wrangle_position_multiple_same_type():  
    """  
    Test error reporting with multiple wrangles of same type  
    """  
    with pytest.raises(TypeError, match="ERROR IN WRANGLE #2 convert.data_type - at line 12 - data_type invalid_type is not supported."):  
        wrangles.recipe.run(  
            """  
            read:  
              - test:  
                  rows: 5  
                  values:  
                    header1: value1  
            wrangles:  
                - convert.data_type:  
                    input: header1  
                    output: temp1  
                    data_type: str  
                - convert.data_type:  
                    input: header1  
                    output: temp2  
                    data_type: invalid_type  
            """  
        )

def test_complete_error_reporting_flow():  
    """  
    Test complete error reporting with nested batch and multiple wrangles  
    """  
    def batch_error(df):  
        if len(df) > 5:  
            raise RuntimeError("Batch too large")  
        return df  
      
    with pytest.raises(RuntimeError, match="ERROR IN WRANGLE #2 batch - Batch #1 - ERROR IN WRANGLE #1 custom.batch_error - at line 2 - Batch too large"):  
        wrangles.recipe.run(  
            """  
            read:  
              - test:  
                  rows: 20  
                  values:  
                    header1: value1  
            wrangles:  
                - convert.case:  
                    input: header1  
                    output: temp  
                    case: upper  
                - batch:  
                    batch_size: 10  
                    wrangles:  
                        - custom.batch_error: {}  
                        - convert.case:  
                            input: header1  
                            case: lower  
                - convert.case:  
                    input: header1  
                    output: final  
                    case: title  
            """,  
            functions=batch_error  
        )