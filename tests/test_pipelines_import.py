import wrangles


# Files
## CSV
def test_import_csv():
    """
    Test a basic .csv import
    """
    recipe = """
      import:
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
      import:
        file:
          name: tests/samples/data.txt
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_csv_fields():
    """
    Test a csv import where user has selected only a subset of the fields
    """
    recipe = """
      import:
        file:
          name: tests/samples/data.csv
          fields:
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
      import:
        file:
          name: tests/samples/data.json
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_json_fields():
    """
    Test a json import where user has selected a subset of fields
    """
    recipe = """
      import:
        file:
          name: tests/samples/data.json
          fields:
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
      import:
        file:
          name: tests/samples/data.xlsx
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace']

def test_import_excel_fields():
    """
    Test a basic .xlsx import
    """
    recipe = """
      import:
        file:
          name: tests/samples/data.xlsx
          fields:
            - Find
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find']