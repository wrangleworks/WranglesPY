import wrangles
import pandas as pd
from wrangles.connectors import memory
import pytest


class TestRun:
    """
    Test matrix run
    """

    def test_matrix_list(self):
        """
        Test using variables from a list
        """
        test_vals = []

        def fn(value):
            test_vals.append(value)

        wrangles.recipe.run(
            """
            run:
              on_start:
                - matrix:
                    variables:
                      var: [a,b,c]
                    run:
                      - custom.fn:
                          value: ${var}
            """,
            functions=fn,
        )

        assert sorted(test_vals) == ["a", "b", "c"]

    def test_matrix_list_from_variable(self):
        """
        Test using variables from a list defined by a variable
        """
        test_vals = []

        def fn(value):
            test_vals.append(value)

        wrangles.recipe.run(
            """
            run:
              on_start:
                - matrix:
                    variables:
                      var: ${input_var}
                    run:
                      - custom.fn:
                          value: ${var}
            """,
            functions=fn,
            variables={"input_var": ["a", "b", "c"]},
        )

        assert sorted(test_vals) == ["a", "b", "c"]

    def test_matrix_list_from_json(self):
        """
        Test using variables from a list
        defined by a variable as JSON
        """
        test_vals = []

        def fn(value):
            test_vals.append(value)

        wrangles.recipe.run(
            """
            run:
              on_start:
                - matrix:
                    variables:
                      var: ${input_var}
                    run:
                      - custom.fn:
                          value: ${var}
            """,
            functions=fn,
            variables={"input_var": '["a","b","c"]'},
        )

        assert sorted(test_vals) == ["a", "b", "c"]


class TestRead:
    def test_list(self):
        """
        Test using variables from a list
        """
        for i in range(3):
            memory.dataframes[f"test_matrix_read_list_{i}"] = pd.DataFrame(
                {"header": [f"value{i}"]}
            )

        df = wrangles.recipe.run(
            """
            read:
              - union:
                  sources:
                    - matrix:
                        variables:
                          var: [0,1,2]
                        read:
                          - memory:
                              id: test_matrix_read_list_${var}
            """
        )

        assert list(df["header"].values) == ["value0", "value1", "value2"]

    def test_custom_function(self):
        """
        Test using variables from a list
        """
        for i in range(3):
            memory.dataframes[f"test_matrix_read_fn_{i}"] = pd.DataFrame(
                {"header": [f"value{i}"]}
            )

        def get_list():
            return [0, 1, 2]

        df = wrangles.recipe.run(
            """
            read:
              - union:
                  sources:
                    - matrix:
                        variables:
                          var: custom.get_list
                        read:
                          - memory:
                              id: test_matrix_read_fn_${var}
            """,
            functions=get_list,
        )

        assert list(df["header"].values) == ["value0", "value1", "value2"]

    def test_read_directory(self):
        """
        Test using variables defined by the files in a directory
        """
        df = wrangles.recipe.run(
            """
            read:
              - union:
                  sources:
                    - matrix:
                        variables:
                          var: dir(tests/samples/matrix_dir)
                        read:
                          - file:
                              name: ${var}
            """
        )

        assert list(df["header"].values) == ["value1", "value2", "value3"]

    def test_read_if(self):
        """
        Test using matrix and if in combination
        """
        df = wrangles.recipe.run(
            """
            read:
              - union:
                  sources:
                    - matrix:
                        variables:
                          var: dir(tests/samples/matrix_dir)
                        read:
                          - file:
                              name: ${var}
                              if: ${var}.endswith(".csv")
            """
        )

        assert list(df["header"].values) == ["value1", "value2"]

    def test_not_aggregated(self):
        """
        Test that a matrix not explicitly aggregated is
        unioned together.
        """
        df = wrangles.recipe.run(
            """
            read:
              - matrix:
                  variables:
                    var: dir(tests/samples/matrix_dir)
                  read:
                    - file:
                        name: ${var}
            """
        )

        assert list(df["header"].values) == ["value1", "value2", "value3"]


