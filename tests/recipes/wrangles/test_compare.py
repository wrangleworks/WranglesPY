import wrangles
import pandas as pd


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
            output: output
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
        assert df["output"].values.tolist() == [
            ["@@@@@Mario", 0.67],
            ["@@@@@Luigi", 0.67],
            ["Empty A", 0],
            ["Empty B", 0],
            ["Both Empty", 0],
        ]

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
            output: output
            method: overlap
            include_ratio: True
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )

        assert df["output"].values.tolist() == [
            ["Mario", 1],
            ["Luigi", 1],
            ["Mar*io", 0.909],
            ["Lui*gi", 0.909],
        ]

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
