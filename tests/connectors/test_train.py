import wrangles
import pandas as pd
import pytest

#
# Classify
#
def test_classify_read():
    """
    Testing reading classify wrangle data (using Food data)
    """
    recipe = """
    read:
      - train.classify:
          model_id: a62c7480-500e-480c
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['Category'] == 'Grains'

def test_classify_write():
    """
    Writing data to a Wrangle (re-training)
    """
    recipe = """
    write:
      - train.classify:
          columns:
            - Example
            - Category
            - Notes
          model_id: a62c7480-500e-480c
    """
    data = pd.DataFrame({
        'Example': ['rice', 'milk', 'beef'],
        'Category': ['Grains', 'Dairy', 'Meat'],
        'Notes': ['Notes here', 'and here', 'and also here']
    })
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert len(df) == 3

def test_classify_write_2():
    """
    Train with incorrect columns
    """
    with pytest.raises(ValueError, match="must be provided for train.classify"):
        wrangles.recipe.run(
            """
            write:
            - train.classify:
                columns:
                    - Example2
                    - Category2
                    - Notes2
                model_id: a62c7480-500e-480c
            """,
            dataframe=pd.DataFrame({
                'Example2': ['rice', 'milk', 'beef'],
                'Category2': ['Grains', 'Dairy', 'Meat'],
                'Notes2': ['Notes here', 'and here', 'and also here']
            })
        )

def test_classify_error():
    """
    Not Providing model_id or name in train wrangles
    """
    with pytest.raises(ValueError, match="name or a model id must be provided"):
        wrangles.recipe.run(
            """
            write:
            - train.classify:
                columns:
                    - Example
                    - Category
                    - Notes
            """,
            dataframe=pd.DataFrame({
                'Example': ['rice', 'milk', 'beef'],
                'Category': ['Grains', 'Dairy', 'Meat'],
                'Notes': ['Notes here', 'and here', 'and also here']
            })
        )

def test_classify_read_two_cols_wrgl(mocker):
    """
    Wrangle that contains only two columns
    """
    m1 = mocker.patch("wrangles.data.model_content")
    m1.return_value = {
        "Data": [['Hello', 'Wrangles'], ['Hello', 'Python']]
    }
    df = wrangles.recipe.run(
        """
        read:
        - train.classify:
            model_id: a62c7480-500e-480c
        """
    )
    assert df.iloc[0].tolist() == ['Hello', 'Wrangles', '']

def test_classify_read_four_cols_error(mocker):
    """
    Wrangles that does not contain 3 columns
    """
    m1 = mocker.patch("wrangles.data.model_content")
    m1.return_value = {
        "Data": [['Hello']]
    }
    with pytest.raises(ValueError, match="contain three columns"):
        wrangles.recipe.run(
            """
            read:
            - train.classify:
                model_id: a62c7480-500e-480c
            """
        )


#
# Extract
#
def test_extract_read():
    """
    Read extract wrangle data
    """
    recipe = """
    read:
      - train.extract:
          model_id: ee5f020e-d88e-4bd5
    """
    df = wrangles.recipe.run(recipe)
    assert len(df) == 3

def test_extract_write():
    """
    Writing data to a wrangle (re-training)
    """
    recipe = """
    write:
      - train.extract:
          columns:
            - Entity to Find
            - Variation (Optional)
            - Notes
          model_id: ee5f020e-d88e-4bd5
    """
    data = pd.DataFrame({
        'Entity to Find': ['Rachel', 'Dolores', 'TARS'],
        'Variation (Optional)': ['', '', ''],
        'Notes': ['Blade Runner', 'Westworld', 'Interstellar'],
    })
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Entity to Find'] == 'Rachel'

def test_extract_write_2():
    """
    Incorrect columns for extract read
    """
    with pytest.raises(ValueError, match="must be provided for train.extract"):
        wrangles.recipe.run(
            """
            write:
            - train.extract:
                columns:
                    - Entity to Find2
                    - Variation (Optional)2
                    - Notes2
                model_id: ee5f020e-d88e-4bd5
            """,
            dataframe=pd.DataFrame({
                'Entity to Find2': ['Rachel', 'Dolores', 'TARS'],
                'Variation (Optional)2': ['', '', ''],
                'Notes2': ['Blade Runner', 'Westworld', 'Interstellar'],
            })
        )

def test_extract_read_two_cols_wrgl(mocker):
    """
    Wrangle that contains only two columns
    """
    m1 = mocker.patch("wrangles.data.model_content")
    m1.return_value = {
        "Data": [['Hello', 'Wrangles'], ['Hello', 'Python']]
    }
    recipe = """
    read:
      - train.extract:
          model_id: a62c7480-500e-480c
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0].tolist() == ['Hello', 'Wrangles', '']

