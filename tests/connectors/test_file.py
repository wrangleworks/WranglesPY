"""
Test the file connector for reading and writing files to the local file system.
"""
import wrangles
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
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(
            """
            read:
              - file:
                  name: data.jason
            """
        )
    assert (
        info.typename == 'ValueError' and 
        info.value.args[0] == "File type 'jason' is not supported by the file connector."
    )

def test_write_unsupported_filetype():
    """
    # Exporting file type error message
    """
    recipe = """
      read:
        file:
          name: tests/temp/temp.csv
      
      write:
        - file:
            name: tests/temp/data.jason
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert info.typename == 'ValueError' and info.value.args[0] == "File type 'jason' is not supported by the file connector."

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
