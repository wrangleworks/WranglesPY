import wrangles
import pandas as pd
import pytest

#
# Dictionary Element
#
def test_dictionary_element_1():
    data = pd.DataFrame({
    'Prop': [{'colours': ['red', 'white', 'blue'], 'shapes': 'round', 'materials': 'tungsten'}]
    })
    recipe = """
    wrangles:
      - select.dictionary_element:
          input: Prop
          output: Shapes
          element: shapes
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Shapes'] == 'round'
    
# if the input is multiple columns (a list)
def test_dictionary_element_2():
    data = pd.DataFrame({
    'Prop1': [{'colours': ['red', 'white', 'blue'], 'shapes': 'round', 'materials': 'tungsten'}],
    'Prop2': [{'colours': ['red', 'white', 'blue'], 'shapes': 'ROUND', 'materials': 'tungsten'}]
    })
    recipe = """
    wrangles:
      - select.dictionary_element:
          input:
            - Prop1
            - Prop2
          output:
            - Shapes1
            - Shapes2
          element: shapes
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Shapes2'] == 'ROUND'
    
# if the input and output are not the same type
def test_dictionary_element_3():
    data = pd.DataFrame({
    'Prop1': [{'colours': ['red', 'white', 'blue'], 'shapes': 'round', 'materials': 'tungsten'}],
    'Prop2': [{'colours': ['red', 'white', 'blue'], 'shapes': 'ROUND', 'materials': 'tungsten'}]
    })
    recipe = """
    wrangles:
      - select.dictionary_element:
          input:
            - Prop1
            - Prop2
          output: Shapes1
          element: shapes
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        "The list of inputs and outputs must be the same length for select.dictionary_element" in info.value.args[0]
    )

def test_dictionary_elem_default():
    """
    Test user defined default value
    """
    data = pd.DataFrame({
    'Col1': [{'A': '1', 'B': '2'}],
    })
    recipe = """
    wrangles:
      - select.dictionary_element:
          input: Col1
          output: Out
          element: C
          default: '3'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'][0] == '3'

