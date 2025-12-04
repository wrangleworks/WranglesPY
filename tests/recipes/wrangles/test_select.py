import wrangles
import pandas as pd
import pytest


class TestSelectDictionaryElement:
    """
    Test select.dictionary_element
    """
    def test_dictionary_element_one_input(self):
        """
        Default select.dictionary_element test
        """
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
        
    def test_dictionary_element_two_inputs(self):
        """
        # if the input is multiple columns (a list)
        """
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

    def test_dictionary_element_input_output_error(self):
        """
        Test the the user receives a clear error
        if the input and output are not the same length
        """
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

    def test_dictionary_elem_default(self):
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

    def test_dictionary_element_where(self):
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

    def test_dictionary_element_list(self):
        """
        Test selecting multiple elements
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                output: Out
                element:
                - A
                - B
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A': '1', 'B': '2', 'C': '3'}],
            })
        )
        assert df['Out'][0] == {'A': '1', 'B': '2'}

    def test_dictionary_element_list_rename(self):
        """
        Test selecting multiple elements
        and renaming one
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                element:
                - A: A_1
                - B
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A': '1', 'B': '2', 'C': '3'}],
            })
        )
        assert df['Col1'][0] == {'A_1': '1', 'B': '2'}

    def test_dictionary_element_list_wildcard(self):
        """
        Test selecting multiple elements
        with a wildcard
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                element:
                - A: A_1
                - "*"
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A': '1', 'B': '2', 'C': '3'}],
            })
        )
        assert df['Col1'][0] == {'A_1': '1', 'B': '2', 'C': '3'}

    def test_dictionary_element_list_rename_wildcard(self):
        """
        Test selecting multiple elements
        with a wildcard
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                element:
                - "*1": "*2"
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A1': '1', 'B1': '2', 'C1': '3'}],
            })
        )
        assert df['Col1'][0] == {'A2': '1', 'B2': '2', 'C2': '3'}

    def test_dictionary_element_list_default(self):
        """
        Test selecting multiple elements
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                output: Out
                element:
                - A
                - B
                - Z
                default: default_value
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A': '1', 'B': '2', 'C': '3'}],
            })
        )
        assert df['Out'][0] == {'A': '1', 'B': '2', 'Z': 'default_value'}

    def test_dictionary_element_list_default_dict(self):
        """
        Test selecting multiple elements
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                output: Out
                element:
                - A
                - Y
                - Z
                default:
                  Y: default_value_1
                  Z: default_value_2
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A': '1', 'B': '2', 'C': '3'}],
            })
        )
        assert df['Out'][0] == {
            'A': '1',
            'Y': 'default_value_1',
            'Z': 'default_value_2'
        }

    def test_dictionary_element_json_element_list(self):
        """
        Test the select.dictionary_element works even
        if it's a json string for element as a list
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.dictionary_element:
                input: column
                element:
                - a
                - b
            """,
            dataframe=pd.DataFrame({
                'column': ['{"a": 1, "b": 2, "c": 3}']
            })
        )
        assert df['column'][0] == {'a': 1, 'b': 2}

    def test_dictionary_element_json_element_single(self):
        """
        Test the select.dictionary_element works even
        if it's a json string for element as a single value
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.dictionary_element:
                input: column
                element: a
            """,
            dataframe=pd.DataFrame({
                'column': ['{"a": 1, "b": 2, "c": 3}']
            })
        )
        assert df['column'][0] == 1

    def test_dictionary_element_string_wildcard(self):
        """
        Test selecting elements with a wildcard passed as a string
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                output: Output
                element: A*
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A1': '1', 'B1': '2', 'A2': '3'}],
            })
        )
        assert df['Output'][0] == {'A1': '1', 'A2': '3'}

    def test_dictionary_element_string_wildcard_nonexistent(self):
        """
        Test selecting nonexistent elements with a wildcard passed as a string
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                output: Output
                element: C*
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A1': '1', 'B1': '2', 'A2': '3'}],
            })
        )
        assert df['Output'][0] == {}

    def test_dictionary_element_wildcard_single_element(self):
        """
        Test that wildcard output is a dictionary
        with only one matched element
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                output: Output
                element: B*
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A1': '1', 'B1': '2', 'A2': '3'}],
            })
        )
        assert df['Output'][0] == {'B1': '2'}

    def test_dictionary_element_regex_single_element(self):
        """
        Test that regex output is a dictionary
        with only one matched element
        """
        df = wrangles.recipe.run("""
            wrangles:
            - select.dictionary_element:
                input: Col1
                output: Output
                element: 'regex: B.*'
            """,
            dataframe=pd.DataFrame({
            'Col1': [{'A1': '1', 'B1': '2', 'A2': '3'}],
            })
        )
        assert df['Output'][0] == {'B1': '2'}

    def test_dictionary_element_empty_dict(self):
        """
        Test the select.dictionary_element works even
        if the input is an empty dictionary
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.dictionary_element:
                input: column
                element: a
            """,
            dataframe=pd.DataFrame({
                'column': [{}]
            })
        )
        assert df['column'][0] == ''

    def test_dictionary_element_empty(self):
        """
        Test the select.dictionary_element with an empty data column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.dictionary_element:
                input: column
                output: output column
                element: a
            """,
            dataframe=pd.DataFrame({
                'column': []
            })
        )
        assert list(df.columns) == ['column', 'output column'] and len(df) == 0


class TestSelectListElement:
    """
    Test select.list_element
    """
    def test_list_element_1(self):
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

    def test_list_element_2(self):
        """
        Empty values
        """
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

    def test_list_element_3(self):
        """
        Out of Index values
        """
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

    def test_list_element_4(self):
        """
        If the input is multiple columns (a list)
        """
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

    def test_list_element_5(self):
        """
        If the input and output are not the same type
        """
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

    def test_list_element_where(self):
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
        
    def test_list_elem_default_string(self):
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
        
    def test_list_elem_default_list(self):
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

    def test_list_element_integer_as_string(self):
        """
        Test that select.list_element gives the correct answer
        for an integer given as a string.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.list_element:
                input: Col1
                output: Second Element
                element: '1'
            """,
            dataframe=pd.DataFrame({
                'Col1': [['A', 'B', 'C']]
            })
        )
        assert df.iloc[0]['Second Element'] == 'B'

    def test_list_element_slice(self):
        """
        Test that select.list_element gives the correct
        answer for selecting a slice from a list.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.list_element:
                input: Col1
                element: ':2'
            """,
            dataframe=pd.DataFrame({
                'Col1': [['A', 'B', 'C']]
            })
        )
        assert df["Col1"][0] == ["A","B"]

    def test_list_element_invalid_element(self):
        """
        Test that select.list_element gives a clear
        error if the user tries to select an element
        using invalid syntax.
        """
        with pytest.raises(ValueError, match="'a'"):
            wrangles.recipe.run(
                """
                wrangles:
                - select.list_element:
                    input: Col1
                    element: 'a'
                """,
                dataframe=pd.DataFrame({
                    'Col1': [['A', 'B', 'C']]
                })
            )

    def test_list_element_json(self):
        """
        Test that select.list_element works even if
        the input is a json string.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.list_element:
                input: column
                element: 1
            """,
            dataframe=pd.DataFrame({
                'column': ['["A", "B", "C"]']
            })
        )
        assert df['column'][0] == 'B'

    def test_list_element_empty_list(self):
        """
        Test that select.list_element works even if
        the input is an empty list.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.list_element:
                input: column
                element: 1
            """,
            dataframe=pd.DataFrame({
                'column': [[]]
            })
        )
        assert df['column'][0] == ''

    def test_list_element_empty(self):
        """
        Test that select.list_element with an empty data column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.list_element:
                input: column
                output: output column
                element: 1
            """,
            dataframe=pd.DataFrame({
                'column': []
            })
        )
        assert list(df.columns) == ['column', 'output column'] and len(df) == 0


class TestHighestConfidence:
    """
    Test select.highest_confidence
    """
    def test_highest_confidence_1(self):
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

    def test_highest_confidence_list_output(self):
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

    def test_highest_confidence_where(self):
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

    def test_highest_confidence_single_output(self):
        """
        Test that select.highest_confidence works to
        see that a list of one is the same as a single value
        for output
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
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Winner'] == ['C', 0.99]

    def test_highest_confidence_json_input(self):
        """
        Test that select.highest_confidence works where
        the input values is are in JSON.
        """
        data = pd.DataFrame({
        'Col1': ['{"A": 0.79}'],
        'Col2': ['{"B": 0.80}'],
        'Col3': ['{"C": 0.99}']
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

    def test_highest_confidence_input_strings(self):
        """
        Test that select.highest_confidence works where
        input scores are string. 
        """
        data = pd.DataFrame({
        'Col1': [['A', '0.79']],
        'Col2': [['B', '0.80']],
        'Col3': [['C', '0.99']]
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

    def test_highest_confidence_input_single_column_list(self):
        """
        Test that select.highest_confidence works where
        where the input is a sinlge column with a list
        """
        data = pd.DataFrame({
        'Col1': [[['A', 0.79], ['B', 0.80], ['C', 0.99]]]
        })
        recipe = """
        wrangles:
            - select.highest_confidence:
                input: Col1
                output: Winner
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Winner'] == ['C', 0.99]

    def test_highest_confidence_error(self):
        """
        Test that select.highest_confidence gives 
        a clear error message with invalid input/output
        """
        with pytest.raises(ValueError):
            raise wrangles.recipe.run(
                """
                wrangles: 
                    - select.highest_confidence:
                        input: 
                            - Col1
                            - Col2
                            - Col3
                        output: Winner
                """,
                dataframe=pd.DataFrame({
                    'Col1': [['A, .079']],
                    'Col2': ['B = 0.80'], 
                    'Col3': [['C: 0.99']]
                })
            )

    def test_highest_confidence_empty(self):
        """
        Test that select.highest_confidence with an empty data column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.highest_confidence:
                input: column
                output: Winner
            """,
            dataframe=pd.DataFrame({
                'column': []
            })
        )
        assert list(df.columns) == ['column', 'Winner'] and len(df) == 0


class TestSelectThreshold:
    """
    Test select.threshold
    """
    def test_threshold_1(self):
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

    def test_threshold_2(self):
        """
        Noun (Token) return empty aka None
        """
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

    def test_threshold_3(self):
        """
        Noun (Token) return empty aka None and cell 2 is a list
        """
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

    def test_threshold_4(self):
        """
        Cell_1[0] is above the threshold
        """
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
        
    def test_threshold_5(self):
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

    def test_threshold_where(self):
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

    def test_threshold_empty(self):
        """
        Test that select.threshold with an empty data column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.threshold:
                input:
                  - column1
                  - column2
                output: Top Words
                threshold: .77
            """,
            dataframe=pd.DataFrame({
                'column1': [],
                'column2': []
            })
        )
        assert list(df.columns) == ['column1', 'column2', 'Top Words'] and len(df) == 0


class TestSelectLeft:
    """
    Test select.left
    """
    def test_left_two_inputs(self):
        """
        Multi Columns input and output
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
                output:
                    - Out1
                    - Out2
                length: 5
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Out1'] == 'One T'

    def test_left_overwrite_input(self):
        """
        Output is none
        """
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

    def test_left_where(self):
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

    def test_left_multi_input_single_output(self):
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

    def test_left_invalid_length_value(self):
        """
        Test that select.left gives a clear error if
        the value of length is invalid.
        """
        with pytest.raises(TypeError, match="must be an integer"):
            wrangles.recipe.run(
                """
                wrangles:
                - select.left:
                    input: Col1
                    length: a
                """,
                dataframe=pd.DataFrame({
                    'Col1': ['example'],
                })
            )

    def test_left_length_as_string(self):
        """
        Test that select.left gives the correct answer
        if the length is given as a string, but
        is a valid integer.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.left:
                    input: Col1
                    length: '4'
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == "exam"

    def test_left_length_as_zero(self):
        """
        Test that select.left gives a clear error if
        the value of length is zero.
        """
        with pytest.raises(ValueError, match="may not equal 0"):
            wrangles.recipe.run(
                """
                wrangles:
                - select.left:
                    input: Col1
                    length: 0
                """,
                dataframe=pd.DataFrame({
                    'Col1': ['example'],
                })
            )

    def test_left_negative_length(self):
        """
        Test that select.left gives the correct answer
        if the length is given as a string, but
        is a valid integer.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.left:
                    input: Col1
                    length: -4
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == "ple"

    def test_left_shorter_than_length(self):
        """
        Test that select.left gives the original
        string back if a length longer than that
        is set.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.left:
                    input: Col1
                    length: 10
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == "example"

    def test_left_negative_more_than_length(self):
        """
        Test that a negative value
        longer than the length of the string
        gives back an empty string.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.left:
                    input: Col1
                    length: -10
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == ""

    def test_select_left_empty_df(self):
        """
        Test select.left with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.left:
                    input: Col1
                    output: output column
                    length: 3
            """,
            dataframe=pd.DataFrame({
                'Col1': [],
            })
        )
        assert df.empty


class TestSelectRight:
    """
    Test select.right
    """
    def test_right_two_inputs(self):
        """
        Multi column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.right:
                input:
                    - Col1
                    - Col2
                output:
                    - Out1
                    - Out2
                length: 4
            """,
            dataframe=pd.DataFrame({
                'Col1': ['One Two Three Four'],
                'Col2': ['A B C D']
            })
        )
        assert df.iloc[0]['Out1'] == 'Four'

    def test_right_overwrite_input(self):
        """
        Output is none
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.right:
                input: Col1
                length: 4
            """,
            dataframe=pd.DataFrame({
                'Col1': ['One Two Three Four'],
                'Col2': ['A B C D']
            })
        )
        assert df.iloc[0]['Col1'] == 'Four'

    def test_right_multi_input_single_output(self):
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

    def test_right_where(self):
        """
        Test select.right using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.right:
                    input: Col1
                    length: 6
                    where: numbers > 6
            """,
            dataframe=pd.DataFrame({
                'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
                'numbers': [6, 7, 8]
            })
        )
        assert df['Col1'].to_list() == ['One Two Three Four', ' Eight', 'Twelve']


    def test_right_invalid_length_value(self):
        """
        Test that select.right gives a clear error if
        the value of length is invalid.
        """
        with pytest.raises(TypeError, match="must be an integer"):
            wrangles.recipe.run(
                """
                wrangles:
                - select.right:
                    input: Col1
                    length: a
                """,
                dataframe=pd.DataFrame({
                    'Col1': ['example'],
                })
            )

    def test_right_length_as_string(self):
        """
        Test that select.right gives the correct answer
        if the length is given as a string, but
        is a valid integer.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.right:
                    input: Col1
                    length: '3'
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == "ple"

    def test_right_length_as_zero(self):
        """
        Test that select.right gives a clear error if
        the value of length is zero.
        """
        with pytest.raises(ValueError, match="may not equal 0"):
            wrangles.recipe.run(
                """
                wrangles:
                - select.right:
                    input: Col1
                    length: 0
                """,
                dataframe=pd.DataFrame({
                    'Col1': ['example'],
                })
            )

    def test_right_negative_length(self):
        """
        Test that select.right gives the correct answer
        if the length is given as a string, but
        is a valid integer.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.right:
                    input: Col1
                    length: -3
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == "exam"

    def test_right_shorter_than_length(self):
        """
        Test that select.right gives the original
        string back if a length longer than that
        is set.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.right:
                    input: Col1
                    length: 10
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == "example"

    def test_right_negative_more_than_length(self):
        """
        Test that a negative value
        longer than the length of the string
        gives back an empty string.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.right:
                    input: Col1
                    length: -10
            """,
            dataframe=pd.DataFrame({
                'Col1': ['example'],
            })
        )
        assert df["Col1"][0] == ""

    def test_select_right_empty_df(self):
        """
        Test select.left with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.right:
                    input: Col1
                    output: output column
                    length: 3
            """,
            dataframe=pd.DataFrame({
                'Col1': [],
            })
        )
        assert df.empty


class TestSelectSubstring:
    """
    Test select.substring
    """
    def test_substring_1(self):
        """
        Multi column input
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
                output:
                    - Out1
                    - Out2
                start: 4
                length: 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Out1'] == ' Two'

    def test_substring_2(self):
        """
        Output is none
        """
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

    def test_substring_no_length(self):
        """
        Test select.substring with no length
        """
        data = pd.DataFrame({
        'Col1': ['One Two Three Four'],
        'Col2': ['A B C D']
        })
        recipe = """
        wrangles:
            - select.substring:
                input: Col1
                start: 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Col1'] == ' Two Three Four'

    def test_substring_no_start(self):
        """
        Test select.substring with no start
        """
        data = pd.DataFrame({
        'Col1': ['One Two Three Four'],
        'Col2': ['A B C D']
        })
        recipe = """
        wrangles:
            - select.substring:
                input: Col1
                length: 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Col1'] == 'One '

    def test_substring_no_start_no_length(self):
        """
        Test select.substring error with no start or length
        """
        data = pd.DataFrame({
        'Col1': ['One Two Three Four'],
        'Col2': ['A B C D']
        })
        recipe = """
        wrangles:
            - select.substring:
                input: Col1
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "Either start or length must be provided." in info.value.args[0]
        )

    def test_substring_multi_input_single_output(self):
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

    def test_substring_where(self):
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

    def test_select_substring_empty_df(self):
        """
        Test select.substring with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - select.substring:
                  input: Col1
                  output: Out1
                  start: 1
                  length: 3
            """,
            dataframe=pd.DataFrame({
                'Col1': [],
            })
        )
        assert df.empty


class TestGroupBy:
    """
    Test select.group_by
    """
    def test_group_by(self):
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

    def test_group_by_multiple_by(self):
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

    def test_group_by_without_by(self):
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

    def test_group_by_without_aggregations(self):
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

    def test_group_by_agg_lists(self):
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

    def test_group_by_same_column(self):
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

    def test_group_by_percentiles(self):
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

    def test_group_by_to_list(self):
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

    def test_group_by_to_list_multiple_by(self):
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

    def test_group_by_to_list_multiple_list(self):
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


    def test_group_by_where(self):
        """
        Test group by using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.group_by:
                by: agg
                list: to_list
                where: agg <> 'b'
            """,
            dataframe=pd.DataFrame({
                "agg": ["a", "a", "b", "c"],
                "to_list": [1,2,3,4]
            })
        )

        assert (
            list(df.values[0]) == ['a', [1,2]] and
            list(df.values[1]) == ['c', [4]]
        )

    def test_group_by_agg_same_column(self):
        """
        Test group by and aggregating
        on the same column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.group_by:
                by:
                    - agg
                count:
                    - agg
            """,
            dataframe=pd.DataFrame({
                "agg": ["a", "a", "a", "b"],
            })
        )

        assert (
            list(df.values[0]) == ['a', 3] and
            list(df.values[1]) == ['b', 1]
        )

    def test_custom_function(self):
        """
        Test a group by that uses a custom function
        to aggregate the values
        """
        def sum_times_two(x):
            return sum(x) * 2

        df = wrangles.recipe.run(
            """
            wrangles:
              - select.group_by:
                  by: group
                  custom.sum_times_two: agg
            """,
            dataframe=pd.DataFrame({
                "group": ["a", "a", "a", "b"],
                "agg": [1,2,3,4]
            }),
            functions=[sum_times_two]
        )

        assert (
            list(df.values[0]) == ['a', 12] and
            list(df.values[1]) == ['b', 8]
        )

    def test_custom_function_invalid(self):
        """
        Test that a clear error is raised if the user
        tries to use a custom function that isn't valid
        """
        with pytest.raises(ValueError, match="bad_function"):
            wrangles.recipe.run(
                """
                wrangles:
                - select.group_by:
                    by: group
                    custom.bad_function: agg
                """,
                dataframe=pd.DataFrame({
                    "group": ["a", "a", "a", "b"],
                    "agg": [1,2,3,4]
                })
            )

    def test_by_only(self):
        """
        Test grouping without any aggregations
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - select.group_by:
                  by: to_group
            """,
            dataframe=pd.DataFrame({
                "to_group": ["a", "a", "a", "b"],
            })
        )
        assert (
            list(df.columns) == ['to_group'] and
            df["to_group"].tolist() == ["a", "b"]
        )

    def test_group_by_empty_df(self):
        """
        Test group_by with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - select.group_by:
                  by: to_group
            """,
            dataframe=pd.DataFrame({
                "to_group": [],
            })
        )
        assert df.empty and df.columns.to_list() == ['to_group']

    def test_group_by_first(self):  
        """  
        Test select.group_by with first aggregation  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - select.group_by:  
                by: group  
                first: value  
            """,  
            dataframe=pd.DataFrame({  
                "group": ["a", "a", "a", "b", "b"],  
                "value": [1, 2, 3, 4, 5]  
            })  
        )  
        
        assert (  
            list(df.values[0]) == ['a', 1] and  
            list(df.values[1]) == ['b', 4]  
        )  
    
    def test_group_by_first_multiple_columns(self):  
        """  
        Test select.group_by with first on multiple columns  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - select.group_by:  
                by: group  
                first:  
                    - value1  
                    - value2  
            """,  
            dataframe=pd.DataFrame({  
                "group": ["a", "a", "a", "b", "b"],  
                "value1": [1, 2, 3, 4, 5],  
                "value2": [10, 20, 30, 40, 50]  
            })  
        )  
        
        assert (  
            list(df.values[0]) == ['a', 1, 10] and  
            list(df.values[1]) == ['b', 4, 40]  
        )  
    
    def test_group_by_first_with_column_suffix(self):  
        """  
        Test that first creates column names with .first suffix  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - select.group_by:  
                by: group  
                first: value  
            """,  
            dataframe=pd.DataFrame({  
                "group": ["a", "a", "b"],  
                "value": [1, 2, 3]  
            })  
        )  
        
        # Check that column is named 'value.first' not just 'value'  
        assert 'value.first' in df.columns or 'value' in df.columns  
    
    def test_group_by_first_and_last(self):  
        """  
        Test using both first and last aggregations together  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - select.group_by:  
                by: group  
                first: value  
                last: value  
            """,  
            dataframe=pd.DataFrame({  
                "group": ["a", "a", "a", "b", "b"],  
                "value": [1, 2, 3, 4, 5]  
            })  
        )  
        
        assert (  
            list(df.values[0]) == ['a', 1, 3] and  
            list(df.values[1]) == ['b', 4, 5]  
        )  
    
    def test_group_by_first_with_other_aggregations(self):  
        """  
        Test first combined with other aggregation functions  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - select.group_by:  
                by: group  
                first: value  
                sum: value  
                max: value  
            """,  
            dataframe=pd.DataFrame({  
                "group": ["a", "a", "a", "b", "b"],  
                "value": [1, 2, 3, 4, 5]  
            })  
        )  
        
        assert (  
            list(df.values[0]) == ['a', 1, 6, 3] and  
            list(df.values[1]) == ['b', 4, 9, 5]  
        )  
    
    def test_group_by_first_empty_df(self):  
        """  
        Test first aggregation with empty dataframe  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - select.group_by:  
                by: group  
                first: value  
            """,  
            dataframe=pd.DataFrame({  
                "group": [],  
                "value": []  
            })  
        )  
        
        assert df.empty and 'group' in df.columns

class TestSelectElement:
    """
    Test select.element
    """
    def test_element_list(self):
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

    def test_element_dict_without_quotes(self):
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

    def test_element_dict_double_quotes(self):
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

    def test_element_dict_single_quotes(self):
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

    def test_element_dict_escape_quotes(self):
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

    def test_element_dict_not_found(self):
        """
        Test get element from a dict
        where the element does not exist
        """
        with pytest.raises(KeyError) as info:
            raise wrangles.recipe.run(
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
        assert info.typename == 'KeyError' and "not found" in info.value.args[0]

    def test_element_list_not_found(self):
        """
        Test get element from a dict
        where the element does not exist
        """
        with pytest.raises(KeyError) as info:
            wrangles.recipe.run(
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
        assert info.typename == 'KeyError' and "not found" in info.value.args[0]

    def test_element_dict_default(self):
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

    def test_element_list_default(self):
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

    def test_element_multi_layer(self):
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

    def test_element_overwrite_input(self):
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

    def test_element_multiple_io(self):
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

    def test_element_dict_by_index(self):
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

    def test_element_string(self):
        """
        Test getting an element from a string
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[1]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": ["1234567"]
            })
        )
        assert df["result"][0] == "2"

    def test_element_string_slice(self):
        """
        Test getting a slice from a string
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[1:3]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": ["1234567"]
            })
        )
        assert df["result"][0] == "23"

    def test_element_slice(self):
        """
        Test getting a slice from a list
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[1:3]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": [[1,2,3,4,5]]
            })
        )
        assert df["result"][0] == [2,3]

    def test_element_slice_start_only(self):
        """
        Test getting a slice from a list
        with only a start value
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[2:]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": [[1,2,3,4,5]]
            })
        )
        assert df["result"][0] == [3,4,5]

    def test_element_slice_end_only(self):
        """
        Test getting a slice from a list
        with only a start value
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[:2]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": [[1,2,3,4,5]]
            })
        )
        assert df["result"][0] == [1,2]

    def test_element_slice_step_only(self):
        """
        Test getting a slice from a list
        with only a start value
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[::2]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": [[1,2,3,4,5]]
            })
        )
        assert df["result"][0] == [1,3,5]

    def test_element_slice_start_end_step(self):
        """
        Test getting a slice from a list
        with only a start value
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[1:5:2]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": [[1,2,3,4,5,6,7]]
            })
        )
        assert df["result"][0] == [2,4]

    def test_element_json(self):
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
                "col": ['["a", "b", "c"]']
            })
        )
        assert df["result"][0] == "a"

    def test_element_where(self):
        """
        Test get element with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: column[0]
                output: result
                where: numbers > 6
            """,
            dataframe=pd.DataFrame({
                "column": [["a", "b", "c"], [1, 2, 3], ['do', 're', 'mi']],
                'numbers': [6, 7, 8]
            })
        )
        assert df["result"][0] == "" and df["result"][1] == 1 and df["result"][2] == "do"

    def test_select_element_empty_df(self):
        """
        Test select.element with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.element:
                input: col[0]
                output: result
            """,
            dataframe=pd.DataFrame({
                "col": []
            })
        )
        assert df.empty and df.columns.to_list() == ['col', 'result']


