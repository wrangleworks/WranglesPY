import wrangles

recipe = """
read:
  file:
    name: tests/samples/data.csv
"""
df_base = wrangles.pipeline.run(recipe)


def test_pandas_head():
    """
    Test using pandas head function
    """
    recipe = """
      wrangles:
        - pandas.head:
            parameters:
              n: 1
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_base)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 1

def test_pandas_tail():
    """
    Test using pandas tail function
    """
    recipe = """
      wrangles:
        - pandas.tail:
            parameters:
              n: 1
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_base)
    assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 1