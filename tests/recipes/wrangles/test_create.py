import wrangles
import pandas as pd
import pytest


#
# Column
#
def test_create_column_1():
    data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
    recipe = """
    wrangles:
        - create.column:
            output: column3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df.columns) == 3
    
# Adding a value from test connector
def test_create_columns_2():
    data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
    recipe = """
    wrangles:
        - create.column:
            output: column3
            value: <boolean>
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['column3'] in [True, False]
    
# Adding multiple columns with the same generated value
def test_create_columns_3():
    data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
    recipe = """
    wrangles:
        - create.column:
            output:
              - column3
              - column4
            value: <boolean>
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['column4'] in [True, False]
    
# Adding multiple columns with multiple generated values
def test_create_columns_4():
    data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
    recipe = """
    wrangles:
        - create.column:
            output:
              - column3
              - column4
            value:
              - <boolean>
              - <number(1-3)>
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['column4'] in [1, 2, 3, 4]
    
# if the output is a list with length one
def test_create_columns_5():
    data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
    recipe = """
    wrangles:
        - create.column:
            output:
              - column3
            value:
              - <boolean>
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['column3'] in [True, False]
    
def test_column_exists():
    """
    Check error if trying to create a column that already exists
    """
    data = pd.DataFrame({
      'col': ['data1']
    })
    recipe = """
    wrangles:
      - create.column:
          output: col
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == '"col" column already exists in dataFrame.'

def test_column_exists_list():
    """
    Check error if trying to create a list of columns where one already exists
    """
    data = pd.DataFrame({
      'col': ['data1']
    })
    recipe = """
    wrangles:
      - create.column:
          output:
            - col
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0].startswith("['col'] column(s)")

#
# Index
#
def test_create_index_1():
    data = pd.DataFrame([['one', 'two'], ['une', 'deux'], ['uno', 'dos']], columns=['column1', 'column2'])
    recipe = """
        wrangles:
            - create.index:
                output: index_col
                start: 1
                
        """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[-1]['index_col'] == 3

#
# GUID
#
def test_guid_1():
    data = pd.DataFrame({
    'Product': ['A', 'B'],
    })
    recipe = """
    wrangles:
        - create.guid:
            output: GUID Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert 'GUID Col' in list(df.columns)


#
# JINJA
#
def test_jinja_from_columns():
    """
    Tests functionality with template given as a string
    """
    data = pd.DataFrame({
        'type': ['phillips head', 'flat head'],
        'length': ['3 inch', '6 inch']
    })
    recipe = """
    wrangles:
      - create.jinja:
          output: description
          template: 
            string: This is a {{length}} {{type}} screwdriver
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'


def test_jinja_string_template():
    """
    Tests functionality with template given as a string
    """
    data = pd.DataFrame({
        'data column': [
            {'type': 'phillips head', 'length': '3 inch'},
            {'type': 'flat head', 'length': '6 inch'}
        ]
    })
    recipe = """
    wrangles:
      - create.jinja:
          input: data column
          output: description
          template: 
            string: "This is a {{length}} {{type}} screwdriver"
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

def test_jinja_column_template():
    """
    Tests functionality with templates in dataframe column
    """
    data = pd.DataFrame({
        'data column': [
            {'type': 'phillips head', 'length': '3 inch'},
            {'type': 'flat head', 'length': '6 inch'}
        ],
        'template column': [
            'This is a {{length}} {{type}} screwdriver',
            'This is a {{length}} {{type}} screwdriver'
        ]
    })
    recipe = """
    wrangles:
      - create.jinja:
          input: data column
          output: description
          template: 
            column: template column
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

def test_jinja_file_template():
    """
    Tests functionality with a template in a file
    """
    data = pd.DataFrame({
        'data column': [
            {'type': 'phillips head', 'length': '3 inch'},
            {'type': 'flat head', 'length': '6 inch'}
        ]
    })
    recipe = """
    wrangles:
      - create.jinja:
          input: data column
          output: description
          template: 
            file: tests/samples/jinjadescriptiontemplate.jinja
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

