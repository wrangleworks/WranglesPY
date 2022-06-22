import wrangles

recipe = """
read:
  file:
    name: tests/samples/data.csv
"""
df_base = wrangles.recipe.run(recipe)


def test_export_df_columns():
    """
    Test returning a dateframe where user has defined the columns
    """
    recipe = """
      write:
        dataframe:
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe, dataframe=df_base)
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
    wrangles.recipe.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.csv
    """
    df = wrangles.recipe.run(recipe)
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
    wrangles.recipe.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.txt
    """
    df = wrangles.recipe.run(recipe)
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
    wrangles.recipe.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.json
          orient: records
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 3

def test_export_csv_columns():
    """
    Test exporting a .json
    """
    recipe = """
      write:
        file:
          name: temp.csv
          columns:
            - Find
    """
    wrangles.recipe.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.csv
          columns:
            - Find
    """
    df = wrangles.recipe.run(recipe)
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
    wrangles.recipe.run(recipe, dataframe=df_base)
    recipe = """
      read:
        file:
          name: temp.txt
    """
    df1 = wrangles.recipe.run(recipe)
    recipe = """
      read:
        file:
          name: temp.csv
    """
    df2 = wrangles.recipe.run(recipe)
    assert df1.columns.tolist() == ['Find', 'Replace'] and len(df1) == 3 and df2.columns.tolist() == ['Find', 'Replace'] and len(df2)