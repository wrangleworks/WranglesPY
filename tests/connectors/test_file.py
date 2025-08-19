"""
Test the file connector for reading and writing files to the local file system.
"""
import uuid as _uuid
import wrangles
import pandas as _pd
import pytest

def test_read_csv():
    """
    Test a basic .csv import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.csv
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_read_txt():
    """
    Test a basic .txt import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.txt
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_read_json():
    """
    Test a basic .json import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.json
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_read_excel():
    """
    Test a basic .xlsx import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.xlsx
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

## JSON Lines
def test_read_jsonl():
    recipe = """
    read:
      file:
        name: tests/samples/data.jsonl
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_read_csv_columns():
    """
    Test a csv import where user has selected only a subset of the columns
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.csv
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find']

def test_read_json_columns():
    """
    Test a json import where user has selected a subset of columns
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.json
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find']

def test_read_excel_columns():
    """
    Test a basic .xlsx import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.xlsx
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find']   

# Write using index
def test_write_file_indexed():
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            case: lower
    write:
        file:
          name: tests/temp/write_data.xlsx
          index: true
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_write_file_optional_col():
    """
    Tests an optional column that is there
    """
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            output: find
            case: lower
    write:
        file:
          name: tests/temp/write_data.xlsx
          columns:
            - Find
            - Replace
            - find?
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace', 'find']

def test_write_file_optional_not_col():
    """
    Tests an optional column that is not there
    """
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            output: Find
            case: lower
    write:
        file:
          name: tests/temp/write_data.xlsx
          columns:
            - Find
            - Replace
            - find?
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_write_csv():
    """
    Test exporting a .csv
    """
    wrangles.recipe.run(
        """
          read:
            - test:
               rows: 5
               values:
                 Find: aaa
                 Replace: bbb
          write:
            file:
               name: tests/temp/temp.csv
        """
    )
    df = wrangles.recipe.run(
        """
          read:
            file:
              name: tests/temp/temp.csv
        """
    )
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5

def test_write_txt():
    """
    Test exporting a .txt
    """
    wrangles.recipe.run(
        """
          read:
            - test:
               rows: 5
               values:
                 Find: aaa
                 Replace: bbb
          write:
            file:
               name: tests/temp/temp.txt
        """
    )
    df = wrangles.recipe.run(
        """
          read:
            file:
              name: tests/temp/temp.txt
        """
    )
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5

def test_write_json():
    """
    Test exporting a .json
    """
    wrangles.recipe.run(
        """
          read:
            - test:
               rows: 5
               values:
                 Find: aaa
                 Replace: bbb
          write:
            file:
               name: tests/temp/temp.json
               orient: records
        """
    )
    df = wrangles.recipe.run(
        """
          read:
            file:
              name: tests/temp/temp.json
              orient: records
        """
    )
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5

# Write a json lines file
def test_write_jsonl():
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            case: lower
    write:
        file:
          name: tests/temp/write_data.jsonl
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_read_unsupported_filetype():
    """
    Check an appropriate error is given if the user 
    tries to read an unknown file type
    """
    with pytest.raises(ValueError, match="'jason'"):
        wrangles.recipe.run(
            """
            read:
              - file:
                  name: data.jason
            """
        )

def test_write_unsupported_filetype():
    """
    # Exporting file type error message
    """
    with pytest.raises(ValueError, match="'jason'"):
        wrangles.recipe.run(
            """
            read:
                - file:
                    name: tests/temp/temp.csv
            
            write:
                - file:
                    name: tests/temp/data.jason
            """
        )

# Write using index
def test_write_with_index():
    recipe = """
    read:
      file:
        name: tests/samples/data.xlsx
    wrangles:
        - convert.case:
            input: Find
            case: lower
    write:
        file:
          name: tests/temp/write_data.xlsx
          index: true
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_write_pickle():
    """
    Test writing a pickle file
    """
    filename = str(_uuid.uuid4())
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
        write:
          - file:
              name: tests/temp/${filename}.pkl
        """,
        variables={"filename": filename}
    )
    df = _pd.read_pickle(f"tests/temp/{filename}.pkl")
    assert (
        df["header1"][0] == "value1"
        and len(df) == 5
    )

def test_write_pickle_gzip():
    """
    Test writing a pickle file that's gzipped
    """
    filename = str(_uuid.uuid4())
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
        write:
          - file:
              name: tests/temp/${filename}.pkl.gz
        """,
        variables={"filename": filename}
    )
    df = _pd.read_pickle(f"tests/temp/{filename}.pkl.gz")
    assert (
        df["header1"][0] == "value1"
        and len(df) == 5
    )

def test_read_pickle():
    """
    Test reading a pickle file
    """
    filename = str(_uuid.uuid4())
    _pd.DataFrame(
        {"header1": ["value1", "value2", "value3"]}
    ).to_pickle(f"tests/temp/{filename}.pkl")

    df = wrangles.recipe.run(
        """
        read:
          - file:
              name: tests/temp/${filename}.pkl
        """,
        variables={"filename": filename}
    )
    
    assert (
        df["header1"][0] == "value1"
        and len(df) == 3
    )

def test_read_pickle_gzip():
    """
    Test reading a pickle file that's gzipped
    """
    filename = str(_uuid.uuid4())
    _pd.DataFrame(
        {"header1": ["value1", "value2", "value3"]}
    ).to_pickle(f"tests/temp/{filename}.pkl.gz")

    df = wrangles.recipe.run(
        """
        read:
          - file:
              name: tests/temp/${filename}.pkl.gz
        """,
        variables={"filename": filename}
    )
    
    assert (
        df["header1"][0] == "value1"
        and len(df) == 3
    )

def test_read_object():
    """
    Test reading a file passed directly into the recipe as an object
    """
    df = wrangles.recipe.run(
      """
      read:
        - file:
            name: ${file}
      """,
      variables={
        "file": {
          "name": "example.csv",
          "mimeType": "text/csv",
          "data": "Q29sMSxDb2wyCmEseApiLHkKYyx6Cg=="
        }
      }
    )
    assert len(df) == 3 and df['Col1'][0] == 'a'

def test_read_object_json():
    """
    Test reading a file passed directly into the recipe as an object
    where the variable was JSON
    """
    df = wrangles.recipe.run(
      """
      read:
        - file:
            name: ${file}
      """,
      variables={
        "file": """{
          "name": "example.csv",
          "mimeType": "text/csv",
          "data": "Q29sMSxDb2wyCmEseApiLHkKYyx6Cg=="
        }"""
      }
    )
    assert len(df) == 3 and df['Col1'][0] == 'a'
