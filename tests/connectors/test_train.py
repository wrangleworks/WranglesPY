import wrangles
import pandas as pd
import pytest

#
# Classify
#

# testing reading classify wrangle data (using Food data)
def test_classify_read():
    recipe = """
    read:
      - train.classify:
          model_id: a62c7480-500e-480c
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['Category'] == 'Grains'
    
# Writing data to a Wrangle (re-training)
def test_classify_write():
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
    
# Train with incorrect columns
def test_classify_write_2():
    recipe = """
    write:
      - train.classify:
          columns:
            - Example2
            - Category2
            - Notes2
          model_id: a62c7480-500e-480c
    """
    data = pd.DataFrame({
        'Example2': ['rice', 'milk', 'beef'],
        'Category2': ['Grains', 'Dairy', 'Meat'],
        'Notes2': ['Notes here', 'and here', 'and also here']
    })
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The columns Example, Category, Notes must be provided for train.classify.'
    
    
# Not Providing model_id or name in train wrangles
def test_classify_error():
    recipe = """
    write:
      - train.classify:
          columns:
            - Example
            - Category
            - Notes
    """
    data = pd.DataFrame({
        'Example': ['rice', 'milk', 'beef'],
        'Category': ['Grains', 'Dairy', 'Meat'],
        'Notes': ['Notes here', 'and here', 'and also here']
    })
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "Either a name or a model id must be provided"
    
# Wrangle that contains only two columns
def test_classify_read_two_cols_wrgl(mocker):
    m1 = mocker.patch("wrangles.data.model_data")
    m1.return_value = [['Hello', 'Wrangles'], ['Hello', 'Python']]
    recipe = """
    read:
      - train.classify:
          model_id: a62c7480-500e-480c
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0].tolist() == ['Hello', 'Wrangles', '']
    
# wrangles that does not contain 3 columns
def test_classify_read_four_cols_error(mocker):
    m1 = mocker.patch("wrangles.data.model_data")
    m1.return_value = [['Hello']]
    recipe = """
    read:
      - train.classify:
          model_id: a62c7480-500e-480c
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert info.typename == 'ValueError' and info.value.args[0] == "Classify Wrangle data should contain three columns. Check Wrangle data"

#
# Extract
#

# read extract wrangle data
def test_extract_read():
    recipe = """
    read:
      - train.extract:
          model_id: ee5f020e-d88e-4bd5
    """
    df = wrangles.recipe.run(recipe)
    assert len(df) == 3
    
    
# writing data to a wrangle (re-training)
def test_extract_write():
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
    
# Incorrect columns for extract read
def test_extract_write_2():
    recipe = """
    write:
      - train.extract:
          columns:
            - Entity to Find2
            - Variation (Optional)2
            - Notes2
          model_id: ee5f020e-d88e-4bd5
    """
    data = pd.DataFrame({
        'Entity to Find2': ['Rachel', 'Dolores', 'TARS'],
        'Variation (Optional)2': ['', '', ''],
        'Notes2': ['Blade Runner', 'Westworld', 'Interstellar'],
    })
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The columns Entity to Find, Variation (Optional), Notes must be provided for train.extract.'
    
# Wrangle that contains only two columns
def test_extract_read_two_cols_wrgl(mocker):
    m1 = mocker.patch("wrangles.data.model_data")
    m1.return_value = [['Hello', 'Wrangles'], ['Hello', 'Python']]
    recipe = """
    read:
      - train.extract:
          model_id: a62c7480-500e-480c
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0].tolist() == ['Hello', 'Wrangles', '']
    
# wrangles that does not contain 3 columns
def test_extract_read_four_cols_error(mocker):
    m1 = mocker.patch("wrangles.data.model_data")
    m1.return_value = [['Hello']]
    recipe = """
    read:
      - train.extract:
          model_id: a62c7480-500e-480c
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert info.typename == 'ValueError' and info.value.args[0] == "Extract Wrangle data should contain three columns. Check Wrangle data"
    
# Not Providing model_id or name in train wrangles
def test_extract_error():
    recipe = """
    write:
      - train.extract:
          columns:
            - Entity to Find
            - Variation (Optional)
            - Notes
    """
    data = pd.DataFrame({
        'Entity to Find': ['Rachel', 'Dolores', 'TARS'],
        'Variation (Optional)': ['', '', ''],
        'Notes': ['Blade Runner', 'Westworld', 'Interstellar'],
    })
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "Either a name or a model id must be provided"


#
# Standardize
#

def test_standardize_read_1():
    recipe = """
    read:
      - train.standardize:
          model_id: fc7d46e3-057f-47bd
    """
    df = wrangles.recipe.run(recipe)
    assert len(df) == 2
    
def test_standardize_write_1():
    recipe = """
    write:
      - train.standardize:
          columns:
            - Find
            - Replace
            - Notes
          model_id: fc7d46e3-057f-47bd
    """
    data = pd.DataFrame({
        'Find': ['ASAP', 'ETA'],
        'Replace': ['As Soon As Possible', 'Estimated Time of Arrival'],
        'Notes': ['For pytests', ''],
    })
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Find'] == 'ASAP'
    
# write standardize with incorrect columns
def test_standardize_write_2():
    recipe = """
    write:
      - train.standardize:
          columns:
            - Find2
            - Replace2
            - Notes2
          model_id: fc7d46e3-057f-47bd
    """
    data = pd.DataFrame({
        'Find2': ['ASAP', 'ETA'],
        'Replace2': ['As Soon As Possible', 'Estimated Time of Arrival'],
        'Notes2': ['For pytests', ''],
    })
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'The columns Find, Replace, Notes must be provided for train.standardize.'
    
# Wrangle that contains only two columns
def test_standardize_read_two_cols_wrgl(mocker):
    m1 = mocker.patch("wrangles.data.model_data")
    m1.return_value = [['Hello', 'Wrangles'], ['Hello', 'Python']]
    recipe = """
    read:
      - train.standardize:
          model_id: a62c7480-500e-480c
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0].tolist() == ['Hello', 'Wrangles', '']
    
# wrangles that does not contain 3 columns
def test_standardize_read_four_cols_error(mocker):
    m1 = mocker.patch("wrangles.data.model_data")
    m1.return_value = [['Hello']]
    recipe = """
    read:
      - train.standardize:
          model_id: a62c7480-500e-480c
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert info.typename == 'ValueError' and info.value.args[0] == "Standardize Wrangle data should contain three columns. Check Wrangle data"
    
    
# Not Providing model_id or name in train wrangles
def test_standardize_error():
    recipe = """
    write:
      - train.standardize:
          columns:
            - Find
            - Replace
            - Notes
    """
    data = pd.DataFrame({
        'Find': ['rice', 'milk', 'beef'],
        'Replace': ['Grains', 'Dairy', 'Meat'],
        'Notes': ['Notes here', 'and here', 'and also here']
    })
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "Either a name or a model id must be provided"