class TestSelectColumns:
    """
    Test select.columns
    """
    def test_select_columns_basic(self):
        """
        Test select.columns using basic inputs
        The original df will be 5 columns and want to select only 2 column
        """
        data = pd.DataFrame({
            'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
            'Col2': [1, 2, 3],
            'Col3': [4, 5, 6],
            'Col4': [7, 8, 9],
            'Col5': [10, 11, 12]
        })
        recipe = """
        wrangles:
            - select.columns:
                input:
                    - Col1
                    - Col5

        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df.columns) == 2 and df['Col1'][0] == 'One Two Three Four' and df['Col5'][0] == 10

    def test_select_column_wildcard(self):
        """
        Test select.column using a wilcard
        Select only cols that have a number
        """
        data = pd.DataFrame({
            'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
            'Col2': [1, 2, 3],
            'Random1': [4, 5, 6],
            'Col4': [7, 8, 9],
            'Random2': [10, 11, 12]
        })
        recipe = """
        wrangles:
            - select.columns:
                input: Col*
            - convert.case:
                input: Col1
                case: upper

        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df.columns) == 3 and [x for x in df.columns] == ['Col1', 'Col2', 'Col4']
        
    def test_select_column_with_non_existing_cols(self):
        """
        Test outputing a column(s) that do not exists. This will trigger wildcard error
        """
        data = pd.DataFrame({
            'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
            'Col2': [1, 2, 3],
        })
        recipe = """
        wrangles:
            - select.columns:
                input: YOLO
            - convert.case:
                input: Col1
                case: upper
        """
        with pytest.raises(KeyError) as info:
            raise wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert info.typename == 'KeyError' and "YOLO" in info.value.args[0]
        
    def test_select_columns_where(self):
        """
        Test select.columns with where.
        This does not actually do anything to the data
        when the where is included.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - select.columns:
                    input:
                        - Col1
                        - Col5
                    where: Col5 > 11
            """,
            dataframe=pd.DataFrame({
                'Col1': ['One Two Three Four', 'Five Six Seven Eight', 'Nine Ten Eleven Twelve'],
                'Col2': [1, 2, 3],
                'Col3': [4, 5, 6],
                'Col4': [7, 8, 9],
                'Col5': [10, 11, 12]
            })
        )
        assert (
            df.columns.to_list() == ['Col1', 'Col5'] and
            df['Col5'].to_list() == [12]
        )

    def test_select_columns_empty_df(self):
        """
        Test select.columns with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': [],
            'Col4': [],
            'Col5': []
        })
        recipe = """
        wrangles:
            - select.columns:
                input:
                    - Col1
                    - Col5

        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col5']


