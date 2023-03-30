"""
Tests for generic write functionality.
"""
import wrangles
import pandas as pd


def test_specify_columns():
    """
    Test writing and selecting only a subset of columns
    """
    data = pd.DataFrame({
        'col1': ['val1'],
        'col2': ['val2']
    })
    recipe = """
    write:
      - dataframe: 
          columns:
            - col1
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ['col1']

def test_specify_columns_wildcard():
    """
    Test writing and selecting only a subset of columns using a wildcard
    """
    data = pd.DataFrame({
        'col1': ['val1'],
        'col2': ['val2']
    })
    recipe = """
    write:
      - dataframe: 
          columns:
            - col*
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns.tolist() == ['col1','col2']

def test_specify_columns_regex():
    """
    Test writing and selecting only a subset of columns using regex
    """
    data = pd.DataFrame({
        'col1': ['val1'],
        'col2': ['val2'],
        'col3a': ['val3']
    })
    recipe = """
    write:
      - dataframe: 
          columns:
            - "regex: col."
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns.tolist() == ['col1','col2']

def test_specify_not_columns():
    """
    Test writing and excluding a subset of columns
    """
    data = pd.DataFrame({
        'col1': ['val1'],
        'col2': ['val2']
    })
    recipe = """
    write:
      - dataframe: 
          not_columns:
            - col2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ['col1']

def test_specify_not_columns_wildcard():
    """
    Test writing and excluding a subset of columns using a wildcard
    """
    data = pd.DataFrame({
        'col1': ['val1'],
        'col2': ['val2'],
        '3col': ['val3']
    })
    recipe = """
    write:
      - dataframe: 
          not_columns:
            - col*
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ['3col']

def test_specify_not_columns_regex():
    """
    Test writing and excluding a subset of columns using a regex
    """
    data = pd.DataFrame({
        'col1': ['val1'],
        'col2': ['val2'],
        '3col': ['val3']
    })
    recipe = """
    write:
      - dataframe: 
          not_columns:
            - "regex: col."
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.columns == ['3col']

def test_specify_where():
    """
    Test writing and applying a WHERE sql criteria
    """
    data = pd.DataFrame({
        'col1': ['val1', 'val2', 'val3'],
        'col2': ['vala', 'valb', 'valc']
    })
    recipe = """
    write:
      - dataframe: 
          where: |
            col1 = 'val1'
            or col2 = 'valc'
            
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['col1'].values.tolist() == ['val1', 'val3']

def test_multiple():
    """
    Test writing more than one output
    """
    wrangles.recipe.run(
        """
        read:
          test:
            rows: 3
            values:
              Column1: aaa
              Column2: bbb
        write:
          - file:
              name: tests/temp/temp.txt
          - file:
              name: tests/temp/temp.csv
        """
    )
    df1 = wrangles.recipe.run(
        """
        read:
          file:
              name: tests/temp/temp.txt
        """
    )
    df2 = wrangles.recipe.run(
        """
        read:
          file:
            name: tests/temp/temp.csv
        """
    )
    assert (
        df1.columns.tolist() == ['Column1', 'Column2'] and
        len(df1) == 3 and
        df1['Column1'][0] == 'aaa' and
        df2.columns.tolist() == ['Column1', 'Column2'] and
        len(df2) == 3 and
        df2['Column2'][0] == 'bbb'
    )