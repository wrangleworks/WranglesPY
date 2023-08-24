import wrangles
import pandas as pd


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
    Test using a custom function
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

    lens = [len(v) for v in save_vals.values()]
    assert lens == [3,2,1]
