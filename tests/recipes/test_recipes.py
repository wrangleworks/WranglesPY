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

def test_recipe_from__recipe_file():
    """
    Testing recipe passed as a filename with .recipe extension
    """
    df = wrangles.recipe.run(
        "tests/samples/recipe_sample.recipe",
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

def test_recipe_by_version_id():
    """
    Test running a recipe using a model ID and version ID
    """
    df = wrangles.recipe.run("c37af8a6-43d8-4127:fe885889-67f2-4f3a-b33a-1a37ff5c243c")
    assert (
        len(df) == 10 and
        list(df.columns) == ["header"]
    )

def test_recipe_by_version_tag():
    """
    Test running a recipe using a model ID and version tag
    """
    df1 = wrangles.recipe.run("c37af8a6-43d8-4127:1.0")
    df2 = wrangles.recipe.run("c37af8a6-43d8-4127:2.0")
    assert (
        len(df1) == 10 and
        len(df2) == 20
    )

def test_recipe_wrong_model():
    """
    Test the error message when a model is incorrect type
    """
    with pytest.raises(ValueError, match="Using classify model_id a62c7480-500e-480c in a recipe wrangle"):
            wrangles.recipe.run('a62c7480-500e-480c')

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

class TestColumnWildcards:
    def test_wildcard_expansion(self):
        """
        Test basic wildcard expansion
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            "col1"
        )
        assert columns == ["col1"]

    def test_wildcard_expansion_list(self):
        """
        Test wildcard expansion
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            ["col1", "col2"]
        )
        assert columns == ["col1", "col2"]

    def test_wildcard_expansion_star(self):
        """
        Test wildcard expansion with star
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            "col*"
        )
        assert columns == ["col1","col2","col3"]

    def test_wildcard_expansion_regex(self):
        """
        Test wildcard expansion with regex
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            "regex:col[1-2]"
        )
        assert columns == ["col1","col2"]

    def test_wildcard_expansion_regex_space(self):
        """
        Test wildcard expansion with "regex: "
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            "regex: col[1-2]"
        )
        assert columns == ["col1","col2"]

    def test_wildcard_expansion_regex_case_insensitive(self):
        """
        Test that regex: isn't case sensitive
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            "REGEX:col[1-2]"
        )
        assert columns == ["col1","col2"]

    def test_wildcard_expansion_missing_column_error(self):
        """
        Test wildcard expansion raises an appropriate error
        for a missing column
        """
        with pytest.raises(KeyError, match="does not exist"):
            raise wrangles.recipe._wildcard_expansion(
                ["col1","col2","col3"],
                "col4"
            )

    def test_wildcard_expansion_missing_column_error(self):
        """
        Test wildcard expansion raises an appropriate error
        for a missing column
        """
        with pytest.raises(KeyError, match="does not exist"):
            raise wrangles.recipe._wildcard_expansion(
                ["col1","col2","col3"],
                "col4"
            )

    def test_wildcard_expansion_optional_column(self):
        """
        Test that wildcard doesn't error on an
        optional column that doesn't exist
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            ["col1", "col4?"]
        )
        assert columns == ["col1"]

    def test_wildcard_expansion_overlap(self):
        """
        Test wildcard expansion on overlapping searches
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            ["col1", "col*"]
        )
        assert columns == ["col1", "col2", "col3"]

    def test_wildcard_expansion_dict(self):
        """
        Test wildcard expansion on a dict
        """
        columns = wrangles.utils.wildcard_expansion_dict(
            ["col1","col2","col3"],
            {"col1": "col1"}
        )
        assert columns == {"col1": "col1"}

    def test_wildcard_expansion_dict_rename(self):
        """
        Test wildcard expansion on a dict
        """
        columns = wrangles.utils.wildcard_expansion_dict(
            ["col1","col2","col3"],
            {"col1": "new_col1"}
        )
        assert columns == {"col1": "new_col1"}

    def test_wildcard_expansion_dict_wildcard(self):
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

    def test_wildcard_expansion_dict_regex(self):
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

    def test_wildcard_not(self):
        """
        Test wildcard that uses a not column
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["col1","col2","col3"],
            ["*", "-col1"]
        )
        assert columns == ['col2', 'col3']

    def test_wildcard_not_exclamation_start_name(self):
        """
        Test that a column starting with a - can still be selected
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["-col1","col2","col3"],
            ["-col1"]
        )
        assert columns == ['-col1']

    def test_not_star(self):
        """
        Test wildcard that uses a not column with a * as a wildcard
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["a", "col1","col2","col3"],
            ["col*", "-*3"]
        )
        assert columns == ['col1', 'col2']

    def test_not_regex(self):
        """
        Test using not regex
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["a", "col1","col2","col3"],
            ["col*", "-regex:.*3"]
        )
        assert columns == ['col1', 'col2']

    def test_not_regex_alt_syntax(self):
        """
        Test using not regex alternative syntax
        """
        columns = wrangles.recipe._wildcard_expansion(
            ["a", "col1","col2","col3"],
            ["col*", "regex:-.*3"]
        )
        assert columns == ['col1', 'col2']

    def test_star_regex_special_chars(self):
        """
        Test that regex special characters are escaped
        correctly when using a wildcard
        """
        columns = wrangles.recipe._wildcard_expansion(
            [".col1",".col2",":col3"],
            [".col*"]
        )
        assert columns == ['.col1', '.col2']

    def test_not_in_recipe(self):
        """
        Test not syntax in a recipe
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 10
                values:
                    header1: value1
                    header2: value2
                    header3: value3
                columns:
                    - "*"
                    - -header1
            """
        )
        assert (
            df.columns.tolist() == ["header2", "header3"] and
            len(df) == 10
        )

    def test_not_syntax_error(self):
        """
        Test that a likely syntax error by adding a space
        after the dash gives a clear error message
        """
        with pytest.raises(ValueError, match="without a space"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 10
                    values:
                      header1: value1
                      header2: value2
                      header3: value3
                    columns:
                      - "*"
                      - - header1
                """
            )

    def test_only_not_string(self):
        """
        Test not syntax in a recipe
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 10
                values:
                    header1: value1
                    header2: value2
                    header3: value3
                columns: -header1
            """
        )
        assert (
            df.columns.tolist() == ["header2", "header3"] and
            len(df) == 10
        )

    def test_only_not_list(self):
        """
        Test not syntax in a recipe
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 10
                values:
                    header1: value1
                    header2: value2
                    header3: value3
                columns:
                  - -header1
                  - -header2
            """
        )
        assert (
            df.columns.tolist() == ["header3"] and
            len(df) == 10
        )

    def test_non_matching_wildcard(self):
        """
        Test error message - wildcard expansion finds no matches
        """
        data = pd.DataFrame({
            'name': ['hammer', 'wrench', 'cable'],
            'val1': ['13 kg', '5kg', '1kg'],
            'val2': ['13cm', '12cm', '30cm'],
            'val3': ['blue', 'silver', 'orange']
        })
        with pytest.raises(KeyError) as info:
            raise wrangles.recipe.run(
                """
                wrangles:
                - format.trim:
                    input: attr*
                """,
                dataframe=data
            )
        assert (
            info.typename == 'KeyError' and
            'Wildcard expansion pattern did not find any matching columns' in info.value.args[0]
        )

    def test_non_matching_wildcard_as_list(self):
        """
        Test error message - wildcard expansion finds no matches as list
        """
        data = pd.DataFrame({
            'name': ['hammer', 'wrench', 'cable'],
            'val1': ['13 kg', '5kg', '1kg'],
            'val2': ['13cm', '12cm', '30cm'],
            'val3': ['blue', 'silver', 'orange']
        })
        with pytest.raises(KeyError) as info:

            wrangles.recipe.run(
                """
                wrangles:
                - format.trim:
                    input:
                      - attr*
                """,
                dataframe=data
            )
        assert (
            info.typename == 'KeyError' and
            'Wildcard expansion pattern did not find any matching columns' in info.value.args[0]
        )

    def test_non_matching_wildcard_non_existing_inputs(self):
        """
        Test error message - two inputs that do not exists
        """
        data = pd.DataFrame({
            'name': ['hammer', 'wrench', 'cable'],
            'val1': ['13 kg', '5kg', '1kg'],
            'val2': ['13cm', '12cm', '30cm'],
            'val3': ['blue', 'silver', 'orange']
        })
        with pytest.raises(KeyError) as info:

            wrangles.recipe.run(
                """
                wrangles:
                - format.trim:
                    input:
                      - attr*
                      - nothing
                """,
                dataframe=data
            )
        assert (
            info.typename == 'KeyError' and
            "format.trim - 'Column nothing does not exist'" in info.value.args[0]
        )



def test_run_as_string():
    """
    Test a run defined as a string runs correctly assuming there are no parameters.
    """
    ref_values = []

    def set_value():
        ref_values.append(1)

    wrangles.recipe.run(
        """
        run:
          on_start:
            - custom.set_value
        """,
        functions=set_value
    )
    assert ref_values == [1]

def test_read_as_string():
    """
    Test a read defined as a string runs correctly assuming there are no parameters.
    """
    def get_values():
        return pd.DataFrame({
            'header': ['value']
        })

    df = wrangles.recipe.run(
        """
        read:
          - custom.get_values
        """,
        functions=get_values
    )
    assert df["header"][0] == "value"

def test_wrangle_as_string():
    """
    Test a wrangle defined as a string runs correctly assuming there are no parameters.
    """
    def set_values(df):
        df['header'] = "value1"
        return df

    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        wrangles:
          - custom.set_values
        """,
        functions=set_values
    )
    assert df["header"][0] == "value1"

