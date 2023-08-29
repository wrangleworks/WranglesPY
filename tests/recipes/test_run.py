"""
Test generic run behavior.

Tests specific to an individual connector should go 
in a test file for the respective connectors
e.g. tests/connectors/test_notifications.py
"""
import pandas as pd
import wrangles
import pytest


def test_on_success():
    """
    Testing on success action is triggered correctly when finished
    """
    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    success_rec = """
    write:
      - file:
          name: tests/temp/temp2.csv
    """
    recipe = """
    run:
      on_success:
        - recipe:
            name: ${rec2}
    wrangles:
      - convert.case:
          input: col1
          output: out1
          case: upper
    """
    vars = {
        "rec2": success_rec
    }
    df = wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert df.iloc[0]['out1'] == 'HELLO WORLD'

def test_on_failure():
    """
    Testing on failure action is triggered correctly
    """
    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    failure_rec = """
    write:
      - file:
          name: tests/temp/temp3.csv
    """
    recipe = """
    run:
      on_failure:
        - recipe:
            name: ${rec2}
    wrangles:
        - convert.case:
            input: col111
            output: out
            case: upper
    """
    vars = {
        "rec2": failure_rec
    }
    with pytest.raises(KeyError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert (
        info.typename == 'KeyError' and
        "Column col111" in info.value.args[0]
    )
