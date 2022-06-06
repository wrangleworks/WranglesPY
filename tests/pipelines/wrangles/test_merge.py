import wrangles
import pandas as pd

#
# Coalesce
#
df_test_coalesce = pd.DataFrame(
    {
        'Col1': ['A', '', ''],
        'Col2': ['', 'B', ''],
        'Col3': ['', '', 'C']
    }
)
def test_coalesce():
    recipe = """
    wrangles:
    - merge.coalesce:
        input: 
        - Col1
        - Col2
        - Col3
        output: Output Col
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_coalesce)
    assert df['Output Col'].values.tolist() == ['A', 'B', 'C']

#
# Concatenate
#
df_test_concatenate_one_col = pd.DataFrame(
    {
        'Col1': [['A', 'B', 'C']]
    }
)
def test_concatenate_one_col():
    recipe = """
    wrangles:
        - merge.concatenate:
            input: Col1
            output: Join List
            char: ' '
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_concatenate_one_col)
    assert df.iloc[0]['Join List'] == 'A B C'
    

df_test_coalesce_multi_cols = pd.DataFrame(
    {
        'Col1': ['A'],
        'Col2': ['B'],
        'Col3': ['C']
    }
)
def test_coalesce_multi_cols():
    recipe = """
    wrangles:
        - merge.concatenate:
            input: 
                - Col1
                - Col2
                - Col3
            output: Join Col
            char: ', '
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_coalesce_multi_cols)
    assert df.iloc[0]['Join Col'] == 'A, B, C'
    
#
# Lists
#
df_test_join_lists = pd.DataFrame(
    {
        'Col1': [['A', 'B']],
        'Col2': [['D', 'E']]
    }
)
def test_join_lists():
    recipe = """
    wrangles:
        - merge.lists:
            input: 
                - Col1
                - Col2
            output: Combined Col
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_join_lists)
    print(df.iloc[0]['Combined Col'] == ['A', 'B', 'D', 'E'])


#
# to_list
#
df_test_to_lists = pd.DataFrame(
    {
        'Col1': ['A'],
        'Col2': ['B'],
        'Col3': ['C']
    }
)

def test_to_lists():
    recipe = """
    wrangles:
        - merge.to_list:
            input: 
                - Col1
                - Col2
                - Col3
            output: Combined Col
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_to_lists)
    assert df.iloc[0]['Combined Col'] == ['A', 'B', 'C']
    

df_test_to_dict = pd.DataFrame({
    'Col1':[{'A'}],
    'Col2':[{'B'}]
})

def test_to_dict():
    recipe = """
    wrangles:
        - merge.to_dict:
            input: 
                - Col1
                - Col2
            output: Dict Col
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_to_dict)
    assert df.iloc[0]['Dict Col'] == {'Col1': 'A', 'Col2': 'B'}