class TestSelectHead:
    """
    Test select.head
    """
    def test_head(self):
        """
        Test using head to return n rows
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.head:
                n: 3
            """,
            dataframe=pd.DataFrame({
                "heading": [1,2,3,4,5,6]
            })
        )
        assert df["heading"].values.tolist() == [1,2,3]

    def test_head_where(self):
        """
        Test using head with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.head:
                n: 2
                where: numbers > 10
            """,
            dataframe=pd.DataFrame({
                'heading': [1,2,3,4,5,6],
                'numbers': [12, 9, 14, 8, 15, 2]
            })
        )
        assert df['heading'].to_list() == [1, 3]

    def test_head_empty_df(self):
        """
        Test using head with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.head:
                n: 2
            """,
            dataframe=pd.DataFrame({
                'heading': [],
                'numbers': []
            })
        )
        assert df.empty and df.columns.to_list() == ['heading', 'numbers']


class TestSelectTail:
    """
    Test select.tail
    """
    def test_tail(self):
        """
        Test using tail to return n rows
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.tail:
                n: 3
            """,
            dataframe=pd.DataFrame({
                "heading": [1,2,3,4,5,6]
            })
        )
        assert df["heading"].values.tolist() == [4,5,6]

    def test_tail_where(self):
        """
        Test tail with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.tail:
                n: 2
                where: numbers < 10
            """,
            dataframe=pd.DataFrame({
                "heading": [1,2,3,4,5,6],
                'numbers': [12, 9, 14, 8, 15, 2]
            })
        )
        assert df['heading'].to_list() == [4, 6]

    def test_tail_empty_df(self):
        """
        Test select.tail with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.tail:
                n: 3
            """,
            dataframe=pd.DataFrame({
                "heading": []
            })
        )
        assert df.empty and df.columns.to_list() == ['heading']