def test_dictionary_element_where():
    """
    Test select.dictionary_element using where
    """
    data = pd.DataFrame({
    'Prop': [{'colours': ['red', 'white', 'blue'], 'shapes': 'round', 'materials': 'tungsten'},
             {'colours': ['green', 'gold', 'yellow'], 'shapes': 'square', 'materials': 'titanium'},
             {'colours': ['orange', 'purple', 'black'], 'shapes': 'triangular', 'materials': 'aluminum'}],
    'numbers': [3, 6, 10]
    })
    recipe = """
    wrangles:
      - select.dictionary_element:
          input: Prop
          output: Shapes
          element: shapes
          where: numbers > 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Shapes'] == 'square' and df.iloc[0]['Shapes'] == ''

#
# List Element
#
def test_list_element_1():
    data = pd.DataFrame({
    'Col1': [['A', 'B', 'C']]
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Second Element
          element: 1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Second Element'] == 'B'
    
# Empty values
def test_list_element_2():
    data = pd.DataFrame({
    'Col1': [['A One', '', 'C']],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Second Element
          element: 1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Second Element'] == ''
    
# Out of Index values
def test_list_element_3():
    data = pd.DataFrame({
    'Col1': [['A One']],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Second Element
          element: 5
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Second Element'] == ''
    
# if the input is multiple columns (a list)
def test_list_element_4():
    data = pd.DataFrame({
    'Col1': [['A One', 'A Two']],
    'Col2': [['Another here']],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: 
            - Col1
            - Col2
          output:
            - Out1
            - Out2
          element: 1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Out1'] == 'A Two'
    
# if the input and output are not the same type
def test_list_element_5():
    data = pd.DataFrame({
    'Col1': [['A One', 'A Two']],
    'Col2': [['Another here']],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: 
            - Col1
            - Col2
          output: Out1
          element: 1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        "The list of inputs and outputs must be the same length for select.list_element" in info.value.args[0]
    )

def test_list_element_where():
    """
    Test list element using where
    """
    data = pd.DataFrame({
        'Col1': [['A', 'B', 'C'], ['D', 'E', 'F'], ['G', 'H', 'I']],
        'numbers': [0, 4, 8]
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Second Element
          element: 1
          where: numbers != 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Second Element'] == 'B' and df.iloc[1]['Second Element'] ==''
    
def test_list_elem_default_string():
    """
    Test default to be a string
    """
    data = pd.DataFrame({
    'Col1': [['A'], [], 'C'],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Out
          element: 0
          default: 'None'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].values.tolist() == ['A', 'None', 'C']
    
def test_list_elem_default_list():
    """
    Test default to be a empty list
    """
    data = pd.DataFrame({
    'Col1': [[['A']], [], [['C']]],
    })
    recipe = """
    wrangles:
      - select.list_element:
          input: Col1
          output: Out
          element: 0
          default: []
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].values.tolist() == [['A'], [], ['C']]
    
    
#
# Highest confidence
#
def test_highest_confidence_1():
    data = pd.DataFrame({
    'Col1': [['A', .79]],
    'Col2': [['B', .80]],
    'Col3': [['C', .99]]
    })
    recipe = """
    wrangles:
      - select.highest_confidence:
          input:
            - Col1
            - Col2
            - Col3
          output: Winner
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Winner'] == ['C', 0.99]
    
# Test the output when using a list of two columns
def test_highest_confidence_list_output():
    """
    Tests the output when using a list of two columns
    """
    data = pd.DataFrame({
    'Col1': [['A', .79]],
    'Col2': [['B', .80]],
    'Col3': [['C', .99]]
    })
    recipe = """
    wrangles:
      - select.highest_confidence:
          input:
            - Col1
            - Col2
            - Col3
          output: 
            - Winner
            - Confidence
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Winner'] == 'C' and df.iloc[0]['Confidence'] == 0.99

def test_highest_confidence_where():
    """
    Test select.highest_confidence using where
    """
    data = pd.DataFrame({
    'Col1': [['A', .79], ['D', .88], ['G', .97]],
    'Col2': [['B', .80], ['E', .33], ['H', .15]],
    'Col3': [['C', .99], ['F', .89], ['I', .98]],
    'numbers': [7, 8, 9]
    })
    recipe = """
    wrangles:
      - select.highest_confidence:
          input:
            - Col1
            - Col2
            - Col3
          output: Winner
          where: numbers > 7
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Winner'] == ['F', .89] and df.iloc[0]['Winner'] == ''

#
# Threshold
#
def test_threshold_1():
    data = pd.DataFrame({
    'Col1': [['A', .60]],
    'Col2': [['B', .79]]
    })
    recipe = """
    wrangles:
      - select.threshold:
          input:
            - Col1
            - Col2
          output: Top Words
          threshold: .77
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B'
    
# Noun (Token) return empty aka None
def test_threshold_2():
    data = pd.DataFrame({
    'Col1': [None],
    'Col2': ['B || .90']
    })
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B || .90'
    
# Noun (Token) return empty aka None and cell 2 is a list
def test_threshold_3():
    data = pd.DataFrame({
    'Col1': [None],
    'Col2': [['B || .90']]
    })
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B || .90'
    
# Cell_1[0] is above the threshold
def test_threshold_4():
    data = pd.DataFrame({
    'Col1': [['A', .90]],
    'Col2': [['B', .79]]
    })
    recipe = """
    wrangles:
      - select.threshold:
          input:
            - Col1
            - Col2
          output: Top Words
          threshold: .77
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'A'
    
def test_threshold_5():
    data = pd.DataFrame({
    'Col1': ['A || .50'],
    'Col2': ['B || .90']
    })
    recipe = """
    wrangles:
        - select.threshold:
            input:
                - Col1
                - Col2
            output: Top Words
            threshold: .77
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Top Words'] == 'B || .90'

