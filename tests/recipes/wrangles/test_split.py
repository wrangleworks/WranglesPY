import wrangles
import pandas as pd
import pytest


class TestSplitText:
    """
    Test split.text
    """

    def test_split_text_no_output(self):
        """
        Test overwriting the input
        if the output isn't set
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    col1: Wrangles,are,cool

            wrangles:
            - split.text:
                input: col1
            """
        )
        assert df["col1"][0] == ["Wrangles", "are", "cool"]

    def test_split_text_char(self):
        """
        Test setting the character to split on
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: Col1
                    char: ', '
            """,
            dataframe=pd.DataFrame({"Col1": ["Hello, Wrangles!"]}),
        )
        assert df.iloc[0]["Col1"] == ["Hello", "Wrangles!"]

    def test_split_text_wildcard_output(self):
        """
        Using a wildcard for output columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: Col
                    output: Col*
                    char: ', '
            """,
            dataframe=pd.DataFrame({"Col": ["Hello, Wrangles!"]}),
        )
        assert df.iloc[0]["Col2"] == "Wrangles!"

    def test_split_text_named_columns(self):
        """
        Multiple named columns as outputs - text to columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: Col
                output:
                - Col 1
                - Col 2
                - Col 3
            """,
            dataframe=pd.DataFrame({"Col": ["Hello,Wrangles!,Other"]}),
        )
        assert df.iloc[0]["Col 2"] == "Wrangles!"

    def test_split_text__regex_multichar(self):
        """
        Multiple character split
        """
        df = wrangles.recipe.run(
            r"""
            wrangles:
                - split.text:
                    input: col1
                    output: out1
                    char: 'regex: @|&|\$'
            """,
            dataframe=pd.DataFrame({"col1": ["Wrangles@are&very$cool"]}),
        )
        assert df.iloc[0]["out1"] == ["Wrangles", "are", "very", "cool"]

    def test_split_text_wildcard_multichar(self):
        """
        Multiple character split using wildcard (*)
        """
        df = wrangles.recipe.run(
            r"""
            wrangles:
                - split.text:
                    input: col1
                    output: out*
                    char: 'regex: @|&|\$'
            """,
            dataframe=pd.DataFrame({"col1": ["Wrangles@are&very$cool"]}),
        )
        assert df.iloc[0]["out4"] == "cool"

    def test_split_text_excess_columns(self):
        """
        If more columns than number of splits
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: 
                    - Out1
                    - Out2
                    - Out3
                    - Out4
                    - Out5
                    char: ' '
                    pad: True
            """,
            dataframe=pd.DataFrame({"col1": ["Wrangles are very cool"]}),
        )
        assert df["Out5"].iloc[0] == ""

    def test_split_text_more_splits_than_output(self):
        """
        Test split.text with more values after splitting than output columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: 
                    - Out1
                    - Out2
                    - Out3
                    char: ' '
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool, I tell you whut!"]}
            ),
        )
        assert (
            list(df.columns) == ["col1", "Out1", "Out2", "Out3"]
            and df["Out3"].iloc[0] == "very"
        )

    def test_split_text_uneven_lengths(self):
        """
        Test split.text with uneven split/output lengths
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: output*
                    char: ', '
            """,
            dataframe=pd.DataFrame(
                {
                    "col1": [
                        "Wrangles, are, very, cool",
                        "There, is, a, wrangle, for, that",
                    ]
                }
            ),
        )
        assert df["output6"].iloc[0] == "" and df["output6"].iloc[1] == "that"

    def test_split_text_where(self):
        """
        Test split.text using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: Col1
                    output: output
                    char: ', '
                    where: numbers > 4
            """,
            dataframe=pd.DataFrame(
                {
                    "Col1": ["Hello, Wrangles!", "Hello, World!", "Hola, Mundo!"],
                    "numbers": [4, 5, 6],
                }
            ),
        )
        assert df.iloc[2]["output"] == ["Hola", "Mundo!"] and df.iloc[0]["output"] == ""

    def test_split_text_where_wildcard(self):
        """
        Test split.text using where and a wildcard
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: Col1
                    output: output*
                    char: ', '
                    where: numbers > 4
            """,
            dataframe=pd.DataFrame(
                {
                    "Col1": ["Hello, Wrangles!", "Hello, World!", "Hola, Mundo!"],
                    "numbers": [4, 5, 6],
                }
            ),
        )
        assert df["output1"].to_list() == ["", "Hello", "Hola"] and df[
            "output2"
        ].to_list() == ["", "World!", "Mundo!"]

    def test_split_text_element_string(self):
        """
        Test a string passed into the element parameter
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: Out
                char: ' '
                element: '1'
            """,
            dataframe=pd.DataFrame({"col1": ["Wrangles are very cool"]}),
        )
        assert df["Out"].iloc[0] == "are"

    def test_split_text_element_integer(self):
        """
        Select element from the output list
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: Out
                    char: ' '
                    element: 0
            """,
            dataframe=pd.DataFrame({"col1": ["Wrangles are very cool"]}),
        )
        assert df.iloc[0]["Out"] == "Wrangles"

    def test_split_text_index_out_of_range(self):
        """
        Select element from the output that beyond the range
        Should give an empty value
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: Out
                    char: ' '
                    element: 100
            """,
            dataframe=pd.DataFrame({"col1": ["Wrangles are very cool"]}),
        )
        assert df.iloc[0]["Out"] == ""

    def test_split_text_slice(self):
        """
        Select element from the output list, using list slice
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: Out
                    char: ' '
                    element: '0:3'
            """,
            dataframe=pd.DataFrame({"col1": ["Wrangles are very cool"]}),
        )
        assert df.iloc[0]["Out"] == ["Wrangles", "are", "very"]

    def test_split_text_slice_start_only(self):
        """
        Test a string slice passed into the element parameter
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: Out
                char: ' '
                element: ':3'
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool and super fun to work with"]}
            ),
        )
        assert df["Out"].iloc[0] == ["Wrangles", "are", "very"]

    def test_split_text_slice_end_only(self):
        """
        Test a string slice passed into the element parameter
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: Out
                char: ' '
                element: '3:'
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool and super fun to work with"]}
            ),
        )
        assert df["Out"].iloc[0] == [
            "cool",
            "and",
            "super",
            "fun",
            "to",
            "work",
            "with",
        ]

    def test_split_text_slice_step(self):
        """
        Test a string slice passed into
        the element parameter with a step
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: Out
                char: ' '
                element: '1:5:2'
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool and super fun to work with"]}
            ),
        )
        assert df["Out"][0] == ["are", "cool"]

    def test_split_text_slice_columns_output(self):
        """
        Test a string slice passed into
        the element parameter with the output
        to columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output:
                - Out1
                - Out2
                char: ' '
                element: '2:4'
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool and super fun to work with"]}
            ),
        )
        assert df["Out1"][0] == "very" and df["Out2"][0] == "cool"

    def test_split_text_slice_columns_pad(self):
        """
        Test a string slice passed into
        the element parameter with pad True
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output:
                - Out1
                - Out2
                - Out3
                char: ' '
                element: '2:4'
                pad: True
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool and super fun to work with"]}
            ),
        )
        assert (
            df["Out1"][0] == "very" and df["Out2"][0] == "cool" and df["Out3"][0] == ""
        )

    def test_split_text_slice_reverse(self):
        """
        Test slicing the results using -1 step
        to give the results in reverse order
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output:
                - Out1
                - Out2
                - Out3
                char: ' '
                element: '::-1'
                pad: True
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool and super fun to work with"]}
            ),
        )
        assert (
            df["Out1"][0] == "with"
            and df["Out2"][0] == "work"
            and df["Out3"][0] == "to"
        )

    def test_split_text_slice_last_n(self):
        """
        Test slicing the last 2 values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output:
                - Out1
                - Out2
                char: ' '
                element: '-2:'
            """,
            dataframe=pd.DataFrame(
                {"col1": ["Wrangles are very cool and super fun to work with"]}
            ),
        )
        assert df["Out1"][0] == "work" and df["Out2"][0] == "with"

    def test_split_text_inclusive(self):
        """
        Tests split.text with inclusive set to True
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: out1
                    char: 'ga'
                    inclusive: True
            """,
            dataframe=pd.DataFrame({"col1": ["80ga 90ga 100ga"]}),
        )
        assert df["out1"].iloc[0] == ["80", "ga", " 90", "ga", " 100", "ga", ""]

    def test_split_text_regex(self):
        """
        Tests split.text using regex
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: out1
                    char: 'regex: (,|!)'
            """,
            dataframe=pd.DataFrame({"col1": ["Hello, Wrangles!"]}),
        )
        assert df["out1"].iloc[0][1] == "," and len(df["out1"].iloc[0]) == 5

    def test_split_text_pad_mismatch_error(self):
        """
        Test that an appropriate error is given to the user
        if the user sets pad: false and the length of the output
        does not match the number of columns.
        """
        with pytest.raises(ValueError, match="same length"):
            wrangles.recipe.run(
                """
                read:
                  - test:
                      rows: 1
                      values:
                        col1: "wrangles,are,cool"
                wrangles:
                  - split.text:
                      input: col1
                      output:
                        - out1
                        - out2
                        - out3
                        - out4
                      pad: False
                """
            )

    def test_split_text_regex_case_insensitive(self):
        """
        Tests split.text using regex with
        the case insensitive flag
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    char: 'regex:(?i)x'
            """,
            dataframe=pd.DataFrame({"col1": ["1x2", "1X2"]}),
        )
        assert df["col1"][0] == ["1", "2"] and df["col1"][1] == ["1", "2"]

    def test_split_text_wildcard_list_output(self):
        """
        Test split.text with a wildcard list for output
        """
        df = wrangles.recipe.run(
            r"""
            wrangles:
                - split.text:
                    input: col1
                    output: 
                      - out*
                    char: ' '
            """,
            dataframe=pd.DataFrame({"col1": ["This is a string that will be split"]}),
        )
        assert len(df.columns.to_list()) == 9 and df.iloc[0]["out4"] == "string"

    def test_split_text_empty(self):
        """
        Test split.text with an empty string
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.text:
                    input: col1
                    output: out1
                    char: ' '
            """,
            dataframe=pd.DataFrame({"col1": []}),
        )
        assert df.empty and df.columns.to_list() == ["col1", "out1"]

    def test_split_text_skip_empty_true(self):
        """
        Test split.text with skip_empty: true skips empty tokens
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: out
                char: ','
                skip_empty: true
            """,
            dataframe=pd.DataFrame({"col1": ["a,,b, ,c,,"]}),
        )
        assert df["out"][0] == ["a", "b", "c"]

    def test_split_text_skip_empty_false(self):
        """
        Test split.text with skip_empty: false includes empty tokens
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: out
                char: ','
                skip_empty: false
            """,
            dataframe=pd.DataFrame({"col1": ["a,,b, ,c,,"]}),
        )
        assert df["out"][0] == ["a", "", "b", " ", "c", "", ""]

    def test_split_text_skip_empty_default(self):
        """
        Test split.text with skip_empty not set (should include empty tokens by default)
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: out
                char: ','
            """,
            dataframe=pd.DataFrame({"col1": ["a,,b, ,c,,"]}),
        )
        assert df["out"][0] == ["a", "", "b", " ", "c", "", ""]

    def test_split_text_skip_empty_all_empty(self):
        """
        Test split.text with skip_empty: true and all tokens empty
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: out
                char: ','
                skip_empty: true
            """,
            dataframe=pd.DataFrame({"col1": [",,,"]}),
        )
        assert df["out"][0] == []

    def test_split_text_skip_empty_leading_trailing(self):
        """
        Test split.text with skip_empty: true and leading/trailing delimiters
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.text:
                input: col1
                output: out
                char: ','
                skip_empty: true
            """,
            dataframe=pd.DataFrame({"col1": [",a,b,"]}),
        )
        assert df["out"][0] == ["a", "b"]


class TestSplitList:
    """
    Test split.list
    """

    def test_split_list_1(self):
        """
        Using Wild Card
        """
        data = pd.DataFrame({"Col": [["Hello", "Wrangles!"]]})
        recipe = """
        wrangles:
            - split.list:
                input: Col
                output: Col*
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]["Col2"] == "Wrangles!"

    def test_split_list_json(self):
        """
        Test the split.list function with a JSON string
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.list:
                    input: Col
                    output: Col*
            """,
            dataframe=pd.DataFrame({"Col": ['["Hello", "Wrangles!"]']}),
        )
        assert df["Col2"][0] == "Wrangles!"

    def test_split_list_2(self):
        """
        Multiple column named outputs
        """
        data = pd.DataFrame({"col1": [["Hello", "Wrangles!"]]})
        recipe = """
        wrangles:
        - split.list:
            input: col1
            output:
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]["out2"] == "Wrangles!"

    def test_split_list_where(self):
        """
        Test split.list using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.list:
                    input: Col
                    output: Col*
                    where: numbers > 4
            """,
            dataframe=pd.DataFrame(
                {
                    "Col": [
                        ["Hello", "Wrangles!"],
                        ["Hola", "Mundo!"],
                        ["Bonjour", "Monde!"],
                    ],
                    "numbers": [4, 5, 6],
                }
            ),
        )
        assert df["Col1"].to_list() == ["", "Hola", "Bonjour"] and df[
            "Col2"
        ].to_list() == ["", "Mundo!", "Monde!"]

    def test_split_list_wildcard(self):
        """
        Test the split.list function using a wildcard output
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.list:
                    input: Col
                    output: Col*
            """,
            dataframe=pd.DataFrame({"Col": [["Hello", "Wrangles!", "and", "World!"]]}),
        )
        assert len(df.columns.to_list()) == 5 and df["Col2"][0] == "Wrangles!"

    def test_split_list_wildcard_list(self):
        """
        Test the split.list function using a
        wildcard output as a list
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.list:
                    input: Col
                    output: 
                      - Col*
            """,
            dataframe=pd.DataFrame({"Col": [["Hello", "Wrangles!", "and", "World!"]]}),
        )
        assert len(df.columns.to_list()) == 5 and df["Col2"][0] == "Wrangles!"

    def test_split_list_empty(self):
        """
        Test split.list with an empty column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.list:
                    input: Col
                    output: output*
            """,
            dataframe=pd.DataFrame({"Col": []}),
        )
        assert df.empty and df.columns.to_list() == ["Col"]

    def test_split_list_empty_where(self):
        """
        Test split.list with an empty where result
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.list:
                    input: Col
                    output: Col*
                    where: numbers > 4
            """,
            dataframe=pd.DataFrame({"Col": ["Hello", "Wrangles!"], "numbers": [4, 3]}),
        )
        assert list(df.columns) == ["Col", "numbers"] and len(df) == 2


class TestSplitDictionary:
    """
    Test split.dictionary
    """

    def test_split_dictionary(self):
        """
        Test splitting a dictionary
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
            """,
            dataframe=pd.DataFrame({"col1": [{"Col1": "A", "Col2": "B", "Col3": "C"}]}),
        )
        assert df["Col2"][0] == "B"

    def test_split_dictionary_json(self):
        """
        Test splitting a dictionary that is
        actually a JSON string
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
            """,
            dataframe=pd.DataFrame(
                {"col1": ['{"Col1": "A", "Col2": "B", "Col3": "C"}']}
            ),
        )
        assert df["Col2"][0] == "B"

    def test_split_dictionary_where(self):
        """
        Test split.dictionary using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                where: numbers > 3
            """,
            dataframe=pd.DataFrame(
                {
                    "col1": [
                        {"Col1": "A", "Col2": "B", "Col3": "C"},
                        {"Col1": "D", "Col2": "E", "Col3": "F"},
                        {"Col1": "G", "Col2": "H", "Col3": "I"},
                    ],
                    "numbers": [3, 4, 5],
                }
            ),
        )
        assert df["Col2"][1] == "E" and df["Col2"][0] == ""

    def test_split_dictionary_default(self):
        """
        Test splitting a dictionary with default values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                default:
                    Col2: X
                    Col4: D
            """,
            dataframe=pd.DataFrame({"col1": [{"Col1": "A", "Col2": "B", "Col3": "C"}]}),
        )
        assert df["Col2"][0] == "B" and df["Col4"][0] == "D"

    def test_split_dictionary_multiple(self):
        """
        Test splitting a list of dictionaries
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: 
                    - col1
                    - col2
            """,
            dataframe=pd.DataFrame(
                {
                    "col1": [{"Col1": "A", "Col2": "B", "Col3": "C"}],
                    "col2": [{"Col4": "D", "Col5": "E", "Col6": "F"}],
                }
            ),
        )
        assert df["Col2"][0] == "B" and df["Col4"][0] == "D"

    def test_split_dictionary_multiple_duplicates(self):
        """
        Test splitting a list of dictionaries with duplicate keys
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: 
                    - col1
                    - col2
            """,
            dataframe=pd.DataFrame(
                {
                    "col1": [{"Col1": "A", "Col2": "B", "Col3": "C"}],
                    "col2": [{"Col3": "D", "Col4": "E", "Col5": "F"}],
                }
            ),
        )
        assert df["Col3"][0] == "D"

    def test_split_dictionary_output_single(self):
        """
        Test splitting a dictionary and
        specifying a single key to output
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output: Out1
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}),
        )
        assert df.columns.tolist() == ["col1", "Out1"] and df["Out1"][0] == "A"

    def test_split_dictionary_output_list(self):
        """
        Test splitting a dictionary and
        specifying a list of keys to output
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - Out1
                    - Out2
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}),
        )
        assert (
            df.columns.tolist() == ["col1", "Out1", "Out2"]
            and df["Out1"][0] == "A"
            and df["Out2"][0] == "B"
        )

    def test_split_dictionary_output_rename(self):
        """
        Test splitting a dictionary and
        specifying a list of keys to output
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - Out1: Renamed1
                    - Out2
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}),
        )
        assert (
            df.columns.tolist() == ["col1", "Renamed1", "Out2"]
            and df["Renamed1"][0] == "A"
            and df["Out2"][0] == "B"
        )

    def test_split_dictionary_output_rename(self):
        """
        Test splitting a dictionary and
        renaming an output column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - Out1: Renamed1
                    - Out2
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}),
        )
        assert (
            df.columns.tolist() == ["col1", "Renamed1", "Out2"]
            and df["Renamed1"][0] == "A"
            and df["Out2"][0] == "B"
        )

    def test_split_dictionary_output_rename_single(self):
        """
        Test splitting a dictionary and
        renaming the output column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    Out1: Renamed1
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}),
        )
        assert df.columns.tolist() == ["col1", "Renamed1"] and df["Renamed1"][0] == "A"

    def test_split_dictionary_output_wildcard(self):
        """
        Test splitting a dictionary and
        setting the output columns using a wildcard
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output: Out*
            """,
            dataframe=pd.DataFrame(
                {"col1": [{"Out1": "A", "Out2": "B", "NotOut3": "C"}]}
            ),
        )
        assert (
            df.columns.tolist() == ["col1", "Out1", "Out2"]
            and df["Out1"][0] == "A"
            and df["Out2"][0] == "B"
        )

    def test_split_dictionary_output_rename_wildcard(self):
        """
        Test splitting a dictionary and
        renaming the output columns using wildcards
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - Out*: Renamed*
                    - NotModified
            """,
            dataframe=pd.DataFrame(
                {"col1": [{"Out1": "A", "Out2": "B", "NotModified": "C"}]}
            ),
        )
        assert (
            df.columns.tolist() == ["col1", "Renamed1", "Renamed2", "NotModified"]
            and df["Renamed1"][0] == "A"
            and df["Renamed2"][0] == "B"
            and df["NotModified"][0] == "C"
        )

    def test_split_dictionary_output_rename_suffix(self):
        """
        Test splitting a dictionary and
        renaming the output columns using wildcards
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - "*": "*_SUFFIX"
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B"}]}),
        )
        assert (
            df.columns.tolist() == ["col1", "Out1_SUFFIX", "Out2_SUFFIX"]
            and df["Out1_SUFFIX"][0] == "A"
            and df["Out2_SUFFIX"][0] == "B"
        )

    def test_split_dictionary_output_rename_all_wildcard(self):
        """
        Test splitting a dictionary and
        using a wildcard to select all other columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - Out*: Renamed*
                    - "*"
            """,
            dataframe=pd.DataFrame(
                {"col1": [{"Out1": "A", "Out2": "B", "NotModified": "C"}]}
            ),
        )
        assert (
            df.columns.tolist() == ["col1", "Renamed1", "Renamed2", "NotModified"]
            and df["Renamed1"][0] == "A"
            and df["Renamed2"][0] == "B"
            and df["NotModified"][0] == "C"
        )

    def test_split_dictionary_output_multiple_wildcards(self):
        """
        Test splitting a dictionary and
        setting the output columns using
        a string with multiple wildcards
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output: "*_Out_*"
            """,
            dataframe=pd.DataFrame(
                {"col1": [{"1_Out_1": "A", "2_Out_2": "B", "NotOut3": "C"}]}
            ),
        )
        assert (
            df.columns.tolist() == ["col1", "1_Out_1", "2_Out_2"]
            and df["1_Out_1"][0] == "A"
            and df["2_Out_2"][0] == "B"
        )

    def test_split_dictionary_output_rename_multiple_wildcards(self):
        """
        Test splitting a dictionary and
        renaming the columns using multiple wildcards
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - "*_Out_*": "*_Renamed_*"
            """,
            dataframe=pd.DataFrame(
                {"col1": [{"1_Out_2": "A", "3_Out_4": "B", "NotOut3": "C"}]}
            ),
        )
        assert (
            df.columns.tolist() == ["col1", "1_Renamed_2", "3_Renamed_4"]
            and df["1_Renamed_2"][0] == "A"
            and df["3_Renamed_4"][0] == "B"
        )

    def test_split_dictionary_output_regex(self):
        """
        Test splitting a dictionary and
        setting the output columns using regex
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.dictionary:
                input: col1
                output: "regex:Out[1-2]"
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}),
        )
        assert (
            df.columns.tolist() == ["col1", "Out1", "Out2"]
            and df["Out1"][0] == "A"
            and df["Out2"][0] == "B"
        )

    def test_split_dictionary_output_regex_rename(self):
        """
        Test splitting a dictionary and
        renaming column using regex
        """
        df = wrangles.recipe.run(
            r"""
            wrangles:
            - split.dictionary:
                input: col1
                output:
                    - "regex:Out([1-2])": "Renamed\\1"
            """,
            dataframe=pd.DataFrame({"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}),
        )
        assert (
            df.columns.tolist() == ["col1", "Renamed1", "Renamed2"]
            and df["Renamed1"][0] == "A"
            and df["Renamed2"][0] == "B"
        )

    def test_split_dictionary_output_regex_missing_capture(self):
        """
        Test splitting a dictionary and
        setting the output columns using regex
        """
        with pytest.raises(ValueError, match="capture group"):
            wrangles.recipe.run(
                r"""
                wrangles:
                - split.dictionary:
                    input: col1
                    output:
                        - "regex:Out[1-2]": "Renamed\\1"
                """,
                dataframe=pd.DataFrame(
                    {"col1": [{"Out1": "A", "Out2": "B", "Out3": "C"}]}
                ),
            )

    def test_split_dictionary_empty(self):
        """
        Test split.dictionary with an empty column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.dictionary:
                    input: Col
            """,
            dataframe=pd.DataFrame({"Col": []}),
        )
        assert df.empty and df.columns.to_list() == ["Col"]


class TestTokenize:
    """
    Test split.tokenize
    """

    def test_tokenize_1(self):
        data = pd.DataFrame(
            {
                "col1": [["Stainless Steel", "Oak Wood"]],
            }
        )
        recipe = """
        wrangles:
        - split.tokenize:
            input: col1
            output: out1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]["out1"][2] == "Oak"

    def test_tokenize_2(self):
        """
        Input is a str
        """
        data = pd.DataFrame({"col1": ["Stainless Steel"]})
        recipe = """
        wrangles:
        - split.tokenize:
            input: col1
            output: out1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]["out1"][1] == "Steel"

    def test_tokenize_3(self):
        """
        If the input is multiple columns (a list)
        """
        data = pd.DataFrame(
            {
                "col1": ["Iron Man"],
                "col2": ["Spider Man"],
            }
        )
        recipe = """
        wrangles:
        - split.tokenize:
            input:
                - col1
                - col2
            output:
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]["out1"][1] == "Man"

    def test_tokenize_4(self):
        """
        If the input and output are not the same
        If the input is multiple columns (a list)
        """
        data = pd.DataFrame(
            {
                "col1": ["Iron Man"],
                "col2": ["Spider Man"],
            }
        )
        recipe = """
        wrangles:
        - split.tokenize:
            input:
                - col1
                - col2
            output: out1
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == "ValueError"
            and "The list of inputs and outputs must be the same length for split.tokenize"
            in info.value.args[0]
        )

    def test_tokenize_where(self):
        """
        Test split.tokenize using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - split.tokenize:
                input: col1
                output: out1
                where: numbers >= 3
            """,
            dataframe=pd.DataFrame(
                {
                    "col1": [
                        ["Stainless Steel", "Oak Wood"],
                        ["Titanium", "Cedar Wood"],
                        ["Aluminum", "Teak Wood"],
                    ],
                    "numbers": [2, 3, 4],
                    "out1": ["Not Overwritten", "Overwritten", "Overwritten"],
                }
            ),
        )
        assert df["out1"].to_list() == [
            "Not Overwritten",
            ["Titanium", "Cedar", "Wood"],
            ["Aluminum", "Teak", "Wood"],
        ]

    def test_boundary(self):
        """
        Test using the boundary method
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  header: >-
                    "What is the meaning of life, the universe, and everything?"
            wrangles:
            - split.tokenize:
                input: header
                method: boundary
            """
        )
        assert df["header"][0][:15] == [
            '"',
            "What",
            " ",
            "is",
            " ",
            "the",
            " ",
            "meaning",
            " ",
            "of",
            " ",
            "life",
            ",",
            " ",
            "the",
        ]

    def test_boundary_without_spaces(self):
        """
        Test using the boundary ignore space method
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  header: >-
                    "What is the meaning of life, the universe, and everything?"
            wrangles:
            - split.tokenize:
                input: header
                method: boundary_ignore_space
            """
        )
        assert df["header"][0][:9] == [
            '"',
            "What",
            "is",
            "the",
            "meaning",
            "of",
            "life",
            ",",
            "the",
        ]

    def test_custom_function(self):
        """
        Test using a custom function
        """

        def func(value):
            return value.split("a")

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  header: >-
                    "What is the meaning of life, the universe, and everything?"
            wrangles:
            - split.tokenize:
                input: header
                method: custom.func
            """,
            functions=func,
        )
        assert df["header"][0] == [
            '"Wh',
            "t is the me",
            "ning of life, the universe, ",
            'nd everything?"',
        ]

    def test_regex(self):
        """
        Test using a regex pattern
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  header: >-
                    "What is the meaning of life, the universe, and everything?"
            wrangles:
            - split.tokenize:
                input: header
                method: regex:[wsg]
            """
        )
        assert df["header"][0] == [
            '"What i',
            " the meanin",
            " of life, the univer",
            "e, and everythin",
            '?"',
        ]

    def test_invalid_method(self):
        """
        Ensure a clear error is given if an invalid method is provided
        """
        with pytest.raises(ValueError, match="Method must be one of"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1
                    values:
                      header: string
                wrangles:
                - split.tokenize:
                    input: header
                    method: invalid_value
                """
            )

    def test_token_empty(self):
        """
        Test split.tokenize with an empty column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - split.tokenize:
                    input: Col
                    output: out1
            """,
            dataframe=pd.DataFrame({"Col": []}),
        )
        assert df.empty and df.columns.to_list() == ["Col", "out1"]