def test_extract_read_four_cols_error(mocker):
    """
    Wrangles that does not contain 3 columns
    """
    m1 = mocker.patch("wrangles.data.model_content")
    m1.return_value = {
        "Data": [['Hello']]
    }
    with pytest.raises(ValueError, match="contain three columns"):
        wrangles.recipe.run(
            """
            read:
            - train.extract:
                model_id: a62c7480-500e-480c
            """
        )

def test_extract_error():
    """
    Not Providing model_id or name in train wrangles
    """
    with pytest.raises(ValueError, match="name or a model id must be provided"):
        wrangles.recipe.run(
            """
            write:
            - train.extract:
                columns:
                    - Entity to Find
                    - Variation (Optional)
                    - Notes
            """,
            dataframe=pd.DataFrame({
                'Entity to Find': ['Rachel', 'Dolores', 'TARS'],
                'Variation (Optional)': ['', '', ''],
                'Notes': ['Blade Runner', 'Westworld', 'Interstellar'],
            })
        )


#
# Standardize
#
def test_standardize_read_1():
    """
    
    """
    df = wrangles.recipe.run(
        """
        read:
        - train.standardize:
            model_id: fc7d46e3-057f-47bd
        """
    )
    assert len(df) == 2
    
def test_standardize_write_1():
    """
    
    """
    df = wrangles.recipe.run(
        """
        write:
        - train.standardize:
            columns:
                - Find
                - Replace
                - Notes
            model_id: fc7d46e3-057f-47bd
        """,
        dataframe=pd.DataFrame({
            'Find': ['ASAP', 'ETA'],
            'Replace': ['As Soon As Possible', 'Estimated Time of Arrival'],
            'Notes': ['For pytests', ''],
        })
    )
    assert df.iloc[0]['Find'] == 'ASAP'

def test_standardize_write_2():
    """
    Write standardize with incorrect columns
    """
    with pytest.raises(ValueError, match="Find, Replace, Notes"):
        wrangles.recipe.run(
            """
            write:
            - train.standardize:
                columns:
                  - Find2
                  - Replace2
                  - Notes2
                model_id: fc7d46e3-057f-47bd
            """,
            dataframe=pd.DataFrame({
        'Find2': ['ASAP', 'ETA'],
        'Replace2': ['As Soon As Possible', 'Estimated Time of Arrival'],
        'Notes2': ['For pytests', ''],
        })
    )

def test_standardize_read_two_cols_wrgl(mocker):
    """
    Wrangle that contains only two columns
    """
    m1 = mocker.patch("wrangles.data.model_content")
    m1.return_value = {
        "Data": [['Hello', 'Wrangles'], ['Hello', 'Python']]
    }
    df = wrangles.recipe.run(
        """
        read:
        - train.standardize:
            model_id: a62c7480-500e-480c
        """
    )
    assert df.iloc[0].tolist() == ['Hello', 'Wrangles', '']

def test_standardize_read_incorrect_cols_error(mocker):
    """
    wrangles that does not contain 3 columns
    """
    m1 = mocker.patch("wrangles.data.model_content")
    m1.return_value = {
        "Data": [['Hello']]
    }
    with pytest.raises(ValueError, match="contain three columns"):
        wrangles.recipe.run(
            """
            read:
            - train.standardize:
                model_id: a62c7480-500e-480c
            """
        )

def test_standardize_error():
    """
    Test that not providing a model_id or name gives a clear error
    """
    with pytest.raises(ValueError, match="name or a model id must be provided"):
        wrangles.recipe.run(
            """
            write:
            - train.standardize:
                columns:
                    - Find
                    - Replace
                    - Notes
            """,
            dataframe=pd.DataFrame({
                'Find': ['rice', 'milk', 'beef'],
                'Replace': ['Grains', 'Dairy', 'Meat'],
                'Notes': ['Notes here', 'and here', 'and also here']
            })
        )
