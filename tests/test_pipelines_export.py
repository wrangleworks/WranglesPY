import wrangles

recipe = """
read:
  file:
    name: tests/samples/data.csv
"""
df_base = wrangles.pipeline.run(recipe)


def test_export_df_fields():
    """
    Test returning a dateframe where user has defined the fields
    """
    recipe = """
      write:
        dataframe:
          fields:
            - Find
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_base)
    assert df.columns.tolist() == ['Find']


def test_export_csv():
    """
    Test exporting a .csv
    """
    recipe = """
      write:
        file:
          name: temp.csv
    """
    wrangles.pipeline.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.csv
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 3

def test_export_txt():
    """
    Test exporting a .txt
    """
    recipe = """
      write:
        file:
          name: temp.txt
    """
    wrangles.pipeline.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.txt
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 3

def test_export_json():
    """
    Test exporting a .json
    """
    recipe = """
      write:
        file:
          name: temp.json
          orient: records
    """
    wrangles.pipeline.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.json
          orient: records
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 3

def test_export_csv_fields():
    """
    Test exporting a .json
    """
    recipe = """
      write:
        file:
          name: temp.csv
          fields:
            - Find
    """
    wrangles.pipeline.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.csv
          fields:
            - Find
    """
    df = wrangles.pipeline.run(recipe)
    assert df.columns.tolist() == ['Find'] and len(df) == 3

def test_export_multiple():
    """
    Test exporting a .txt
    """
    recipe = """
      write:
        - file:
            name: temp.txt
        - file:
            name: temp.csv
    """
    wrangles.pipeline.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.txt
    """
    df1 = wrangles.pipeline.run(recipe)
    recipe = """
      read:
        file:
          name: temp.csv
    """
    df2 = wrangles.pipeline.run(recipe)
    assert df1.columns.tolist() == ['Find', 'Replace'] and len(df1) == 3 and df2.columns.tolist() == ['Find', 'Replace'] and len(df2)