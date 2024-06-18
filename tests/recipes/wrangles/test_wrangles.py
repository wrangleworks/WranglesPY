"""
Test generic wrangles functionality, not specific
to an individual wrangle
"""
import wrangles
import pandas as pd
import numpy as np
import pytest


def test_double_where_input():
    """
    Test using multiple where on different rows
    overwriting the input
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = 1

          - convert.case:
              input: col2
              case: lower
              where: col1 = 2 
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'world'


def test_empty_double_where_input():
    """
    Test using multiple empty where on different rows
    overwriting the input
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = 3

          - convert.case:
              input: col2
              case: lower
              where: col1 = 4 
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['col2'][0] == 'HeLlO' and df['col2'][1] == 'WoRlD'


def test_double_where_output():
    """
    Test using multiple where on different rows
    with an output column
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              output: results
              case: upper
              where: col1 = 1

          - convert.case:
              input: col2
              output: results
              case: lower
              where: col1 = 2 
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['results'][0] == 'HELLO' and df['results'][1] == 'world'

def test_empty_output_double_where_output():
    """
    Test using multiple empty where on different rows
    with an output column
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              output: results
              case: upper
              where: col1 = 3

          - convert.case:
              input: col2
              output: results
              case: lower
              where: col1 = 3 
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['results'][0] == '' and df['results'][1] == ''

def test_where_params():
    """
    Test using using a parameterized query
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = ?
              where_params:
                - 1
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'WoRlD'

def test_empty_where_params():
    """
    Test using using a parameterized query
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = ?
              where_params:
                - 0
                
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['col2'][0] == 'HeLlO' and df['col2'][1] == 'WoRlD'

def test_where_params_dict():
    """
    Test using using a parameterized query with dict
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = :key
              where_params:
                key: 1
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'WoRlD'

def test__empty_where_params_dict():
    """
    Test using using a parameterized query with dict that is empty
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = :key
              where_params:
                key: 0
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        })
    )
    assert df['col2'][0] == 'HeLlO' and df['col2'][1] == 'WoRlD'

def test_where_params_variable():
    """
    Test using using a parameterized query
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = ?
              where_params:
                - ${var}
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        }),
        variables={'var': 1}
    )
    assert df['col2'][0] == 'HELLO' and df['col2'][1] == 'WoRlD'

def test_empty_where_params_variable():
    """
    Test using using a parameterized query
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = ?
              where_params:
                - ${var}
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
        }),
        variables={'var': 4}
    )
    assert df['col2'][0] == 'HeLlO' and df['col2'][1] == 'WoRlD'

def test_where_unsupported_sql_type():
    """
    Test using a value that isn't supported by SQL
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - convert.case:
              input: col2
              case: upper
              where: col1 = 1
        """,
        dataframe= pd.DataFrame({
            'col1': [1, 2],
            'col2': ['HeLlO', 'WoRlD'],
            "col3": [np.array([1,2,3]), np.array([4,5,6])]
        }),
        variables={'var': 1}
    )
    assert (
        type(df["col3"][0]).__name__ == "ndarray" and
        list(df["col3"][0]) == [1,2,3]
    )

def test_where_data_types_preserved():
    """
    Test that data types are preserved when using where
    """
    df = wrangles.recipe.run(
        """
        wrangles:
        - math:
            input: (Column2 - Column1)/Column1
            output: Column3
            where: NULLIF(Column1, '') IS NOT NULL
        """,
        dataframe= pd.DataFrame({
            'Column1': [65, 72, '', 92, 87, 79],
            'Column2': [2, 5, 4, 2, 1, 6]
        })
    )
    assert (
        df["Column1"].values.tolist() == [65, 72, '', 92, 87, 79] and
        df["Column3"][2] == ""
    )

def test_where_empty_case_df():
    """
    Test using where on an empty dataframe
    """
    data=pd.DataFrame({
            'col1': ['1', '0', '1', '0', '1'],
            'col2': ['python', 'java', 'sql', 'r', 'c++'],
        })
    df = wrangles.recipe.run(
        """
        wrangles:
            - convert.case:
                input: col2
                case: upper
                where: col1 = 2
        """,
        dataframe=data
        
    )
    assert df.equals(data)

def test_where_empty_output_case_df():
    """
    Test using where on an empty dataframe
    """
    data=pd.DataFrame({
            'col1': ['1', '0', '1', '0', '1'],
            'col2': ['python', 'java', 'sql', 'r', 'c++'],
        })
    expected_df = pd.DataFrame({
            'col1': ['1', '0', '1', '0', '1'],
            'col2': ['python', 'java', 'sql', 'r', 'c++'],
            'output': ['','','','','']
        })
    df = wrangles.recipe.run(
        """
        wrangles:
            - convert.case:
                input: col2
                output: output
                case: upper
                where: col1 = 2
        """,
        dataframe=data
        
    )
    assert df.equals(expected_df)

def test_where_empty_prefix_df():
    """
    Test using where on an empty dataframe
    """
    data=pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python', 'java', 'sql', 'r', 'c++'],
    })
    df = wrangles.recipe.run(
        """
        wrangles:
            - format.prefix:
                input: col2
                value: test-
                where: col1 = 2
        """,
        dataframe=data
    )
    assert df.equals(data)

def test_where_empty_suffix_df():
    """
    Test using where on an empty dataframe
    """
    data = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python', 'java', 'sql', 'r', 'c++'],
    })
    df = wrangles.recipe.run(
        """
        wrangles:
            - format.suffix:
                input: col2
                value: test-
                where: col1 = 2
        """,
        dataframe=data
    )
    assert df.equals(data)

