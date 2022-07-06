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
