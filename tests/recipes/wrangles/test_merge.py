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

    def test_key_value_pais_empty_dataframe(self):
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