def test_write_as_string():
    """
    Test a write defined as a string runs correctly assuming there are no parameters.
    """
    ref_values = []

    def write_values(df):
        ref_values.append(df['header'][0])

    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        write:
          - custom.write_values
        """,
        functions=write_values
    )
    assert ref_values == ["value"]

def test_enhanced_error_message_long_recipe():  
    """  
    Test that error messages clearly identify the failed wrangle in a long recipe  
    """  
    def failing_function(df):  
        raise RuntimeError("This is the actual error from wrangle #5")  
      
    def working_function(df):  
        df["temp"] = "processed"  
        return df  
      
    recipe = """  
    read:  
      - test:  
          rows: 5  
          values:  
            col1: value1  
      
    wrangles:  
      - custom.working_function: {}  
      - convert.case:  
          input: col1  
          output: step2  
          case: upper  
      - custom.working_function: {}  
      - format.trim:  
          input: step2  
          output: step4  
      - custom.failing_function: {}  
      - custom.working_function: {}  
      - convert.case:  
          input: temp  
          output: final  
          case: lower  
    """  
      
    with pytest.raises(RuntimeError, match=r"ERROR IN WRANGLE: custom.failing_function - This is the actual error from wrangle #5"):  
        wrangles.recipe.run(recipe, functions=[working_function, failing_function])

def test_enhanced_error_message_read_phase():  
    """Test error message prominence in read phase"""  
    def failing_read():  
        raise RuntimeError("Read operation failed")  
      
    with pytest.raises(RuntimeError, match=r"ERROR IN READ: custom.failing_read.*Read operation failed"):  
        wrangles.recipe.run(  
            """  
            read:  
              - custom.failing_read: {}  
            """,  
            functions=[failing_read]  
        )  
    
def test_enhanced_error_message_write_phase():  
    """Test error message prominence in write phase"""  
    def failing_write(df):  
        raise RuntimeError("Write operation failed")  
      
    with pytest.raises(RuntimeError, match=r"ERROR IN WRITE: custom.failing_write.*Write operation failed"):  
        wrangles.recipe.run(  
            """  
            read:  
              - test:  
                  rows: 1  
                  values:  
                    col1: test  
            write:  
              - custom.failing_write: {}  
            """,  
            functions=[failing_write]  
        )

def test_enhanced_error_message_nested_recipe():  
    """Test error messages work correctly with nested meta-wrangles"""  

    def working_function(df):  
        """A working custom function for testing"""  
        df["temp"] = "processed"  
        return df  
    
    def failing_function(df):  
        """A function that always fails"""  
        raise RuntimeError("Error in nested recipe")  
    
    # Test the batch wrangle with a failing function  
    with pytest.raises(RuntimeError, match="ERROR IN WRANGLE: batch - ERROR IN WRANGLE: custom.failing_function - Error in nested recipe"):  
        wrangles.recipe.run(  
            """  
            read:  
            - test:  
                rows: 5  
                values:  
                    column: value  
            
            wrangles:  
            - batch:  
                wrangles:  
                - custom.working_function: {}  
                - custom.failing_function: {}  
                - custom.working_function: {}  
            """,  
            functions={  
                "working_function": working_function,  
                "failing_function": failing_function  
            }  
        )