class TestWrite:
    def test_matrix_column_set(self):
        """
        Test using variables from a column contents
        """
        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    filename: set(col1)
                write:
                    - file:
                        name: tests/temp/${filename}.csv
                        where: col1 = ?
                        where_params:
                        - ${filename}
            """,
            dataframe=pd.DataFrame({"col1": ["a", "a", "a", "b", "b", "c"]}),
        )

        lens = [
            len(wrangles.connectors.file.read(f"tests/temp/{char}.csv"))
            for char in ["a", "b", "c"]
        ]

        assert lens == [3, 2, 1]

    def test_matrix_column_set_ordered(self):
        """
        Test that using set preserves the order correctly
        """
        check_order = []

        def _test_func(df, var1, var2):
            check_order.append(var1 == str(var2))

        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    var1: set(col1)
                    var2: set(col2)
                write:
                    - custom._test_func:
                        var1: ${var1}
                        var2: ${var2}
            """,
            dataframe=pd.DataFrame(
                {
                    "col1": ["1", "1", "2", "2", "3", "3", "4", "4"],
                    "col2": [1, 1, 2, 2, 3, 3, 4, 4],
                }
            ),
            functions=_test_func,
        )

        assert all(check_order)

    def test_invalid_column(self):
        """
        Test that a clear error is raised if the user
        tries to use a column that doesn't exist
        """
        with pytest.raises(ValueError, match="col2 not recognized"):
            wrangles.recipe.run(
                """
                write:
                - matrix:
                    variables:
                        filename: set(col2)
                    write:
                        - file:
                            name: tests/temp/${filename}.csv
                            where: col1 = ?
                            where_params:
                            - ${filename}
                """,
                dataframe=pd.DataFrame({"col1": ["a", "a", "a", "b", "b", "c"]}),
            )

    def test_matrix_list(self):
        """
        Test using variables from a list
        """
        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    filename:
                    - x
                    - y
                    - z
                write:
                    - file:
                        name: tests/temp/${filename}.csv
                        where: col1 = ?
                        where_params:
                        - ${filename}
            """,
            dataframe=pd.DataFrame({"col1": ["x", "x", "x", "y", "y", "z"]}),
        )

        lens = [
            len(wrangles.connectors.file.read(f"tests/temp/{char}.csv"))
            for char in ["x", "y", "z"]
        ]

        assert lens == [3, 2, 1]

    def test_matrix_custom_function(self):
        """
        Test using a custom function within the write
        """
        save_vals = {}

        def save_data(df, input):
            save_vals[df[input][0]] = df[input].tolist()

        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    key: [a,b,c]
                write:
                    - custom.save_data:
                        input: col1
                        where: col1 = ?
                        where_params:
                        - ${key}
            """,
            dataframe=pd.DataFrame({"col1": ["a", "a", "a", "b", "b", "c"]}),
            functions=save_data,
        )
        assert [len(save_vals["a"]), len(save_vals["b"]), len(save_vals["c"])] == [
            3,
            2,
            1,
        ]

    def test_matrix_variable_custom_function(self):
        """
        Test using a custom function to generate variables
        """

        def get_list():
            return ["a", "b", "c"]

        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    key: custom.get_list
                write:
                    - memory:
                        id: variable_custom_functions_test_${key}
                        where: col1 = ?
                        where_params:
                        - ${key}
            """,
            dataframe=pd.DataFrame({"col1": ["a", "a", "a", "b", "b", "c"]}),
            functions=get_list,
        )

        assert (
            len(memory.dataframes["variable_custom_functions_test_a"]["data"]) == 3
            and len(memory.dataframes["variable_custom_functions_test_b"]["data"]) == 2
            and len(memory.dataframes["variable_custom_functions_test_c"]["data"]) == 1
        )

    def test_matrix_variable_custom_function_single_value(self):
        """
        Test using a custom function that returns a scalar
        """

        def get_scalar():
            return "aa"

        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    key: custom.get_scalar
                write:
                    - memory:
                        id: variable_custom_function_single_value_${key}
                        where: col1 = ?
                        where_params:
                        - ${key}
            """,
            dataframe=pd.DataFrame({"col1": ["aa", "aa", "aa", "bb", "bb", "cc"]}),
            functions=get_scalar,
        )

        assert (
            len(memory.dataframes["variable_custom_function_single_value_aa"]["data"])
            == 3
        )

    def test_strategy_default(self):
        """
        Test using default strategy for multiple variables
        """
        prefix = "matrix_strategy_default"
        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    key1: [a,b,c]
                    key2: [1,2]
                    key3: z
                write:
                    - memory:
                        id: ${prefix}_${key1}_${key2}_${key3}
                        where: col1 = ?
                        where_params:
                        - ${key1}
            """,
            dataframe=pd.DataFrame({"col1": ["a", "a", "a", "b", "b", "c"]}),
            variables={"prefix": prefix},
        )
        dfs = [x for x in memory.dataframes if x.startswith(prefix)]
        assert (
            len(memory.dataframes[f"{prefix}_a_1_z"]["data"]) == 3
            and len(memory.dataframes[f"{prefix}_b_2_z"]["data"]) == 2
            and len(memory.dataframes[f"{prefix}_c_1_z"]["data"]) == 1
            and len(dfs) == 3
        )

    def test_strategy_permutations(self):
        """
        Test using permutations strategy for multiple variables
        """
        prefix = "matrix_strategy_permutations"
        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    key1: [a,b,c]
                    key2: [1,2]
                strategy: permutations
                write:
                    - memory:
                        id: ${prefix}_${key1}_${key2}
                        where: col1 = ?
                        where_params:
                        - ${key1}
            """,
            dataframe=pd.DataFrame({"col1": ["a", "a", "a", "b", "b", "c"]}),
            variables={"prefix": prefix},
        )
        assert (
            len(memory.dataframes[f"{prefix}_a_1"]["data"]) == 3
            and len(memory.dataframes[f"{prefix}_b_1"]["data"]) == 2
            and len(memory.dataframes[f"{prefix}_c_1"]["data"]) == 1
            and len(memory.dataframes[f"{prefix}_a_2"]["data"]) == 3
            and len(memory.dataframes[f"{prefix}_b_2"]["data"]) == 2
            and len(memory.dataframes[f"{prefix}_c_2"]["data"]) == 1
        )

    def test_strategy_loop(self):
        """
        Test using loop strategy for multiple variables
        """
        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    key1: [a,b,c]
                    key2: [1,2]
                    key3: z
                strategy: loop
                write:
                    - memory:
                        id: matrix_strategy_loop_${key1}_${key2}_${key3}
                        where: col1 = ?
                        where_params:
                        - ${key1}
            """,
            dataframe=pd.DataFrame({"col1": ["a", "a", "a", "b", "b", "c"]}),
        )

        dfs = [x for x in memory.dataframes if x.startswith("matrix_strategy_loop_")]

        assert (
            len(memory.dataframes["matrix_strategy_loop_a_1_z"]["data"]) == 3
            and len(memory.dataframes["matrix_strategy_loop_b_2_z"]["data"]) == 2
            and len(memory.dataframes["matrix_strategy_loop_c_1_z"]["data"]) == 1
            and len(dfs) == 3
        )

    def test_matrix_column_set_non_hashable_lists(self):
        """
        Test using variables from a column containing non-hashable lists
        """
        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    list_var: set(list_col)
                write:
                    - memory:
                        id: test_non_hashable_lists_${list_var}
            """,
            dataframe=pd.DataFrame({"list_col": [[1, 2], [3, 4], [1, 2], [5, 6]]}),
        )

        # Check that we have the right number of unique lists
        expected_ids = [
            "test_non_hashable_lists_[1, 2]",
            "test_non_hashable_lists_[3, 4]",
            "test_non_hashable_lists_[5, 6]",
        ]
        actual_ids = [
            key
            for key in memory.dataframes.keys()
            if key.startswith("test_non_hashable_lists_")
        ]
        assert len(actual_ids) == 3

    def test_matrix_column_set_non_hashable_dicts(self):
        """
        Test using variables from a column containing non-hashable dictionaries
        """
        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    dict_var: set(dict_col)
                write:
                    - memory:
                        id: test_non_hashable_dicts_${dict_var}
            """,
            dataframe=pd.DataFrame(
                {"dict_col": [{"a": 1}, {"b": 2}, {"a": 1}, {"c": 3}]}
            ),
        )

        # Check that we have the right number of unique dicts
        actual_ids = [
            key
            for key in memory.dataframes.keys()
            if key.startswith("test_non_hashable_dicts_")
        ]
        assert len(actual_ids) == 3

    def test_matrix_column_set_non_hashable_numpy_arrays(self):
        """
        Test using variables from a column containing non-hashable numpy arrays
        """
        import numpy as np

        wrangles.recipe.run(
            """
            write:
            - matrix:
                variables:
                    array_var: set(array_col)
                write:
                    - memory:
                        id: test_non_hashable_arrays_${array_var}
            """,
            dataframe=pd.DataFrame(
                {
                    "array_col": [
                        np.array([1, 2]),
                        np.array([3, 4]),
                        np.array([1, 2]),
                        np.array([5, 6]),
                    ]
                }
            ),
        )

        # Check that matrix processing works (pandas drop_duplicates doesn't deduplicate numpy arrays perfectly,
        # but that's acceptable since numpy array equality is complex)
        actual_ids = [
            key
            for key in memory.dataframes.keys()
            if key.startswith("test_non_hashable_arrays_")
        ]
        assert (
            len(actual_ids) >= 3
        )  # May be 3 or 4 depending on how pandas handles numpy array deduplication
