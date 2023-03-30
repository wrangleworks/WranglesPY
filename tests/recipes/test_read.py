"""
Test general read behaviour and special read functions.

Tests specific to an individual connector should go in a test
file for the respective connectors
e.g. tests/connectors/test_file.py
"""
import wrangles


# If they've entered a list, get the first key and value from the first element
def test_input_is_list():
    recipe = """
    read:
        - file:
            name: tests/samples/data.xlsx
        
    """
    df = wrangles.recipe.run(recipe)
    assert len(df.columns.to_list()) == 2

def test_union_files():
    """
    Testing Union of multiple sources together
    """
    df = wrangles.recipe.run(
        """
          read:
            - union:
                sources:
                  - test:
                      rows: 3
                      values:
                        column1: value1
                        column2: value2
                  - test:
                      rows: 3
                      values:
                        column1: value1
                        column2: value2
        """
    )
    assert (
        len(df) == 6 and 
        df.columns.to_list() == ['column1', 'column2']
    )

def test_concatenate_files():
    """
    Testing concatenating multiple sources
    """
    df = wrangles.recipe.run(
        """
          read:
            - concatenate:
                sources:
                  - test:
                      rows: 3
                      values:
                        column1: value1
                        column2: value2
                  - test:
                      rows: 3
                      values:
                        column3: value3
                        column4: value4
        """
    )
    assert (
        len(df) == 3 and
        df.columns.to_list() == ['column1', 'column2', 'column3', 'column4'] and
        df['column1'][0] == "value1" and
        df['column4'][0] == "value4"
    )

# Testing join of multiple sources
def test_join_files():
    recipe = """
    read:
        - join:
            how: inner
            left_on: Find
            right_on: Find2
            sources:
                - file:
                    name: tests/samples/data.xlsx
                - file:
                    name: tests/samples/data2.xlsx
    """
    df = wrangles.recipe.run(recipe)
    assert len(df.columns.to_list()) == 4