def test_where_empty_output_suffix_df():
    """
    Test using where on an empty dataframe
    """
    data = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python', 'java', 'sql', 'r', 'c++'],
        'output': ['','','','','']
    })
    df = wrangles.recipe.run(
        """
        wrangles:
            - format.suffix:
                input: col2
                output: output
                value: test-
                where: col1 = 2
        """,
        dataframe=data
    )
    assert df.equals(data)

def test_where_pad_df():
    """
    Test using where on an empty dataframe
    """
    data = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python', 'java', 'sql', 'r', 'c++'],
    })
    expected_df = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python', 'java', 'sql', 'r', 'c++'],
    })
    df = wrangles.recipe.run(
        """
        wrangles:
            - format.prefix:
                input: col2
                side: right
                char: ~
                where: col1 = 2
        """,
        dataframe=data
    )
    assert df.equals(expected_df)

def test_empty_split_where_df():
    """
    Test using multiple where on different rows
    """
    data = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python, best', 'java, worst', 'sql, medicore', 'r, worst', 'c++, best'],
    })
    expected_df = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python, best', 'java, worst', 'sql, medicore', 'r, worst', 'c++, best'],
        'output': ['','','','','']
    })
    df = wrangles.recipe.run(
        """
        wrangles:
            - split.text:
                input: col2
                output: output
                char: ', '
                where: col1 = 2
            
        """,
        dataframe=data
    )
    
    assert df.equals(expected_df)

def test_empty_mutli_where_df():
    """
    Test using multiple where on different rows
    """
    data = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python, best', 'java, worst', 'sql, medicore', 'r, worst', 'c++, best'],
    })
    expected_df = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python, best', 'java, worst', 'sql, medicore', 'r, worst', 'c++, best'],
        'output': ['','','','','']
    })
    df = wrangles.recipe.run(
        """
        wrangles:
            - split.text:
                input: col2
                output: output
                char: ', '
                where: col1 = 2
            
        """,
        dataframe=data
    )

    assert df.equals(expected_df)

def test_empty_mutli_output_where_df():
    """
    Test using multiple where on different rows
    """
    data = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python, best', 'java, worst', 'sql, medicore', 'r, worst', 'c++, best'],
    })
    expected_df = pd.DataFrame({
        'col1': ['1', '0', '1', '0', '1'],
        'col2': ['python, best', 'java, worst', 'sql, medicore', 'r, worst', 'c++, best'],
        'output1': ['','','','',''],
        'output2': ['','','','','']
    })
    df = wrangles.recipe.run(
        """
        wrangles:
            - split.text:
                input: col2
                output: 
                    - output1
                    - output2
                char: ', '
                where: col1 = 2
            
        """,
        dataframe=data
    )

    assert df.equals(expected_df)

def test_where_empty_case_df():
    """
    Test using where on an empty dataframe
    """
    data=pd.DataFrame({
            'col1': ['1', '0', '1', '0', '1'],
            'col2': ['python', 'java', 'sql', 'r', 'c++'],
        })
    expected_df = pd.DataFrame({
            'col1': ['1', '0', '1', '0', '1'],
            'col2': ['python', 'java', 'sql', 'r', 'c++'],
            'output': ['','','','',''],
        })
    df = wrangles.recipe.run(
        """
        wrangles:
            - convert.case:
                input: col2
                output: output
                case: upper
                where: col1 = 2

            - format.prefix:
                input: col2
                value: test-
                where: col1 = 2
        """,
        dataframe=data
        
    )
    assert df.equals(expected_df)

def test_classify_where():
    """
    Test classify using where
    """
    data = pd.DataFrame({
    'Col1': ['Ball Bearing', 'Roller Bearing'],
    'Col2': ['Ball Bearing', 'Needle Bearing'],
    'number': [25, 31]
    })
    expected_df = pd.DataFrame({
    'Col1': ['Ball Bearing', 'Roller Bearing'],
    'Col2': ['Ball Bearing', 'Needle Bearing'],
    'number': [25, 31],
    'Class1': ['',''],
    'Class2': ['','']
    })
    recipe = """
    wrangles:
        - classify:
            input: 
              - Col1
              - Col2
            output: 
              - Class1
              - Class2
            model_id: c77839db-237a-476b
            where: number < 25
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.equals(expected_df)

def test_filter_where():
    data = pd.DataFrame({
        'Random': ['Apples', 'None', 'App', None],
    })
    recipe = """
    wrangles:
        - filter:
            where: Random = 'NOT Apples'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 0

def test_filter_where_params():
    """
    Test a parameterized where condition
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - filter:
              where: Random = ?
              where_params:
                - NOT Apples
        """,
        dataframe= pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
    )
    assert len(df) == 0

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
              where: val1 >= 30
        """,
        functions=[add_numbers],
        dataframe=pd.DataFrame({
            "val1": [1,2,3],
            "val2": [2,4,6]
        })
    )
    assert df['val3'][0] == "" and df['val3'][2] == ""

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
              where: val1 >= 30

          - custom.subtract_numbers:
              output: val3
              where: val1 = 10
        """,
        functions=[add_numbers, subtract_numbers],
        dataframe=pd.DataFrame({
            "val1": [1,2,3],
            "val2": [2,4,6]
        })
    )
    assert (
        df['val3'][0] == "" and
        df['val3'][1] == "" and
        df['val3'][2] == ""
    )