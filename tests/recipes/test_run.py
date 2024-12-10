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

def test_if_false():
    """
    Test that a run action is not triggered
    when an if statement is false
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
            - recipe:
                if: 1 == 2
                read:
                - test:
                    rows: 1
                    values:
                        header: value
                write:
                - memory:
                    id: run_if_should_not_run
        """
    )
    assert "run_if_should_not_run" not in wrangles.connectors.memory.dataframes

def test_if_true():
    """
    Test that run action is triggered
    when an if statement is true
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
            - recipe:
                if: 1 == 1
                read:
                - test:
                    rows: 1
                    values:
                        header: value
                write:
                - memory:
                    id: run_if_should_run
        """
    )
    assert "run_if_should_run" in wrangles.connectors.memory.dataframes

def test_if_variables_syntax():
    """
    Test that an if statement runs correctly
    when using variables using the syntax ${var}
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
            - recipe:
                if: ${var} == 1
                read:
                  - test:
                      rows: 1
                      values:
                        header: value
                write:
                  - memory:
                      id: run_if_variables_syntax_should_run
        """,
        variables={
            "var": 1
        }
    )

    assert "run_if_variables_syntax_should_run" in wrangles.connectors.memory.dataframes