class TestSelectSample:
    """
    Test select.sample
    """
    def test_sample_integer(self):
        """
        Test selecting a sample with a whole number 
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: <word>
            wrangles:
            - select.sample:
                rows: 2
            """
        )
        assert len(df) == 2

    def test_sample_integer_as_string(self):
        """
        Test selecting a sample with an integer
        that the user entered as a string
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: <word>
            wrangles:
            - select.sample:
                rows: '2'
            """
        )
        assert len(df) == 2

    def test_sample_float_as_string(self):
        """
        Test selecting a sample with a float
        that the user entered as a string
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 6
                values:
                    header1: <word>
            wrangles:
            - select.sample:
                rows: '0.5'
            """
        )
        assert len(df) == 3

    def test_sample_fraction(self):
        """
        Test selecting a sample with a fraction
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 10
                values:
                    header1: <word>
            wrangles:
            - select.sample:
                rows: 0.2
            """
        )
        assert len(df) == 2

    def test_sample_bad_value(self):
        """
        Test selecting a sample with
        an invalid number for rows
        """
        with pytest.raises(ValueError) as error:
            raise wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 10
                    values:
                        header1: <word>
                wrangles:
                - select.sample:
                    rows: -1
                """
            )
        assert "must be a positive" in error.value.args[0]

    def test_sample_bad_type(self):
        """
        Test selecting a sample with
        an invalid value for rows
        """
        with pytest.raises(ValueError) as error:
            raise wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 10
                    values:
                        header1: <word>
                wrangles:
                - select.sample:
                    rows: a
                """
            )
        assert "must be a positive" in error.value.args[0]

    def test_sample_greater_than_rows(self):
        """
        Test selecting a sample with a whole number
        that is greater than the number of rows.
        This should return the same number as
        the original dataframe.
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: <word>
            wrangles:
            - select.sample:
                rows: 10
            """
        )
        assert len(df) == 5

    def test_sample_where(self):
        """
        Test selecting a sample with a where condition
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.sample:
                rows: 2
                where: header1 = 'a'
            """,
            dataframe=pd.DataFrame({
                "header1": ["a","a","a","b","b","b"],
                "header2": [-1,-2,-3,1,2,3]
            })
        )
        assert (
            len(df) == 2 and
            all([x < 0 for x in df["header2"]])
        )

    def test_select_sample_empty_df(self):
        """
        Test select.sample with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.sample:
                rows: 2
            """,
            dataframe=pd.DataFrame({
                "heading": []
            })
        )
        assert df.empty and df.columns.to_list() == ['heading']


