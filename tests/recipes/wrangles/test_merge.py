import wrangles
import pandas as pd
import pytest


class TestMergeCoalesce:
    """
    Test merge.coalesce
    """
    def test_columns(self):
        """
        Test coalescing multiple columns into one
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input: 
                  - Col1
                  - Col2
                  - Col3
                output: Output Col
            """,
            dataframe=pd.DataFrame({
                'Col1': ['A', '', ''],
                'Col2': ['', 'B', ''],
                'Col3': ['', '', 'C']
            })
        )
        assert df['Output Col'].values.tolist() == ['A', 'B', 'C']

    def test_where(self):
        """
        Test coalesce using where
        """
        data = pd.DataFrame({
            'Col1': ['A', '', ''],
            'Col2': ['', 'B', ''],
            'Col3': ['', '', 'C'],
            'numbers': [3, 4, 5]
        })
        recipe = """
        wrangles:
        - merge.coalesce:
            input: 
                - Col1
                - Col2
                - Col3
            output: Output Col
            where: numbers = 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Output Col'] == 'B' and df.iloc[0]['Output Col'] ==''

    def test_lists(self):
        """
        Test coalesce with a single column containing a list
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: ["","b","c"]
            wrangles:
            - merge.coalesce:
                input: header
            """
        )
        assert df["header"][0] == 'b'

    def test_lists_with_output(self):
        """
        Test coalesce with a single column containing
        a list that defines an output column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: ["","b","c"]
            wrangles:
            - merge.coalesce:
                input: header
                output: result
            """
        )
        assert df["result"][0] == 'b'

    def test_lists_mixed_list_scalar(self):
        """
        Test coalesce with a single column that
        contains a mix of lists and scalars
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input: header
            """,
            dataframe=pd.DataFrame({
                'header': [["","bb","cc"], '', 'dd', ["ee", ""]]
            })
        )
        assert df["header"].to_list() == ['bb', '', 'dd', 'ee']

    def test_output_error(self):
        """
        Test that a clear error is given if trying to coalesce
        multiple columns but not giving an output
        """
        with pytest.raises(ValueError, match="output column must be provided"):
            wrangles.recipe.run(
                """
                read:
                  - test:
                      rows: 1
                      values:
                        header1: value1
                        header2: value2
                wrangles:
                  - merge.coalesce:
                      input:
                        - header1
                        - header2
                """
            )

    def test_coalesce_empty_dataframe(self):
        """
        Test coalesce with empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
        - merge.coalesce:
            input:
                - Col1
                - Col2
                - Col3
            output: Output Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Output Col']

