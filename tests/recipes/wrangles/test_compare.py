import wrangles
import pandas as pd
import numpy as np


class TestCompareList:
    """
    Test compare.list
    """

    def test_compare_lists_integers_intersection(self):
        """
        Test compare.lists with integer lists using intersection method.
        """
        data = pd.DataFrame({"a": [[1, 2, 3], [4, 5, 6]], "b": [[2, 3, 4], [5, 6, 7]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: intersection
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[2, 3], [5, 6]]

    def test_compare_lists_integers_difference(self):
        """
        Test compare.lists with integer lists using difference method.
        """
        data = pd.DataFrame({"a": [[1, 2, 3], [4, 5, 6]], "b": [[2, 3, 4], [5, 6, 7]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: difference
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[1], [4]]

    def test_compare_lists_bools_intersection(self):
        """
        Test compare.lists with boolean lists using intersection method.
        """
        data = pd.DataFrame({"a": [[True, False], [True]], "b": [[False, True], [False]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: intersection
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[True, False], []]

    def test_compare_lists_bools_difference(self):
        """
        Test compare.lists with boolean lists using difference method.
        """
        data = pd.DataFrame({"a": [[True, False], [True]], "b": [[False, True], [False]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: difference
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[], [True]]

    def test_compare_lists_of_lists_intersection(self):
        """
        Test compare.lists with lists of lists using intersection method.
        """
        data = pd.DataFrame({"a": [[[1,2],[3,4]], [[5,6]]], "b": [[[1,2],[4,3]], [[6,5]]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: intersection
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[[1,2]], []]

    def test_compare_lists_of_lists_difference(self):
        """
        Test compare.lists with lists of lists using difference method.
        """
        data = pd.DataFrame({"a": [[[1,2],[3,4]], [[5,6]]], "b": [[[1,2],[4,3]], [[6,5]]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: difference
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[[3,4]], [[5,6]]]

    def test_compare_lists_of_dicts_intersection(self):
        """
        Test compare.lists with lists of dicts using intersection method.
        """
        data = pd.DataFrame({"a": [[{"x":1},{"y":2}]], "b": [[{"x":1},{"y":3}]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: intersection
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[{"x":1}]]

    def test_compare_lists_of_dicts_difference(self):
        """
        Test compare.lists with lists of dicts using difference method.
        """
        data = pd.DataFrame({"a": [[{"x":1},{"y":2}]], "b": [[{"x":1},{"y":3}]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: difference
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"].tolist() == [[{"y":2}]]

    def test_compare_lists_mixed_types_intersection(self):
        """
        Test compare.lists with mixed types using intersection method.
        """
        data = pd.DataFrame({"a": [[1, '2', True]], "b": [[1, 2, 1]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: intersection
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        # Only 1 is equal (True == 1 in Python)
        assert df["result"].tolist() == [[1, True]]

    def test_compare_lists_mixed_types_difference(self):
        """
        Test compare.lists with mixed types using difference method.
        """
        data = pd.DataFrame({"a": [[1, '2', True]], "b": [[1, 2, 1]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: difference
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        # Only '2' is not in b
        assert df["result"].tolist() == [['2']]

    def test_compare_lists_not_lists(self):
        """
        Test error is raised if input columns are not lists.
        """
        data = pd.DataFrame({"a": [123], "b": [123]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a, b]
            output: result
            method: intersection
        """
        try:
            wrangles.recipe.run(recipe, dataframe=data)
            assert False, "Should raise an error if input columns are not lists"
        except Exception:
            pass

    def test_compare_lists_one_column(self):
        """
        Test error is raised if only one column is passed to compare.lists.
        """
        data = pd.DataFrame({"a": [[1, 2, 3]]})
        recipe = """
        wrangles:
        - compare.lists:
            input: [a]
            output: result
            method: intersection
        """
        try:
            wrangles.recipe.run(recipe, dataframe=data)
            assert False, "Should raise an error if only one column is passed"
        except Exception:
            pass

    def test_compare_lists_intersection(self):
        """
        Test compare.lists with intersection method and string lists.
        """
        """
        Test compare.lists with intersection method
        """
        data = pd.DataFrame(
            {
                "list1": [["A", "B", "C"], ["X", "Y", "Z"]],
                "list2": [["B", "C", "D"], ["Y", "W", "V"]],
            }
        )
        recipe = """  
        wrangles:  
            - compare.lists:  
                input: [list1, list2]  
                output: result  
                method: intersection  
        """
        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df["result"][0] == ["B", "C"] and df["result"][1] == ["Y"]

    def test_compare_lists_difference(self):
        """
        Test compare.lists with difference method and string lists.
        """
        """
        Test compare.lists with difference method
        """
        data = pd.DataFrame(
            {
                "list1": [["A", "B", "C"], ["X", "Y", "Z"]],
                "list2": [["B", "C", "D"], ["Y", "W", "V"]],
            }
        )
        recipe = """  
        wrangles:  
        - compare.lists:  
            input: [list1, list2]  
            output: result  
            method: difference  
        """
        df = wrangles.recipe.run(recipe, dataframe=data)

        assert df["result"][0] == ["A"] and df["result"][1] == ["X", "Z"]

    def test_compare_lists_multiple_lists(self):
        """
        Test compare.lists with more than two lists (first is main).
        """
        """
        Test compare.lists with multiple lists (first is main)
        """
        data = pd.DataFrame(
            {
                "list1": [["A", "B", "C", "D"]],
                "list2": [["B", "C", "E"]],
                "list3": [["C", "F"]],
            }
        )
        recipe = """  
        wrangles:  
        - compare.lists:  
            input: [list1, list2, list3]  
            output: result  
            method: difference  
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["result"][0] == ["A", "D"]

    def test_compare_lists_ignore_case(self):
        """
        Test compare.lists with ignore_case=true for case-insensitive comparison.
        """
        """
        Test compare.lists with ignore_case=true
        """
        data = pd.DataFrame({"list1": [["A", "b", "C"]], "list2": [["a", "B", "d"]]})
        recipe = """  
        wrangles:  
        - compare.lists:  
            input: [list1, list2]  
            output: result  
            method: intersection  
            ignore_case: true  
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert set(df["result"][0]) == {"a", "b"}

class TestCompareText:
    """
    Test compare.text
    """

    def test_compare_text_default(self):
        """
        Test normal Compare Text. Difference (default)
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario Oak Wood White Marble Top Bookshelf",
                    "Luigi Oak Wood White Marble Top Coffee Table",
                    "Peach Oak Wood White Marble Top Console Table",
                ],
                "col2": [
                    "Mario Pine Wood Black Marble Bottom Bookshelf",
                    "Luigi Maple Wood Orange Steel Top Coffee Table",
                    "Peach Normal Wood Blue Plastic Top Console Table",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == [
            "Pine Black Bottom",
            "Maple Orange Steel",
            "Normal Blue Plastic",
        ]

    def test_compare_test_difference_simple_words(self):
        """
        Test with simple words
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario",
                    "Luigi",
                ],
                "col2": [
                    "Super Mario",
                    "Super Luigi",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["Super", "Super"]

    def test_compare_text_intersection(self):
        """
        Test normal Compare Text. Intersection
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario Oak Wood White Marble Top Bookshelf",
                    "Luigi Oak Wood White Marble Top Coffee Table",
                    "Peach Oak Wood White Marble Top Console Table",
                ],
                "col2": [
                    "Mario Pine Wood Black Marble Bottom Bookshelf",
                    "Luigi Maple Wood Orange Steel Top Coffee Table",
                    "Peach Normal Wood Blue Plastic Top Console Table",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == [
            "Mario Wood Marble Bookshelf",
            "Luigi Wood Top Coffee Table",
            "Peach Wood Top Console Table",
        ]

    def test_compare_text_intersection_simple_words(self):
        """
        Test with simple words
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario",
                    "Luigi",
                ],
                "col2": [
                    "Super Mario",
                    "Super Luigi",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["Mario", "Luigi"]

    def test_compare_text_empty_value_second_column(self):
        """
        Having an empty value in second column
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario Oak Wood White Marble Top Bookshelf",
                    "Peach Oak Wood White Marble Top Console Table",
                ],
                "col2": [
                    "Mario Pine Wood Black Marble Bottom Bookshelf",
                    "",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["Mario Wood Marble Bookshelf", ""]

    def test_compare_text_intersection_multiple_columns(self):
        """
        Test intersection with more than two columns
        """
        data = pd.DataFrame(
            {
                "col1": ["mario", "luigi", "peach", "toad"],
                "col2": ["super mario", "super luigi", "super peach", "super toad"],
                "col3": ["mega mario", "mega luigi", "mega peach", "mega toad"],
            }
        )
        recipe = """
        wrangles:
        - compare.text:
            input:
                - col1
                - col2
                - col3
            output: output
            method: intersection
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df["output"].values.tolist() == ["mario", "luigi", "peach", "toad"]

    def test_compare_text_intersection_empty_values(self):
        """
        Having empty values in the columns
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario", "Luigi", "", "Bowser", ""],
                "col2": ["Super Mario", "Super Luigi", "Super Peach", "", ""],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["Mario", "Luigi", "", "", ""]

    def test_compare_text_difference_multiple_columns(self):
        """
        Test difference with more than two columns
        """
        data = pd.DataFrame(
            {
                "col1": ["mario", "luigi", "peach", "toad"],
                "col2": ["super mario", "super luigi", "super peach", "super toad"],
                "col3": ["mega mario", "mega luigi", "mega peach", "mega toad"],
            }
        )
        recipe = """
        wrangles:
        - compare.text:
            input:
                - col1
                - col2
                - col3
            output: output
            method: difference
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert all(x == "super mega" for x in df["output"].values.tolist())

    def test_compare_text_difference_empty_values(self):
        """
        Having empty values in the columns
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario", "Luigi", "", "Bowser", ""],
                "col2": ["Super Mario", "Super Luigi", "Super Peach", "", ""],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["Super", "Super", "Super Peach", "", ""]

    def test_compare_text_empty_value_first_column(self):
        """
        Having an empty value in the first column should return the whole value of the second column
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario Oak Wood White Marble Top Bookshelf",
                    "",
                ],
                "col2": [
                    "Mario Pine Wood Black Marble Bottom Bookshelf",
                    "Peach Oak Wood White Marble Top Console Table",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == [
            "Pine Black Bottom",
            "Peach Oak Wood White Marble Top Console Table",
        ]

    def test_compare_text_overlap(self):
        """
        Using overlap method
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario",
                    "Luigi",
                ],
                "col2": [
                    "SuperMario",
                    "SuperLuigi",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["*****Mario", "*****Luigi"]

    def test_compare_text_overlap_empty_values(self):
        """
        Using overlap method and having empty values
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario", "Luigi", "", "Bowser", ""],
                "col2": ["SuperMario", "SuperLuigi", "SuperPeach", "", ""],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output:
            - output_mask
            - output_ratio
            method: overlap
            non_match_char: '@'
            include_ratio: True
            decimal_places: 2
            exact_match: 'They are the same'
            empty_a: 'Empty A'
            empty_b: 'Empty B'
            all_empty: 'Both Empty'
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output_mask"].values.tolist() == [
            "@@@@@Mario",
            "@@@@@Luigi",
            "Empty A",
            "Empty B",
            "Both Empty",
        ]
        assert df["output_ratio"].values.tolist() == [0.67, 0.67, 0, 0, 0]

    def test_compare_text_overlap_include_ratio(self):
        """
        Using overlap method and including the ratio
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "Mario",
                    "Luigi",
                    "Mario",
                    "Luigi",
                ],
                "col2": [
                    "Mario",
                    "Luigi",
                    "Martio",
                    "Luiigi",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output:
            - output_mask
            - output_ratio
            method: overlap
            include_ratio: True
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )

        assert df["output_mask"].values.tolist() == ["Mario", "Luigi", "Mar*io", "Lui*gi"]
        assert df["output_ratio"].values.tolist() == [1, 1, 0.909, 0.909]

    def test_compare_overlap_default_settings(self):
        """
        Using overlap method and using the default empty values
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario", "Luigi", "", "Bowser", ""],
                "col2": ["SuperMario", "SuperLuigi", "SuperPeach", "", ""],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["*****Mario", "*****Luigi", "", "", ""]

    def test_compare_text_where(self):
        """
        Test Compare Text using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - compare.text:
                input:
                - col1
                - col2
                output: output
                method: difference
                where: col3 == 'Yes'
            """,
            dataframe=pd.DataFrame(
                {
                    "col1": [
                        "Mario Oak Wood White Marble Top Bookshelf",
                        "Luigi Oak Wood White Marble Top Coffee Table",
                        "Peach Oak Wood White Marble Top Console Table",
                    ],
                    "col2": [
                        "Mario Pine Wood Black Marble Bottom Bookshelf",
                        "Luigi Maple Wood Orange Steel Top Coffee Table",
                        "Peach Normal Wood Blue Plastic Top Console Table",
                    ],
                    "col3": ["Yes", "No", "Yes"],
                }
            ),
        )
        assert (
            df["output"][0] == "Pine Black Bottom"
            and df["output"][1] == ""
            and df["output"][2] == "Normal Blue Plastic"
        )

    def test_compare_text_where_empty_values(self):
        """
        Test Compare Text with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - compare.text:
                input:
                - col1
                - col2
                output: output
                method: difference
            """,
            dataframe=pd.DataFrame({"col1": [], "col2": [], "col3": []}),
        )

        assert df.empty and df.columns.to_list() == ["col1", "col2", "col3", "output"]

    def test_compare_text_case_insensitive_difference(self):
        """
        Test compare using case insensitive difference
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "THIS IS IN ALL CAPS",
                    "ANOTHER LINE THAT IS ALSO IN CAPS",
                    "YET ANOTHER LINE IN CAPS",
                ],
                "col2": [
                    "this is in all lowercase",
                    "another line that is also in lowercase",
                    "yet another line in lowercase",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
            case_sensitive: false
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == ["lowercase", "lowercase", "lowercase"]

    def test_compare_text_case_insensitive_intersection(self):
        """
        Test compare using case insensitive intersection
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "THIS IS IN ALL CAPS",
                    "ANOTHER LINE THAT IS ALSO IN CAPS",
                    "YET ANOTHER LINE IN CAPS",
                ],
                "col2": [
                    "this is in all lowercase",
                    "another line that is also in lowercase",
                    "yet another line in lowercase",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
            case_sensitive: false
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"].values.tolist() == [
            "THIS IS IN ALL",
            "ANOTHER LINE THAT IS ALSO IN",
            "YET ANOTHER LINE IN",
        ]

    def test_compare_text_case_insensitive_overlap(self):
        """
        Test compare using case insensitive overlap
        """
        data = pd.DataFrame(
            {
                "col1": [
                    "THIS IS IN ALL CAPS",
                    "ANOTHER LINE THAT IS ALSO IN CAPS",
                    "YET ANOTHER LINE IN CAPS",
                ],
                "col2": [
                    "this is in all lowercase",
                    "another line that is also in lowercase",
                    "yet another line in lowercase",
                ],
            }
        )

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
            case_sensitive: false
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df["output"][1] == "ANOTHER LINE THAT IS ALSO IN *****CA*S*"

    def test_compare_text_case_sensitive_true_enables_case_sensitive_matching(self):
        """
        case_sensitive: true restores real case-sensitive matching, distinct
        from the case-insensitive default.
        """
        data = pd.DataFrame({"col1": ["Mario"], "col2": ["mario"]})
        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
            case_sensitive: true
        """
        df = wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert df["output"][0] == "mario"

    def test_compare_text_case_sensitive_false_and_omitted_equivalent(self):
        """
        case_sensitive: false and omitting it entirely must produce identical
        (case-insensitive) results, since False is the default.
        """
        data = pd.DataFrame(
            {
                "col1": ["THIS IS IN ALL CAPS"],
                "col2": ["this is in all lowercase"],
            }
        )
        outputs = {}
        for label, case_sensitive_line in [
            ("false", "case_sensitive: false"),
            ("omitted", ""),
        ]:
            recipe = f"""
            wrangles:
            - compare.text:
                input:
                - col1
                - col2
                output: output
                method: difference
                {case_sensitive_line}
            """
            df = wrangles.recipe.run(recipe=recipe, dataframe=data)
            outputs[label] = df["output"][0]

        assert outputs["false"] == outputs["omitted"] == "lowercase"

    def test_compare_text_case_sensitive_true_differs_from_default(self):
        """
        case_sensitive: true must produce a different result than the
        case-insensitive default when casing differs between inputs.
        """
        data = pd.DataFrame(
            {
                "col1": ["THIS IS IN ALL CAPS"],
                "col2": ["this is in all lowercase"],
            }
        )
        recipe_true = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
            case_sensitive: true
        """
        recipe_default = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """
        df_true = wrangles.recipe.run(recipe=recipe_true, dataframe=data)
        df_default = wrangles.recipe.run(recipe=recipe_default, dataframe=data)
        assert df_true["output"][0] != df_default["output"][0]
        assert df_default["output"][0] == "lowercase"

    def test_compare_text_default_preserves_title_case(self):
        """
        Regression: forcing case-insensitive matching by default must not lowercase
        legacy difference/intersection output - original casing should be preserved.
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario Oak Wood White Marble Top Bookshelf"],
                "col2": ["Mario Pine Wood Black Marble Bottom Bookshelf"],
            }
        )
        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """
        df = wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert df["output"][0] == "Pine Black Bottom"

    def test_compare_text_overlap_quoted_decimal_places(self):
        """
        Regression: a quoted decimal_places value must not crash overlap.
        """
        data = pd.DataFrame({"col1": ["Mario"], "col2": ["Martio"]})
        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output:
            - output_mask
            - output_ratio
            method: overlap
            include_ratio: true
            decimal_places: "2"
        """
        df = wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert df["output_mask"][0] == "Mar*io"
        assert df["output_ratio"][0] == 0.91

    def test_compare_text_overlap_include_ratio_requires_two_outputs(self):
        """
        include_ratio: true must raise a clear error if output is not a
        list of exactly two column names.
        """
        data = pd.DataFrame({"col1": ["Mario"], "col2": ["Martio"]})

        for bad_output in ["output", "\n            - only_one_column"]:
            recipe = f"""
            wrangles:
            - compare.text:
                input:
                - col1
                - col2
                output:{bad_output}
                method: overlap
                include_ratio: true
            """
            try:
                wrangles.recipe.run(recipe=recipe, dataframe=data)
                assert False, "Should raise an error if output is not a list of two columns"
            except Exception:
                pass

    def test_compare_text_overlap_without_include_ratio_still_accepts_single_output(self):
        """
        Without include_ratio, output can still be a single column name as before.
        """
        data = pd.DataFrame({"col1": ["Mario"], "col2": ["Martio"]})
        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
        """
        df = wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert df["output"][0] == "Mar*io"


class TestCompareTextSimilarity:
    """
    Test compare.text method: similarity
    """

    def _run(self, data, metric=None, decimal_places=None, extra=""):
        metric_line = f"metric: {metric}" if metric else ""
        decimal_places_line = (
            f"decimal_places: {decimal_places}" if decimal_places is not None else ""
        )
        recipe = f"""
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: similarity
            {metric_line}
            {decimal_places_line}
            {extra}
        """
        return wrangles.recipe.run(recipe=recipe, dataframe=data)

    def test_default_metric_is_token_sort(self):
        """
        Omitting metric should behave the same as explicitly requesting token_sort.
        """
        data = pd.DataFrame(
            {
                "col1": ["M8 stainless bolt"],
                "col2": ["M8 stainless bolt 20mm"],
            }
        )
        df_default = self._run(data)
        df_token_sort = self._run(data, metric="token_sort")
        assert df_default["output"][0] == df_token_sort["output"][0]

    def test_token_sort_reordered_tokens_scores_one(self):
        """
        token_sort ignores token order.
        """
        data = pd.DataFrame(
            {
                "col1": ["M8 stainless bolt 20mm"],
                "col2": ["20mm bolt stainless M8"],
            }
        )
        df = self._run(data, metric="token_sort")
        assert df["output"][0] == 1.0

    def test_token_sort_penalizes_missing_and_extra_tokens(self):
        """
        token_sort scores below 1.0 when tokens are missing/extra.
        """
        data = pd.DataFrame(
            {
                "col1": ["M8 stainless bolt"],
                "col2": ["M8 stainless bolt 20mm"],
            }
        )
        df = self._run(data, metric="token_sort")
        assert 0.0 <= df["output"][0] < 1.0

    def test_token_set_subset_containment_scores_one(self):
        """
        token_set can score 1.0 when a shorter token set is fully contained in a longer one.
        """
        data = pd.DataFrame(
            {
                "col1": ["M8 stainless bolt"],
                "col2": ["M8 stainless bolt 20mm"],
            }
        )
        df = self._run(data, metric="token_set")
        assert df["output"][0] == 1.0

    def test_conflicting_attribute_reduces_order_independent_scores(self):
        """
        A conflicting attribute (red vs blue) must reduce both order-independent metrics.
        """
        data = pd.DataFrame(
            {
                "col1": ["red steel bolt"],
                "col2": ["blue steel bolt"],
            }
        )
        df_token_sort = self._run(data, metric="token_sort")
        df_token_set = self._run(data, metric="token_set")
        assert df_token_sort["output"][0] < 1.0
        assert df_token_set["output"][0] < 1.0

    def test_damerau_levenshtein_adjacent_transposition(self):
        """
        damerau_levenshtein should recognize an adjacent transposition as a single edit.
        """
        data = pd.DataFrame({"col1": ["smtih"], "col2": ["smith"]})
        df = self._run(data, metric="damerau_levenshtein")
        # a single transposition on a 5-character word -> normalized similarity 0.8
        assert df["output"][0] == 0.8

    def test_damerau_levenshtein_insertion_deletion_substitution(self):
        """
        damerau_levenshtein should score each single-edit-distance operation
        (insertion, deletion, substitution) as one edit, distinct from a no-op match.
        """
        data = pd.DataFrame(
            {
                "col1": ["bolt", "bolt", "bolt"],
                "col2": ["boltx", "bol", "belt"],
            },
            index=["insertion", "deletion", "substitution"],
        )
        df = self._run(data, metric="damerau_levenshtein")
        # a single insertion on a 4/5-character word -> normalized similarity 0.8
        assert df["output"]["insertion"] == 0.8
        # a single deletion on a 4-character word -> normalized similarity 0.75
        assert df["output"]["deletion"] == 0.75
        # a single substitution on a 4-character word -> normalized similarity 0.75
        assert df["output"]["substitution"] == 0.75

    def test_duplicate_tokens_token_sort_vs_token_set(self):
        """
        token_sort retains duplicate tokens (penalized); token_set is duplicate-insensitive.
        """
        data = pd.DataFrame(
            {
                "col1": ["bolt bolt steel"],
                "col2": ["bolt steel"],
            }
        )
        df_token_sort = self._run(data, metric="token_sort")
        df_token_set = self._run(data, metric="token_set")
        assert df_token_sort["output"][0] < 1.0
        assert df_token_set["output"][0] == 1.0

    def test_anagram_does_not_score_perfect(self):
        """
        Character anagrams with no matching tokens must not receive a perfect score.
        """
        data = pd.DataFrame({"col1": ["tide"], "col2": ["diet"]})
        for metric in ["token_sort", "damerau_levenshtein", "token_set"]:
            df = self._run(data, metric=metric)
            assert df["output"][0] < 1.0

    def test_punctuation_does_not_equate_identifiers(self):
        """
        Normalization must not decide that AB-12 and AB12 are equivalent.
        """
        data = pd.DataFrame({"col1": ["AB-12"], "col2": ["AB12"]})
        for metric in ["token_sort", "damerau_levenshtein", "token_set"]:
            df = self._run(data, metric=metric)
            assert df["output"][0] < 1.0

    def test_unicode_and_case_normalization_exact_match(self):
        """
        Unicode compatibility normalization and case folding should make these equal.
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario Oak Wood"],
                "col2": ["mario   oak-wood"],
            }
        )
        for metric in ["token_sort", "damerau_levenshtein", "token_set"]:
            df = self._run(data, metric=metric)
            assert df["output"][0] == 1.0

    def test_symmetry(self):
        """
        Swapping the two inputs must not change the score, for every metric.
        """
        data_ab = pd.DataFrame(
            {"col1": ["red steel bolt M8"], "col2": ["M8 steel bolt blue"]}
        )
        data_ba = pd.DataFrame(
            {"col1": ["M8 steel bolt blue"], "col2": ["red steel bolt M8"]}
        )
        for metric in ["token_sort", "damerau_levenshtein", "token_set"]:
            df_ab = self._run(data_ab, metric=metric)
            df_ba = self._run(data_ba, metric=metric)
            assert df_ab["output"][0] == df_ba["output"][0]

    def test_scores_are_bounded_between_zero_and_one(self):
        """
        Every produced score must be between 0.0 and 1.0 inclusive.
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario", "red steel bolt", "M8 stainless bolt 20mm", "smtih", "tide"],
                "col2": ["Luigi", "blue steel bolt", "20mm bolt stainless M8", "smith", "diet"],
            }
        )
        for metric in ["token_sort", "damerau_levenshtein", "token_set"]:
            df = self._run(data, metric=metric)
            assert all(0.0 <= score <= 1.0 for score in df["output"].tolist())

    def test_missing_values_return_null_not_string(self):
        """
        wrangles.compare.similarity() (the library function) should return None
        for null/blank inputs, not the strings "nan"/"None", and should never
        stringify a missing value before checking for it.
        """
        from wrangles import compare as compare_lib

        results = compare_lib.similarity(
            input=[
                ["Mario", "Mario"],
                [None, "Luigi"],
                [np.nan, "Peach"],
                ["Bowser", None],
                ["", ""],
            ],
            metric="token_sort",
        )
        assert results[0] == 1.0
        assert results[1] is None
        assert results[2] is None
        assert results[3] is None
        assert results[4] is None

    def test_missing_values_via_recipe_are_not_stringified(self):
        """
        Regression: missing values must never surface as the literal strings
        "nan"/"None" in the output (the recipe engine blanks nulls to '' after
        every wrangle, so that - not "nan"/"None" - is the expected surface value).
        """
        data = pd.DataFrame(
            {
                "col1": ["Mario", None, np.nan, "Bowser"],
                "col2": ["Mario", "Luigi", "Peach", None],
            }
        )
        df = self._run(data, metric="token_sort")
        assert df["output"][0] == 1.0
        for value in df["output"][1:]:
            assert value not in ("nan", "None")

    def test_long_repetitive_string_returns_bounded_score(self):
        """
        Long repetitive strings should still return a single bounded score.
        """
        data = pd.DataFrame(
            {
                "col1": [" ".join(["bolt"] * 500)],
                "col2": [" ".join(["bolt"] * 499 + ["nut"])],
            }
        )
        df = self._run(data, metric="token_sort")
        assert 0.0 <= df["output"][0] <= 1.0

    def test_similarity_requires_exactly_two_columns(self):
        """
        method: similarity requires exactly two input columns.
        """
        data = pd.DataFrame({"col1": ["a"], "col2": ["b"], "col3": ["c"]})
        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            - col3
            output: output
            method: similarity
        """
        try:
            wrangles.recipe.run(recipe=recipe, dataframe=data)
            assert False, "Should raise an error if more than two columns are passed"
        except Exception:
            pass

    def test_similarity_invalid_metric_raises(self):
        """
        An unknown metric should raise an error.
        """
        data = pd.DataFrame({"col1": ["a"], "col2": ["b"]})
        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: similarity
            metric: not_a_real_metric
        """
        try:
            wrangles.recipe.run(recipe=recipe, dataframe=data)
            assert False, "Should raise an error for an invalid metric"
        except Exception:
            pass

    def test_quoted_decimal_places(self):
        """
        Regression: a quoted decimal_places value must not crash similarity.
        """
        data = pd.DataFrame({"col1": ["smtih"], "col2": ["smith"]})
        df = self._run(data, metric="damerau_levenshtein", decimal_places='"2"')
        assert df["output"][0] == 0.8