def test_threshold_where():
    """
    Test select.threshold using where
    """
    data = pd.DataFrame({
    'Col1': [['A', .60], ['C', .88], ['E', .98]],
    'Col2': [['B', .79], ['D', .97], ['F', .11]],
    'numbers': [7, 9, 11]
    })
    recipe = """
    wrangles:
      - select.threshold:
          input:
            - Col1
            - Col2
          output: Top Words
          threshold: .77
          where: numbers >= 9
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Top Words'] == 'C' and df.iloc[0]['Top Words'] == ''
    
#    
# Left
#
# Multi Columns input and output
def test_left_1():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.left:
            input:
                - Col1
                - Col2
            output:
                - Out1
                - Out2
            length: 5
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Out1'] == 'One T'
    
# Output is none
def test_left_2():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.left:
            input: Col1
            length: 5
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == 'One T'

def test_left_where():
    """
    Test slect.left using where
    """
    data = pd.DataFrame({
        'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
        'numbers': [6, 7, 8]
    })
    recipe = """
    wrangles:
        - select.left:
            input: Col1
            output: Out1
            length: 5
            where: numbers = 7
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Out1'] == 'Five ' and df.iloc[0]['Out1'] == ''

# Test the error with a list of inputs and a single output
def test_left_multi_input_single_output():
    """
    Test the error when using a list of input columns and a single output column
    """
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.left:
            input: 
              - Col1
              - Col2
            output: out1
            length: 5
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        "The lists for input and output must be the same length." in info.value.args[0]
    )
    
#
# Right
#
# Multi column
def test_right_1():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.right:
            input:
                - Col1
                - Col2
            output:
                - Out1
                - Out2
            length: 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Out1'] == 'Four'
    
# Output is none
def test_right_2():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.right:
            input: Col1
            length: 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == 'Four'
    
# Test the error with a list of inputs and a single output
def test_right_multi_input_single_output():
    """
    Test the error when using a list of input columns and a single output column
    """
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.right:
            input: 
              - Col1
              - Col2
            output: out1
            length: 5
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        "The lists for input and output must be the same length." in info.value.args[0]
    )

def test_right_where():
    """
    Test select.right using where
    """
    data = pd.DataFrame({
        'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
        'numbers': [6, 7, 8]
    })
    recipe = """
    wrangles:
        - select.right:
            input: Col1
            output: Out1
            length: 6
            where: numbers > 6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[2]['Out1'] == 'Twelve' and df.iloc[0]['Out1'] == ''
    
#
# Substring
#

# Multi column input
def test_substring_1():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.substring:
            input:
                - Col1
                - Col2
            output:
                - Out1
                - Out2
            start: 4
            length: 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Out1'] == ' Two'
    
# Output is none
def test_substring_2():
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.substring:
            input: Col1
            start: 4
            length: 4
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Col1'] == ' Two'

# Test the error with a list of inputs and a single output
def test_substring_multi_input_single_output():
    """
    Test the error when using a list of input columns and a single output column
    """
    data = pd.DataFrame({
    'Col1': ['One Two Three Four'],
    'Col2': ['A B C D']
    })
    recipe = """
    wrangles:
        - select.substring:
            input: 
              - Col1
              - Col2
            output: out1
            start: 4
            length: 4
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        "The lists for input and output must be the same length." in info.value.args[0]
    )

