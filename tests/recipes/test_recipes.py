"""
Tests for misc general recipe logic and operation

Specific tests for individual connectors or wrangles should be placed within
a file for the respective wrangle/connector.
"""
import wrangles
from wrangles.connectors import memory
import pandas as pd
import pytest
import time


def test_recipe_from_file():
    """
    Testing recipe passed as a filename
    """
    df = wrangles.recipe.run(
        "tests/samples/recipe_sample.wrgl.yaml",
        variables= {
            "inputFile": 'tests/samples/data.csv',
            "outputFile": 'tests/temp/write_data.xlsx'
        }
    )
    assert df.columns.tolist() == ['ID', 'Find2']

def test_recipe_from_url():
    """
    Testing reading a recipe from an https:// source
    """
    df = wrangles.recipe.run(
        "https://public.wrangle.works/tests/recipe.wrgl.yml",
        dataframe=pd.DataFrame({
            'col1': ['hello world'],
        })
    )
    assert df.iloc[0]['out1'] == 'HELLO WORLD'

def test_recipe_from_url_not_found():
    """
    Test that if a user passes in a recipe as a URL and the 
    URL produces an error, that a sensible error is communicated
    to the user
    """
    data = pd.DataFrame({
    'col1': ['hello world'],
    })
    recipe = "https://public.wrangle.works/tests/recipe.wrgl.yaaml"
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        info.value.args[0] == 'Error getting recipe from url: https://public.wrangle.works/tests/recipe.wrgl.yaaml\nReason: Not Found-404'
    )

def test_wildcard_expansion_1():
    """
    Wild card Expansion escape character
    """
    data = pd.DataFrame({
        'col1': ['HEllO'],
        'col*': ['WORLD'],
    })
    recipe = r"""
    wrangles:
      - convert.case:
          input:
            - col\*
          output:
            - out
          case: lower
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out'] == 'world'

def test_recipe_special_character():
    """
    Tests special character encoding when reading a recipe containing special characters
    """
    df = wrangles.recipe.run("tests/samples/recipe_special_character.wrgl.yml")
    assert df.iloc[0]['column'] == 'this is a ° symbol'

def test_recipe_model():
    """
    Test running a recipe using a model ID
    """
    df = wrangles.recipe.run("1e13e845-bc3f-4b27")
    assert (
        len(df) == 15 and
        list(df.columns[:3]) == ["Part Number", "Description", "Brand"]
    )

def test_timeout():
    """
    Test that the timeout parameter triggers
    an appropriate error
    """
    def sleep(df, seconds):
        time.sleep(seconds)
        return df

    with pytest.raises(TimeoutError) as info:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
            
            wrangles:
            - custom.sleep:
                seconds: 10
            """
            ,
            functions=sleep,
            timeout=2
        )
    
    assert info.typename == 'TimeoutError'

def test_timeout_time():
    """
    Test that the timeout parameter
    stops the processing in an appropriate time
    """
    def sleep(df, seconds):
        time.sleep(seconds)
        return df

    start = time.time()
    with pytest.raises(TimeoutError) as info:
        raise wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
            
            wrangles:
            - custom.sleep:
                seconds: 10
            """
            ,
            functions=sleep,
            timeout=2
        )
    
    stop = time.time()

    assert (
        info.typename == 'TimeoutError' and
        stop - start < 2.5 and
        stop - start > 1.5
    )

def test_timeout_failure_actions():
    """
    Test that on_failure actions
    are run if the recipe times out
    """
    def sleep(df, seconds):
        time.sleep(seconds)
        return df

    def fail():
        memory.variables["timeout fail action"] = "got here"

    with pytest.raises(TimeoutError) as info:
        raise wrangles.recipe.run(
            """
            run:
              on_failure:
                - custom.fail: {}

            read:
            - test:
                rows: 5
                values:
                    header1: value1
            
            wrangles:
            - custom.sleep:
                seconds: 10
            """
            ,
            functions=[sleep,fail],
            timeout=2
        )

    assert (
        info.typename == 'TimeoutError' and
        memory.variables["timeout fail action"] == "got here"
    )
    
def test_invalid_recipe_file_extension():
    """
    Test that an invalid recipe file extension
    throws an appropriate error
    """
    with pytest.raises(RuntimeError) as info:
        raise wrangles.recipe.run("tests/samples/recipe_sample.wrgl.yaaml")
    assert (
        info.typename == 'RuntimeError' and
        info.value.args[0].startswith('Error reading recipe')
    )

# Optional columns
def test_optional_wrangles_input():
    """
    Test a column indicated as optional
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2

        wrangles:
          - merge.concatenate:
              input:
                - header1
                - header2
                - header3?
              output: result
              char: ","
        """
    )
    assert df["result"][0] == "value1,value2"

def test_non_optional_wrangles_input():
    """
    Test a missing column not indicated
    as optional fails appropriately
    """
    with pytest.raises(KeyError) as error:
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
                    header2: value2

            wrangles:
            - merge.concatenate:
                input:
                    - header1
                    - header2
                    - header3
                output: result
                char: ","
            """
        )
    assert "Column header3 does not exist" in error.value.args[0]

def test_optional_write_columns():
    """
    Test writing an optional column that isn't present
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2

        write:
          - memory:
              id: test_optional_write_columns
              columns:
                - header1
                - header2
                - header3?
        """
    )
    assert memory.dataframes["test_optional_write_columns"]["columns"] == ["header1","header2"]