class TestMergeConcatenate:
    """
    All concatenate tests
    """
    def test_concatenate_1(self):
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'C']]
        })
        recipe = """
        wrangles:
        - merge.concatenate:
            input: Col1
            output: Join List
            char: ' '
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Join List'] == 'A B C'
        
    # Multi column concat
    def test_concatenate_2(self):
        data = pd.DataFrame({
            'Col1': ['A'],
            'Col2': ['B'],
            'Col3': ['C']
        })
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
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Join Col'] == 'A, B, C'

    def test_concatenate_where(self):
        """
        Test concatenate using where
        """
        data = pd.DataFrame({
            'Col1': ['A', 'E', 'H'],
            'Col2': ['B', 'F', 'I'],
            'Col3': ['C', 'G', 'J'],
            'numbers': [23, 44, 13]
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Join Col
                char: ', '
                where: numbers !=13
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Join Col'] == 'A, B, C' and df.iloc[2]['Join Col'] == ''

    def test_where_single_column(self):
        """
        Test concatenate using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - merge.concatenate:
                    input: Col1
                    output: Col1
                    char: ', '
                    where: Col1 LIKE '%A%'
            """,
            dataframe=pd.DataFrame({
                'Col1': [['A', 'B', 'C'], [1,2,3], ['X', 'Y', 'Z']],
            })
        )
        assert df['Col1'].to_list() == ['A, B, C', [1,2,3], ['X','Y','Z']]

    def test_concatenate_integer(self):
        """
        Test that a non-string doesn't
        break the concatenation
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: ["a", 1]
            wrangles:
            - merge.concatenate:
                input: header1
                output: result
                char: ''
            """
        )
        assert df["result"][0] == 'a1'

    def test_concatenate_skip_empty_true(self):
        """
        Test skipping empty values as true
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: a
                    header2: ""
                    header3: b
            wrangles:
            - merge.concatenate:
                input:
                    - header1
                    - header2
                    - header3
                output: result
                char: '-'
                skip_empty: true
            """
        )
        assert df["result"][0] == 'a-b'

    def test_concatenate_skip_empty_false(self):
        """
        Test skipping empty values set as false
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: a
                    header2: ""
                    header3: b
            wrangles:
            - merge.concatenate:
                input:
                    - header1
                    - header2
                    - header3
                output: result
                char: '-'
                skip_empty: false
            """
        )
        assert df["result"][0] == 'a--b'

    def test_concatenate_skip_empty_default(self):
        """
        Test skipping empty values not provided
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: a
                    header2: ""
                    header3: b
            wrangles:
            - merge.concatenate:
                input:
                    - header1
                    - header2
                    - header3
                output: result
                char: '-'
            """
        )
        assert df["result"][0] == 'a--b'

    def test_concatenate_strings(self):
        """
        Test concatenate with a single column of strings (a bug)
        """
        data = pd.DataFrame({
            'Col1': ['AAAAAA', 'EEEEEE', 'HHHHHH'],
            'Col2': ['BBBBBB', 'FFFFFF', 'IIIIII'],
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: Col1
                output: Output Col
                char: ' '
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Output Col'] == 'AAAAAA' and df.iloc[2]['Output Col'] == 'HHHHHH'

    def test_concatenate_strings_skip_empty(self):
        """
        Test concatenate with a single column of strings (a bug) with skip empty
        """
        data = pd.DataFrame({
            'Col1': ['AAAAAA', 'EEEEEE', 'HHHHHH'],
            'Col2': ['BBBBBB', 'FFFFFF', 'IIIIII'],
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: Col1
                output: Output Col
                char: ' '
                skip_empty: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Output Col'] == 'AAAAAA' and df.iloc[2]['Output Col'] == 'HHHHHH'

    def test_concatenate_empty_dataframe(self):
        """
        Test concatenate with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Output Col
                char: ', '
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Output Col']