def test_substring_where():
    """
    Test select.substring using where
    """
    data = pd.DataFrame({
        'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
        'numbers': [6, 7, 8]
    })
    recipe = """
    wrangles:
        - select.substring:
            input: Col1
            output: Out1
            start: 5
            length: 4
            where: numbers = 8
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[2]['Out1'] == ' Ten' and df.iloc[0]['Out1'] == ''

def test_group_by():
    """
    Test basic group by
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by: agg
              sum: sum_me
              min: min_me
              max: max_me
        """,
        dataframe=pd.DataFrame({
            "agg": ["a", "a", "a", "b"],
            "min_me": [1,2,3,4],
            "max_me": [1,2,3,4],
            "sum_me": [1,2,3,4]
        })
    )

    assert (
        list(df.values[0]) == ['a', 6, 1, 3] and
        list(df.values[1]) == ['b', 4, 4, 4]
    )

def test_group_by_multiple_by():
    """
    Test group by with multiple by
    columns specified
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by:
                - agg1
                - agg2
              sum: sum_me
              min: min_me
              max: max_me
        """,
        dataframe=pd.DataFrame({
            "agg1": ["a", "a", "a", "b"],
            "agg2": ["a", "a", "b", "b"],
            "min_me": [1,2,3,4],
            "max_me": [1,2,3,4],
            "sum_me": [1,2,3,4]
        })
    )

    assert (
        list(df.values[0]) == ['a', 'a', 3, 1, 2] and
        list(df.values[1]) == ['a', 'b', 3, 3, 3] and
        list(df.values[2]) == ['b', 'b', 4, 4, 4]
    )

def test_group_by_without_by():
    """
    Test group by with only aggregations
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              sum: sum_me
              min: min_me
              max: max_me
        """,
        dataframe=pd.DataFrame({
            "agg": ["a", "a", "a", "b"],
            "min_me": [1,2,3,4],
            "max_me": [1,2,3,4],
            "sum_me": [1,2,3,4]
        })
    )

    assert list(df.values[0]) == [10, 1, 4]

def test_group_by_without_aggregations():
    """
    Test group by without any aggregations
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by: agg
        """,
        dataframe=pd.DataFrame({
            "agg": ["a", "a", "a", "b"],
            "min_me": [1,2,3,4],
            "max_me": [1,2,3,4],
            "sum_me": [1,2,3,4]
        })
    )

    assert (
        list(df.values[0]) == ['a'] and
        list(df.values[1]) == ['b']
    )

def test_group_by_agg_lists():
    """
    Test with multiple aggregations
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by: agg
              sum:
                - sum_me
                - and_sum_me
        """,
        dataframe=pd.DataFrame({
            "agg": ["a", "a", "a", "b"],
            "sum_me": [1,2,3,4],
            "and_sum_me": [5,6,7,8]
        })
    )

    assert (
        list(df.values[0]) == ['a', 6, 18] and
        list(df.values[1]) == ['b', 4, 8]
    )

def test_group_by_same_column():
    """
    Test group by with different
    aggregations on the same column
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by: agg
              sum: numbers
              min: numbers
              max: numbers
        """,
        dataframe=pd.DataFrame({
            "agg": ["a", "a", "a", "b"],
            "numbers": [1,2,3,4]
        })
    )

    assert (
        list(df.values[0]) == ['a', 6, 1, 3] and
        list(df.values[1]) == ['b', 4, 4, 4]
    )

def test_group_by_percentiles():
    """
    Test group by with different
    aggregations on the same column
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              p0: numbers
              p1: numbers
              p25: numbers
              p50: numbers
              p75: numbers
              p90: numbers
              p100: numbers
        """,
        dataframe=pd.DataFrame({
            "numbers": [i for i in range(101)]
        })
    )

    assert list(df.values[0]) == [0, 1, 25, 50, 75, 90, 100]

def test_group_by_to_list():
    """
    Test group by aggregating to a list
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by: agg
              list: to_list
        """,
        dataframe=pd.DataFrame({
            "agg": ["a", "a", "a", "b"],
            "to_list": [1,2,3,4],
        })
    )

    assert (
        list(df.values[0]) == ['a', [1,2,3]] and
        list(df.values[1]) == ['b', [4]]
    )

def test_group_by_to_list_multiple_by():
    """
    Test group by aggregating on multiple columns
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by:
                - agg1
                - agg2
              list: to_list
        """,
        dataframe=pd.DataFrame({
            "agg1": ["a", "a", "a", "b"],
            "agg2": ["a", "a", "b", "b"],
            "to_list": [1,2,3,4],
        })
    )

    assert (
        list(df.values[0]) == ['a', 'a', [1,2]] and
        list(df.values[1]) == ['a', 'b', [3]] and
        list(df.values[2]) == ['b', 'b', [4]]
    )


def test_group_by_to_list_multiple_list():
    """
    Test group by aggregating
    multiple columns to lists
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.group_by:
              by: agg
              list:
                - to_list1
                - to_list2
        """,
        dataframe=pd.DataFrame({
            "agg": ["a", "a", "a", "b"],
            "to_list1": [1,2,3,4],
            "to_list2": [5,6,7,8],
        })
    )

    assert (
        list(df.values[0]) == ['a', [1,2,3], [5,6,7]] and
        list(df.values[1]) == ['b', [4], [8]]
    )

def test_element_list():
    """
    Test get element from a list
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col[0]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [["a", "b", "c"]]
        })
    )
    assert df["result"][0] == "a"

