import wrangles
import pandas as pd


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
