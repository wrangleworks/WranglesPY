"""
Tests for generic write functionality.
"""
import wrangles
import pandas as pd


def test_write_columns():
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

def test_write_columns_wildcard():
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

def test_write_columns_regex():
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

def test_write_not_columns():
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

def test_write_not_columns_wildcard():
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

def test_write_not_columns_regex():
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

def test_write_where():
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
