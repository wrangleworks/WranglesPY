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

#
# To Dict
#


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
    assert df.iloc[0]['Dict Col'] == {'Col1': {'A'}, 'Col2': {'B'}}
    

#
# Key Value Pairs
#
df_key_value_pairs = pd.DataFrame({
    'Letter': ['A', 'B', 'C'],
    'Number': [1, 2, 3],
})

def test_key_value_pairs():
    recipe = """
    wrangles:
        - merge.key_value_pairs:
            input:
              Letter: Number
            output: Pairs
            
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_key_value_pairs)
    assert df.iloc[2]['Pairs'] == {'C': 3}

# Wildcard
df_key_value_pairs_wildcard = pd.DataFrame({
    'key 1': ['A', 'B', 'C'],
    'key 2': ['One', 'Two', 'three'],
    'value 1': ['a', 'b', 'c'],
    'value 2': ['First', 'Second', 'Third']
})

def test_key_value_pairs_wildcard():
    recipe = """
    wrangles:
        - merge.key_value_pairs:
            input:
              key*: value*
            output: Object
    """
    
    df = wrangles.pipeline.run(recipe, dataframe=df_key_value_pairs_wildcard)
    print(df.iloc[2]['Object'] == {'C': 'c', 'three': 'Third'})