def test_optional_write_not_columns():
    """
    Test writing an optional not column that isn't present
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2

        write:
          - memory:
              id: test_optional_write_not_columns
              columns:
                - header1
                - header2
              not_columns:
                - header3?
        """
    )
    assert memory.dataframes["test_optional_write_not_columns"]["columns"] == ["header1","header2"]

def test_non_optional_write_columns():
    """
    Test a missing column not indicated
    as optional fails appropriately
    """
    with pytest.raises(KeyError) as error:
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 5
                  values:
                    header1: value1
                    header2: value2

            write:
              - memory:
                  id: test_non_optional_write_columns
                  columns:
                    - header1
                    - header2
                    - header3
            """
        )
    assert "Column header3 does not exist" in error.value.args[0]

def test_optional_read_columns():
    """
    Test reading an optional column that isn't present
    """
    memory.dataframes["test_optional_read_columns"] = {
        "index": [0, 1],
        "columns": ["header1", "header2"],
        "data": [["value1", "value2"], ["value1", "value2"]]
    }

    df = wrangles.recipe.run(
        """
        read:
          - memory:
              id: test_optional_read_columns
              columns:
                - header1
                - header2
                - header3?
              orient: split
        """
    )
    assert list(df.columns) == ["header1","header2"]

def test_non_optional_read_columns():
    """
    Test a missing column not indicated
    as optional fails appropriately
    """
    memory.dataframes["test_non_optional_read_columns"] = {
        "index": [0, 1],
        "columns": ["header1", "header2"],
        "data": [["value1", "value2"], ["value1", "value2"]]
    }

    with pytest.raises(KeyError) as error:
        wrangles.recipe.run(
            """
            read:
              - memory:
                  id: test_non_optional_read_columns
                  columns:
                    - header1
                    - header2
                    - header3
                  orient: split
            """
        )
    assert "Column header3 does not exist" in error.value.args[0]

def test_column_with_question_mark():
    """
    Test that a column ending with a
    question mark still works correctly
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
                header?: value3

        wrangles:
          - merge.concatenate:
              input:
                - header1
                - header2
                - header?
              output: result
              char: ","
        """
    )
    assert df["result"][0] == "value1,value2,value3"

def test_wildcard_expansion():
    """
    Test basic wildcard expansion
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        "col1"
    )
    assert columns == ["col1"]

def test_wildcard_expansion_list():
    """
    Test wildcard expansion
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        ["col1", "col2"]
    )
    assert columns == ["col1", "col2"]

def test_wildcard_expansion_star():
    """
    Test wildcard expansion with star
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        "col*"
    )
    assert columns == ["col1","col2","col3"]

def test_wildcard_expansion_regex():
    """
    Test wildcard expansion with regex
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        "regex:col[1-2]"
    )
    assert columns == ["col1","col2"]

def test_wildcard_expansion_regex_space():
    """
    Test wildcard expansion with "regex: "
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        "regex: col[1-2]"
    )
    assert columns == ["col1","col2"]

def test_wildcard_expansion_regex_case_insensitive():
    """
    Test that regex: isn't case sensitive
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        "REGEX:col[1-2]"
    )
    assert columns == ["col1","col2"]

def test_wildcard_expansion_missing_column_error():
    """
    Test wildcard expansion raises an appropriate error
    for a missing column
    """
    with pytest.raises(KeyError, match="does not exist"):
        raise wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            "col4"
        )

def test_wildcard_expansion_missing_column_error():
    """
    Test wildcard expansion raises an appropriate error
    for a missing column
    """
    with pytest.raises(KeyError, match="does not exist"):
        raise wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            "col4"
        )

def test_wildcard_expansion_optional_column():
    """
    Test that wildcard doesn't error on an
    optional column that doesn't exist
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        ["col1", "col4?"]
    )
    assert columns == ["col1"]

def test_wildcard_expansion_overlap():
    """
    Test wildcard expansion on overlapping searches
    """
    columns = wrangles.recipe._wildcard_expansion(
        ["col1","col2","col3"],
        ["col1", "col*"]
    )
    assert columns == ["col1", "col2", "col3"]

def test_wildcard_expansion_dict():
    """
    Test wildcard expansion on a dict
    """
    columns = wrangles.utils.wildcard_expansion_dict(
        ["col1","col2","col3"],
        {"col1": "col1"}
    )
    assert columns == {"col1": "col1"}

def test_wildcard_expansion_dict_rename():
    """
    Test wildcard expansion on a dict
    """
    columns = wrangles.utils.wildcard_expansion_dict(
        ["col1","col2","col3"],
        {"col1": "new_col1"}
    )
    assert columns == {"col1": "new_col1"}

def test_wildcard_expansion_dict_wildcard():
    """
    Test wildcard expansion on a dict
    with a wildcard for input and output names
    """
    columns = wrangles.utils.wildcard_expansion_dict(
        ["col_1","col_2","col_3"],
        {"col_*": "new_*"}
    )
    assert columns == {
        "col_1": "new_1",
        "col_2": "new_2",
        "col_3": "new_3"
    }

def test_wildcard_expansion_dict_regex():
    """
    Test wildcard expansion on a dict on input: output columns
    with regex
    """
    columns = wrangles.utils.wildcard_expansion_dict(
        ["col1","col2","col3"],
        {"regex:col([1-2])": r"new_\1"}
    )
    assert columns == {
        "col1": "new_1",
        "col2": "new_2"
    }
