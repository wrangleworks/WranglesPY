import wrangles
import openpyxl


# Files
## CSV
def test_import_csv():
    """
    Test a basic .csv import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.csv
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_txt():
    """
    Test a basic .txt import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.txt
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_csv_columns():
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
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find']


## JSON
def test_import_json():
    """
    Test a basic .json import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.json
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_json_columns():
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
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find']


## Excel
def test_import_excel():
    """
    Test a basic .xlsx import
    """
    recipe = """
      read:
        file:
          name: tests/samples/data.xlsx
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_excel_columns():
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
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find']   
    
## JSON Lines
def test_read_jsonl_file():
    recipe = """
    read:
      file:
        name: tests/samples/data.jsonl
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

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
          name: tests/samples/write_data.xlsx
          index: true
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']
    
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
          name: tests/samples/write_data.xlsx
          index: true
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']
    
# Write a json lines file
def test_write_file_jsonl():
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
          name: tests/samples/write_data.jsonl
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']