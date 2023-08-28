import wrangles
import pandas as pd
from wrangles.connectors import memory


def test_matrix_column_set():
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
        dataframe=pd.DataFrame({
            "col1": ["a","a","a","b","b","c"]
        })
    )

    lens = [
        len(wrangles.connectors.file.read(f"tests/temp/{char}.csv"))
        for char in ["a", "b", "c"]
    ]

    assert lens == [3,2,1]

def test_matrix_list():
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
        dataframe=pd.DataFrame({
            "col1": ["x","x","x","y","y","z"]
        })
    )

    lens = [
        len(wrangles.connectors.file.read(f"tests/temp/{char}.csv"))
        for char in ["x", "y", "z"]
    ]

    assert lens == [3,2,1]

def test_matrix_custom_function():
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
        dataframe=pd.DataFrame({
            "col1": ["a","a","a","b","b","c"]
        }),
        functions=save_data
    )
    assert (
        [
            len(save_vals["a"]),
            len(save_vals["b"]),
            len(save_vals["c"])
        ]
        == [3,2,1]
    )

def test_matrix_variable_custom_function():
    """
    Test using a custom function to generate variables
    """
    def get_list():
        return ["a","b","c"]

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
        dataframe=pd.DataFrame({
            "col1": ["a","a","a","b","b","c"]
        }),
        functions=get_list
    )
    
    assert (
        len(memory.dataframes["variable_custom_functions_test_a"]["data"]) == 3 and
        len(memory.dataframes["variable_custom_functions_test_b"]["data"]) == 2 and
        len(memory.dataframes["variable_custom_functions_test_c"]["data"]) == 1
    )

def test_strategy_default():
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
        dataframe=pd.DataFrame({
            "col1": ["a","a","a","b","b","c"]
        }),
        variables={"prefix":prefix}
    )
    dfs = [
        x for x in memory.dataframes
        if x.startswith(prefix)
    ]
    assert (
        len(memory.dataframes[f"{prefix}_a_1_z"]["data"]) == 3 and
        len(memory.dataframes[f"{prefix}_b_2_z"]["data"]) == 2 and
        len(memory.dataframes[f"{prefix}_c_1_z"]["data"]) == 1 and
        len(dfs) == 3
    )

def test_strategy_permutations():
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
        dataframe=pd.DataFrame({
            "col1": ["a","a","a","b","b","c"]
        }),
        variables={"prefix":prefix}
    )
    assert (
        len(memory.dataframes[f"{prefix}_a_1"]["data"]) == 3 and
        len(memory.dataframes[f"{prefix}_b_1"]["data"]) == 2 and
        len(memory.dataframes[f"{prefix}_c_1"]["data"]) == 1 and
        len(memory.dataframes[f"{prefix}_a_2"]["data"]) == 3 and
        len(memory.dataframes[f"{prefix}_b_2"]["data"]) == 2 and
        len(memory.dataframes[f"{prefix}_c_2"]["data"]) == 1
    )

def test_strategy_loop():
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
        dataframe=pd.DataFrame({
            "col1": ["a","a","a","b","b","c"]
        })
    )
    
    dfs = [
        x for x in memory.dataframes
        if x.startswith("matrix_strategy_loop_")
    ]

    assert (
        len(memory.dataframes["matrix_strategy_loop_a_1_z"]["data"]) == 3 and
        len(memory.dataframes["matrix_strategy_loop_b_2_z"]["data"]) == 2 and
        len(memory.dataframes["matrix_strategy_loop_c_1_z"]["data"]) == 1 and
        len(dfs) == 3
    )