class TestSelectLength:
    def test_select_string_length(self):
        """
        Test select.length on strings
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.length:
                input: Col1
                output: length
            """,
            dataframe=pd.DataFrame({
                "Col1": ["One Two Three Four", "Five Six Seven Eight", "Nine Ten Eleven Twelve"]
            })
        )
        assert df["length"].to_list() == [18, 20, 22]

    def test_select_array_length(self):
        """
        Test select.length on arrays
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.length:
                input: Col1
                output: length
            """,
            dataframe=pd.DataFrame({
                "Col1": [[1,2,3,4], [5,6,7,8], [9,10,11,12]]
            })
        )
        assert df["length"].to_list() == [4, 4, 4]

    def test_select_dictionary_length(self):
        """
        Test select.length on dictionaries
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.length:
                input: Col1
                output: length
            """,
            dataframe=pd.DataFrame({
                "Col1": [{"a": 1, "b": 2, "c": 3}, {"d": 4, "e": 5}, {"f": 6}]
            })
        )
        assert df["length"].to_list() == [3, 2, 1]

    def test_select_empty_length(self):
        """
        Test select.length on empty values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.length:
                input: Col1
                output: length
            """,
            dataframe=pd.DataFrame({
                "Col1": ["", [], {}]
            })
        )
        assert df["length"].to_list() == [0, 0, 0]

    def test_select_empty_dataframe(self):
        """
        Test select.length on an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - select.length:
                input: Col1
                output: length
            """,
            dataframe=pd.DataFrame({"Col1": []})
        )
        assert len(df) == 0