def test_jinja_multiple_templates():
    """
    Tests that the appropriate error message is shown when multiple templates are given
    """
    data = pd.DataFrame({
        'data column': [
            {'type': 'phillips head', 'length': '3 inch'},
            {'type': 'flat head', 'length': '6 inch'}
        ],
        'template column': [
            'This is a {{length}} {{type}} screwdriver',
            'This is a {{length}} {{type}} screwdriver'
        ]
    })
    recipe = """
    wrangles:
      - create.jinja:
          input: data column
          output: description
          template: 
            string: This is a {{length}} {{type}} screwdriver
            column: template column
    """
    with pytest.raises(Exception) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'Exception' and info.value.args[0] == 'Template must have only one key specified'

def test_jinja_no_template():
    """
    Tests that the appropriate error message is shown when no template is given
    """
    data = pd.DataFrame({
        'data column': [{'type': 'phillips head', 'length': '3 inch'}, {'type': 'flat head', 'length': '6 inch'}]
    })
    recipe = """
    wrangles:
      - create.jinja:
          input: data column
          output: description
    """
    with pytest.raises(TypeError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'TypeError' and info.value.args[0] == "jinja() missing 1 required positional argument: 'template'"

def test_jinja_unsupported_template_key():
    """
    Test that the appropriate error message is shown when template
    is passed a key other than 'file', 'string', 'column'
    """
    data = pd.DataFrame({
        'data column': [{'type': 'phillips head', 'length': '3 inch'}, {'type': 'flat head', 'length': '6 inch'}]
    })
    recipe = """
    wrangles:
      - create.jinja:
          input: data column
          output: description
          template:
            wrong: test
    """
    with pytest.raises(Exception) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'Exception' and info.value.args[0] == "'file', 'column' or 'string' not found"

def test_jinja_output_list():
    """
    Tests specifying the output as a list
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - create.jinja:
              input: data column
              output:
                - description
              template: 
                string: "This is a {{length}} {{type}} screwdriver"
        """,
        dataframe = pd.DataFrame({
            'data column': [
                {'type': 'phillips head', 'length': '3 inch'},
                {'type': 'flat head', 'length': '6 inch'}
            ]
        })
    )
    assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

def test_jinja_output_missing():
    """
    Check error if user doesn't specify output
    """
    with pytest.raises(TypeError) as info:
        wrangles.recipe.run(
            """
            wrangles:
            - create.jinja:
                input: data column
                template: 
                    string: "This is a {{length}} {{type}} screwdriver"
            """,
            dataframe = pd.DataFrame({
                'data column': [
                    {'type': 'phillips head', 'length': '3 inch'},
                    {'type': 'flat head', 'length': '6 inch'}
                ]
            })
        )
    assert (
        info.typename == 'TypeError' and
        info.value.args[0].startswith("jinja() missing")
    )

def test_jinja_variable_with_space():
    """
    Tests variable with a space
    """
    data = pd.DataFrame({
        'head type': ['phillips head', 'flat head'],
        'length': ['3 inch', '6 inch']
    })
    recipe = """
    wrangles:
      - create.jinja:
          output: description
          template: 
            string: This is a {{length}} {{head_type}} screwdriver
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'


#
# UUID
#
def test_uuid_1():
    data = pd.DataFrame({
    'Product': ['A', 'B'],
    })
    recipe = """
    wrangles:
        - create.uuid:
            output: UUID Col
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert 'UUID Col' in list(df.columns)
    
    
#
# Bins
#

def test_create_bins_1():
    data = pd.DataFrame({
        'col': [3, 13, 113]
    })
    recipe = """
    wrangles:
      - create.bins:
            input: col
            output: Pricing
            bins:
                - '-'
                - 10
                - 20
                - 50
                - 70
                - '+'
            labels:
                - 'under 10'
                - '10-20'
                - '20-40'
                - '40-70'
                - '100 and above'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Pricing'].iloc[0] == 'under 10'