class TestMergeLists:
    """
    Test merge.lists
    """
    def test_lists_1(self):
        """
        Joining lists together
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B']],
            'Col2': [['D', 'E']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'D', 'E']

    def test_lists_where(self):
        """
        Test merge.lists using where
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B'], ['C', 'D']],
            'Col2': [['D', 'E'], ['F', 'G']],
            'numbers': [0, 5]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                where: numbers > 0
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == '' and df.iloc[1]['Combined Col'] == ['C', 'D', 'F', 'G']

    def test_lists_remove_duplicates(self):
        """
        Test merge.lists using remove_duplicates
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'C'], ['F', 'G', 'H']],
            'Col2': [['D', 'E', 'C'], ['F', 'G', 'I']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                remove_duplicates: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'C', 'D', 'E'] and df.iloc[1]['Combined Col'] == ['F', 'G', 'H', 'I']

    def test_lists_remove_duplicates_ignore_case_true(self):
        """
        Test merge.lists using remove_duplicates with ignore_case set to true
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'c'], ['f', 'G', 'H']],
            'Col2': [['D', 'E', 'C'], ['F', 'g', 'I']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                remove_duplicates: true
                ignore_case: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'c', 'D', 'E'] and df.iloc[1]['Combined Col'] == ['f', 'G', 'H', 'I']

    def test_lists_remove_duplicates_ignore_case_false(self):
        """
        Test merge.lists using remove_duplicates with ignore_case set to false
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'c'], ['f', 'G', 'H']],
            'Col2': [['D', 'E', 'C'], ['F', 'g', 'I']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                remove_duplicates: true
                ignore_case: false
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'c', 'D', 'E', 'C'] and df.iloc[1]['Combined Col'] == ['f', 'G', 'H', 'F', 'g', 'I']

    def test_lists_ignore_case_false(self):
        """
        Test merge.lists using with ignore_case without remove_duplicates
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B'], ['f', 'G']],
            'Col2': [['D', 'B'], ['F', 'g']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                ignore_case: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'D', 'B'] and df.iloc[1]['Combined Col'] == ['f', 'G', 'F', 'g']

    def test_lists_empty_dataframe(self):
        """
        Test merge.lists with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Combined Col']

    def test_lists_include_empty_true(self):
        """
        Test merge.lists with include_empty=True (should include empty strings)
        """
        data = pd.DataFrame({
            'Col1': ['', 'A', 'B'],  # String column with empty value
            'Col2': [['C', 'D'], ['E'], ['F', 'G']]  # List column
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                include_empty: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['', 'C', 'D']
        assert df.iloc[1]['Combined Col'] == ['A', 'E']
        assert df.iloc[2]['Combined Col'] == ['B', 'F', 'G']

    def test_lists_include_empty_false(self):
        """
        Test merge.lists with include_empty=False (should filter out empty strings)
        """
        data = pd.DataFrame({
            'Col1': ['', 'A', 'B'],  # String column with empty value
            'Col2': [['C', 'D'], ['E'], ['F', 'G']]  # List column
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                include_empty: false
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['C', 'D']  # Empty string filtered out
        assert df.iloc[1]['Combined Col'] == ['A', 'E']
        assert df.iloc[2]['Combined Col'] == ['B', 'F', 'G']

    def test_lists_include_empty_default(self):
        """
        Test merge.lists with default include_empty (should be True for backward compatibility)
        """
        data = pd.DataFrame({
            'Col1': ['', 'A'],  # String column with empty value
            'Col2': [['C', 'D'], ['E']]  # List column
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        # Default should include empty strings for backward compatibility
        assert df.iloc[0]['Combined Col'] == ['', 'C', 'D']
        assert df.iloc[1]['Combined Col'] == ['A', 'E']

    def test_lists_include_empty_mixed_input(self):
        """
        Test merge.lists with include_empty=False and mixed list/string inputs including empty values in lists
        """
        data = pd.DataFrame({
            'Col1': ['', 'A'],  # String column with empty value
            'Col2': [['', 'B', ''], ['C', '']]  # List column with empty values
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                include_empty: false
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        # Should filter out all empty strings
        assert df.iloc[0]['Combined Col'] == ['B']
        assert df.iloc[1]['Combined Col'] == ['A', 'C']


class TestMergeToList:
    """
    Test merge.to_list
    """
    def test_to_lists_1(self):
        data = pd.DataFrame({
            'Col1': ['A'],
            'Col2': ['B'],
            'Col3': ['C']
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'C']
        
    def test_to_lists_where(self):
        """
        Test merge.to_list using where
        """
        data = pd.DataFrame({
            'Col1': ['A', 'D', 'G'],
            'Col2': ['B', 'E', 'H'],
            'Col3': ['C', 'F', 'I'],
            'numbers': [3, 6, 9]
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
                where: numbers = 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == '' and df.iloc[1]['Combined Col'] == ['D', 'E', 'F']

    def test_to_lists_empty_dataframe(self):
        """
        Test merge.to_list with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Combined Col']


