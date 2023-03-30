"""
Test variables that are passed to recipes

Variables are defined in the form ${my_variable}
"""
import wrangles
import pandas as pd
import pytest
import platform


# recipe as a templated value
def test_templated_values_1():
    case_var = "upper"
    inputs = ['col', 'col2']
    templated_rec = """
        convert.case:
          input:
            ${inputs}
          output:
            - out
            - out2
          case: ${case_value}
    """
    data = pd.DataFrame({
        'col': ['Hello World'],
        'col2': ['hello world'],
    })
    recipe = """
    wrangles:
      - ${wrgl1}
    """
    vars = {
        'wrgl1': templated_rec,
        'case_value': case_var,
        'inputs': inputs,
    }
    df = wrangles.recipe.run(recipe, variables=vars, dataframe=data)
    assert df.iloc[0]['out'] == "HELLO WORLD"
    
    
# templated value in a sql command
def test_templated_values_2():
    data = pd.DataFrame({
        'col': ['Hello SQL']
    })
    templated_sql = """
    SELECT * from df
    """
    recipe = """
    wrangles:
      - sql: 
          command: ${sql_command}
    """
    vars = {
        "sql_command": templated_sql,
    }
    df = wrangles.recipe.run(recipe, variables=vars, dataframe=data)
    assert 1

def test_templated_valued_3():
    data = pd.DataFrame({
        'col': ['Hello World']
    })
    templated_case = "case"
    vars = {
        "tmpl_value": templated_case
    }
    recipe = """
    wrangles:
      - convert.case:
          input: col
          output: out
          ${tmpl_value}: upper
    """
    df = wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert df.iloc[0]['out'] == 'HELLO WORLD'
 

def test_within_string():
    """
    Test that a variable within a string works.
    Test at start, middle and end.
    """
    recipe = """
    read:
      - test:
          rows: 1
          values:
            col1: value-${var}
            col2: ${var}-value
            col3: value-${var}-value
    """
    df = wrangles.recipe.run(recipe, variables={'var': '1'})
    assert (
        df.iloc[0]['col1'] == 'value-1'
        and df.iloc[0]['col2'] == '1-value'
        and df.iloc[0]['col3'] == 'value-1-value'
    )

def test_within_string_integer():
    """
    Test that a variable within a string works.
    Test at start, middle and end.
    Test with a non-string type.
    """
    recipe = """
    read:
      - test:
          rows: 1
          values:
            col1: value-${var}
            col2: ${var}-value
            col3: value-${var}-value
    """
    df = wrangles.recipe.run(recipe, variables={'var': 1})
    assert (
        df.iloc[0]['col1'] == 'value-1'
        and df.iloc[0]['col2'] == '1-value'
        and df.iloc[0]['col3'] == 'value-1-value'
    )

def test_json():
    """
    Test that a variable passed in 
    as JSON is interpreted correctly
    """
    recipe = """
    read:
      - test:
          rows: 1
          values: ${json}
    """
    df = wrangles.recipe.run(
        recipe,
        variables={'json': '{"col1":"value1","col2":"value2"}'}
    )
    assert (
        df.iloc[0]['col1'] == 'value1'
        and df.iloc[0]['col2'] == 'value2'
    )

def test_similar_to_json():
    """
    Test that a variable passed 
    in that looks like JSON but isn't
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                column1: ${not_json}
        """,
        variables={'not_json': '{{something}}'}
    )
    assert df['column1'][0] == '{{something}}'

# USER OMITS VARIABLES
def test_missing_error():
    """
    Test that the user gets a sensible error message
    if they've specified a variable that is not found
    """
    recipe = """
    read:
      - file:
          name: ${missing}
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert (
        info.typename == 'ValueError' 
        and info.value.args[0] == 'Variable ${missing} was not found.'
    )

def test_missing_within_string_error():
    """
    Test that the user gets a sensible error message
    if they've specified a variable that is not found
    where the variable is within a string
    """
    recipe = """
    read:
      - file:
          name: file-${missing}.xlsx
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert (
        info.typename == 'ValueError' 
        and info.value.args[0] == 'Variable ${missing} was not found.'
    )


def test_passed_as_parameter():
    """
    Test that a variable passed as
    a parameter is accessed correctly
    """
    recipe = """
    read:
      - test:
          rows: 1
          values:
            header: ${var}
    """
    df = wrangles.recipe.run(
        recipe,
        variables={'var': 'value'}
    )
    assert df.iloc[0]['header'] == 'value'


def test_passed_as_environment_variable():
    """
    Test that a variable passed as an
    environment variable is accessed correctly
    """
    if platform.system() == 'Windows':
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${USERNAME}
        """
    else:
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${USER}
        """

    df = wrangles.recipe.run(recipe)
    assert len(df.iloc[0]['header']) > 0


def test_parameter_overrides_environment():
    """
    Test that a variable passed as
    a parameter overrides one that exists
    as an environment variable
    """
    if platform.system() == 'Windows':
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${USERNAME}
        """
    else:
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${USER}
        """
    df = wrangles.recipe.run(
        recipe,
        variables={'USER':'success', 'USERNAME':'success'}
    )
    assert df.iloc[0]['header'] == 'success'