def test_element_dict_without_quotes():
    """
    Test get element from a dict
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col[a]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [{"a": 1, "b": 2, "c": 3}]
        })
    )
    assert df["result"][0] == 1

def test_element_dict_double_quotes():
    """
    Test get element from a dict
    using double quotes
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col["a"]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [{"a": 1, "b": 2, "c": 3}]
        })
    )
    assert df["result"][0] == 1

def test_element_dict_single_quotes():
    """
    Test get element from a dict
    using single quotes
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col['a']
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [{"a": 1, "b": 2, "c": 3}]
        })
    )
    assert df["result"][0] == 1

def test_element_dict_escape_quotes():
    """
    Test get element from a dict
    using with an escaped quote
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col["a\'"]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [{"a'": 1, "b": 2, "c": 3}]
        })
    )
    assert df["result"][0] == 1

def test_element_dict_not_found():
    """
    Test get element from a dict
    where the element does not exist
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col["d"]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [{"a": 1, "b": 2, "c": 3}]
        })
    )
    assert df["result"][0] == ""

def test_element_list_not_found():
    """
    Test get element from a dict
    where the element does not exist
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col[3]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [["a","b","c"]]
        })
    )
    assert df["result"][0] == ""

def test_element_dict_default():
    """
    Test get element from a dict
    where the element does not exist
    with a default value
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col["d"]
              output: result
              default: x
        """,
        dataframe=pd.DataFrame({
            "col": [{"a": 1, "b": 2, "c": 3}]
        })
    )
    assert df["result"][0] == "x"

def test_element_list_default():
    """
    Test get element from a dict
    where the element does not exist
    with a default value
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col[3]
              output: result
              default: x
        """,
        dataframe=pd.DataFrame({
            "col": [["a","b","c"]]
        })
    )
    assert df["result"][0] == "x"

def test_element_multi_layer():
    """
    Test get element from a list
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col[0]["a"]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [[{"a": 1, "b": 2, "c": 3}]]
        })
    )
    assert df["result"][0] == 1

def test_element_overwrite_input():
    """
    Test get element from a list
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col[0]
        """,
        dataframe=pd.DataFrame({
            "col": [["a", "b", "c"]]
        })
    )
    assert df["col"][0] == "a"

def test_element_multiple_io():
    """
    Test get element from a list
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input:
                - col1[0]
                - col2[2]
              output:
                - result1
                - result2
        """,
        dataframe=pd.DataFrame({
            "col1": [["a", "b", "c"]],
            "col2": [["x", "y", "z"]],
        })
    )
    assert (
        df["result1"][0] == "a" and
        df["result2"][0] == "z" 
    )

def test_element_dict_by_index():
    """
    Test get element from a dict
    by using the index position
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - select.element:
              input: col[0]
              output: result
        """,
        dataframe=pd.DataFrame({
            "col": [{"a": 1, "b": 2, "c": 3}]
        })
    )
    assert df["result"][0] == 1