class TestMergeToDict:
    """
    Test merge.to_dict
    """
    def test_to_dict_1(self):
        data = pd.DataFrame({
        'Col1':[{'A'}],
        'Col2':[{'B'}]
    })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: 
                    - Col1
                    - Col2
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': {'A'}, 'Col2': {'B'}}

    def test_to_dict_2(self):
        """
        Input is a wildcard
        """
        data = pd.DataFrame({
        'Col1':[{'A'}],
        'Col2':[{'B'}]
    })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: Col*
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': {'A'}, 'Col2': {'B'}}

    def test_to_dict_3(self):
        """
        If the row instance is a boolean type
        """
        data = pd.DataFrame({
            'Col1':[True],
            'Col2':[False],
            'Col3': [None],
        })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: Col*
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': True, 'Col2': False, 'Col3': None}

    def test_to_dict_where(self):
        """
        Test merge.to_dict using where
        """
        data = pd.DataFrame({
            'Col1':['A', 'C', 'E'],
            'Col2':['B', 'D', 'F'],
            'numbers': [43, 22, 65]
        })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: 
                    - Col1
                    - Col2
                output: Dict Col
                where: numbers < 60
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': 'A', 'Col2': 'B'} and df.iloc[2]['Dict Col'] == ''

    def test_to_dict_empty_dataframe(self):
        """
        Test merge.to_dict with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Dict Col']


class TestMergeKeyValuePairs:
    """
    Test merge.key_value_pairs
    """
    def test_key_value_pairs_1(self):
        data = pd.DataFrame({
        'Letter': ['A', 'B', 'C'],
        'Number': [1, 2, 3],
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  Letter: Number
                output: Pairs
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[2]['Pairs'] == {'C': 3}

    def test_key_value_pairs_where(self):
        """
        Test merge.key_value_pairs using where
        """
        data = pd.DataFrame({
        'Letter': ['A', 'B', 'C'],
        'Number': [1, 2, 3],
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  Letter: Number
                output: Pairs
                where: Number = 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Pairs'] == {'B': 2} and df.iloc[0]['Pairs'] == ''

    def test_key_value_pairs_2(self):
        """
        Using a Wildcard
        """
        data = pd.DataFrame({
        'key 1': ['A', 'B', 'C'],
        'key 2': ['One', 'Two', 'three'],
        'value 1': ['a', 'b', 'c'],
        'value 2': ['First', 'Second', 'Third']
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  key*: value*
                output: Object
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[2]['Object'] == {'C': 'c', 'three': 'Third'}

    def test_wildcard_where(self):
        """
        Using a Wildcard and where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - merge.key_value_pairs:
                    input:
                        key*: value*
                    output: Object
                    where: '"key 1" = "C"'
            """,
            dataframe=pd.DataFrame({
                'key 1': ['A', 'B', 'C'],
                'key 2': ['One', 'Two', 'three'],
                'value 1': ['a', 'b', 'c'],
                'value 2': ['First', 'Second', 'Third']
            })
        )
        assert (
            df['Object'][0] == '' and 
            df['Object'][2] == {'C': 'c', 'three': 'Third'}
        )

    def test_key_value_pairs_3(self):
        """
        True or False in row Values
        """
        data = pd.DataFrame({
        'key 1': ['A'],
        'key 2': [True],
        'value 1': ['a'],
        'value 2': [False]
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  key*: value*
                output: Object
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Object'] == {'A': 'a', True: False}

    def test_key_value_pairs_empty_dataframe(self):
        """
        Test merge.key_value_pairs with an empty dataframe
        """
        data = pd.DataFrame({
            'key1': [],
            'key2': [],
            'value1': [],
            'value2': []
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  key*: value*
                output: Object
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['key1', 'key2', 'value1', 'value2', 'Object']
    
    def test_key_value_pairs_skip_empty_true(self):  
        """  
        Test merge.key_value_pairs with skip_empty=True - should skip empty keys and values  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '', 'C'],  # Empty key in second row  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # Empty dict because key is empty  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_false(self):  
        """  
        Test merge.key_value_pairs with skip_empty=False - should include empty keys/values  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '', 'C'],  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: false  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {'': 2}  # Empty key included  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_values(self):  
        """  
        Test that skip_empty also skips empty values, not just keys  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', 'B', 'C'],  
            'Number': [1, '', 3],  # Empty value in second row  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # Empty dict because value is empty  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_whitespace(self):  
        """  
        Test that skip_empty treats whitespace-only strings as empty  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '  ', 'C'],  # Whitespace key in second row  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # Whitespace key skipped  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_none_values(self):  
        """  
        Test that skip_empty handles None values correctly  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', 'B', 'C'],  
            'Number': [1, None, 3],  # None value in second row  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # None value skipped  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_multiple_pairs(self):  
        """  
        Test skip_empty with multiple key-value pairs using wildcards  
        """  
        data = pd.DataFrame({  
            'key 1': ['A', '', 'C'],  
            'key 2': ['One', 'Two', ''],  
            'value 1': ['a', 'b', 'c'],  
            'value 2': ['First', '', 'Third']  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    key*: value*  
                output: Object  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Object'] == {'A': 'a', 'One': 'First'}  
        assert df.iloc[1]['Object'] == {}  # Empty key and value skipped  
        assert df.iloc[2]['Object'] == {'C': 'c'}  # Empty key and value skipped  
    
    def test_key_value_pairs_skip_empty_all_empty(self):  
        """  
        Test skip_empty when all keys/values in a row are empty  
        """  
        data = pd.DataFrame({  
            'Letter': ['', '', ''],  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {}  
        assert df.iloc[1]['Pairs'] == {}  
        assert df.iloc[2]['Pairs'] == {}  
    
    def test_key_value_pairs_skip_empty_with_where(self):  
        """  
        Test skip_empty works correctly with where clause  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '', 'C'],  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
                where: Number > 1  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == ''  # Not processed due to where clause  
        assert df.iloc[1]['Pairs'] == {}  # Processed but empty key skipped  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_boolean_values(self):  
        """  
        Test that skip_empty correctly handles boolean values  
        """  
        data = pd.DataFrame({  
            'key 1': ['A'],  
            'key 2': [True],  
            'value 1': ['a'],  
            'value 2': [False]  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    key*: value*  
                output: Object  
                skip_empty: false  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Object'] == {'A': 'a', True: False}

class TestMergeDictionaries:
    """
    Test merge.dictionaries
    """
    def test_merge_dicts_1(self):
        data = pd.DataFrame({
            'd1': [{'Hello': 'Fey'}],
            'd2': [{'Hello2': 'Lucy'}],
        })
        recipe = """
        wrangles:
        - merge.dictionaries:
            input:
                - d1
                - d2
            output: out
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}

    def test_merge_dicts_where(self):
        """
        Tests merge.dictionaries using where
        """
        data = pd.DataFrame({
            'd1': [{'Hello': 'Fey'}, {'Hello': 'Moto'}, {'Hello': 'World'}],
            'd2': [{'Hola': 'Lucy'}, {'Hola': 'Hello'}, {'Hola': 'Nice to meet you'}],
            'numbers': [2, 55, 71]
        })
        recipe = """
        wrangles:
        - merge.dictionaries:
            input:
                - d1
                - d2
            output: out
            where: numbers > 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['out'] == {'Hello': 'Moto', 'Hola': 'Hello'} and df.iloc[0]['out'] == ''

    def test_merge_dicts_empty_dataframe(self):
        """
        Test merge.dictionaries with an empty dataframe
        """
        data = pd.DataFrame({
            'd1': [],
            'd2': [],
            'd3': []
        })
        recipe = """
        wrangles:
        - merge.dictionaries:
            input:
                - d1
                - d2
                - d3
            output: out
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['d1', 'd2', 'd3', 'out']
        
    def test_merge_dicts_skip_empty_true(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should skip empty dictionary values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}],  
            'd2': [{'Hello2': 'Lucy', 'Blank': ''}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should only include non-empty values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_false(self):  
        """  
        Test merge.dictionaries with skip_empty=False - should include empty values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}],  
            'd2': [{'Hello2': 'Lucy', 'Blank': ''}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: false  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should include empty values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Empty': '', 'Hello2': 'Lucy', 'Blank': ''}  
    
    def test_merge_dicts_skip_empty_default(self):  
        """  
        Test merge.dictionaries with default skip_empty (should be False for backward compatibility)  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}],  
            'd2': [{'Hello2': 'Lucy'}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Default should include empty values for backward compatibility  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Empty': '', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_whitespace(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should skip whitespace-only values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Spaces': '   '}],  
            'd2': [{'Hello2': 'Lucy', 'Tab': '\t'}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should skip whitespace-only values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_none_values(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should skip None values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'NoneVal': None}],  
            'd2': [{'Hello2': 'Lucy', 'AlsoNone': None}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should skip None values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_mixed_types(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should handle mixed types correctly  
        """  
        data = pd.DataFrame({  
            'd1': [{'String': 'Value', 'Number': 0, 'Empty': ''}],  
            'd2': [{'Bool': False, 'None': None, 'Valid': 'Data'}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should skip empty string and None, but keep 0 and False (they're valid values)  
        assert df.iloc[0]['out'] == {'String': 'Value', 'Number': 0, 'Bool': False, 'Valid': 'Data'}  
    
    def test_merge_dicts_skip_empty_all_empty(self):  
        """  
        Test merge.dictionaries with skip_empty=True when all values are empty  
        """  
        data = pd.DataFrame({  
            'd1': [{'Empty1': '', 'Empty2': ''}],  
            'd2': [{'Empty3': None, 'Empty4': '   '}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should result in empty dictionary  
        assert df.iloc[0]['out'] == {}  
    
    def test_merge_dicts_skip_empty_where(self):  
        """  
        Test merge.dictionaries with skip_empty=True and where clause  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}, {'Hello': 'Moto', 'Empty': ''}],  
            'd2': [{'Hola': 'Lucy', 'Blank': ''}, {'Hola': 'Hello', 'Blank': ''}],  
            'numbers': [2, 55]  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
            where: numbers > 2  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[1]['out'] == {'Hello': 'Moto', 'Hola': 'Hello'} and df.iloc[0]['out'] == ''

    def test_merge_dicts_with_empty_dict(self):  
        """  
        Test merge.dictionaries with one empty dictionary  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey'}, {}, {'Hello': 'World'}],  
            'd2': [{'Hola': 'Lucy'}, {'Hola': 'Moto'}, {'Hola': 'Nice'}],  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            skip_empty: true
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        expected = [  
            {'Hello': 'Fey', 'Hola': 'Lucy'},  
            {'Hola': 'Moto'},  
            {'Hello': 'World', 'Hola': 'Nice'}  
        ]  
        assert df['out'].tolist() == expected
    
    def test_merge_dicts_few_empty_dict(self):  
        """  
        Test merge.dictionaries with a few empty dictionaries  
        """  
        data = pd.DataFrame({  
            'd1': [{}, {'Hello': 'Fey'}, {}],  
            'd2': [{'Hola': 'Lucy'}, {}, {'Hola': 'Moto'}],  
            'd3': [{'key': 'value'}, {'key': 'test'}, {}]  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
                - d3 
            skip_empty: true 
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        expected = [  
            {'Hola': 'Lucy', 'key': 'value'},  
            {'Hello': 'Fey', 'key': 'test'},  
            {'Hola': 'Moto'}  
        ]  
        assert df['out'].tolist() == expected

    def test_merge_dicts_all_empty_skip_empty_true(self):  
        """  
        Test merge.dictionaries where all dictionaries are empty  
        """  
        data = pd.DataFrame({  
            'd1': [{}, {}, {}],  
            'd2': [{}, {}, {}],  
            'd3': [{}, {}, {}]  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
                - d3  
            skip_empty: true 
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        # All rows should result in empty dictionaries  
        expected = [{}, {}, {}]  
        assert df['out'].tolist() == expected

    def test_merge_dicts_all_empty_skip_empty_false(self):  
        """  
        Test merge.dictionaries where all dictionaries are empty with skip_empty=False 
        """  
        data = pd.DataFrame({  
            'd1': [{}, {}, {}],  
            'd2': [{}, {}, {}],  
            'd3': [{}, {}, {}]  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
                - d3  
            skip_empty: false 
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        expected = [{}, {}, {}]  
        assert df['out'].tolist() == expected
        