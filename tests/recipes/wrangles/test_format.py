import wrangles
import pandas as pd
import pytest

#
# Remove Duplicates
#
# Input column is a list
def test_remove_duplicates_1():
    data = pd.DataFrame([[['Agent Smith', 'Agent Smith', 'Agent Smith']]], columns=['Agents'])
    recipe = """
    wrangles:
    - format.remove_duplicates:
        input: Agents
        output: Remove
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Remove'] == ['Agent Smith']
    
# Input column is a str
def test_remove_duplicates_2():
    data = pd.DataFrame({
    'Agents': ['Agent Smith Agent Smith Agent Smith']
    })
    recipe = """
    wrangles:
    - format.remove_duplicates:
        input: Agents
        output: Remove
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Remove'] == 'Agent Smith'
    
# if the input is multiple columns (a list)
def test_remove_duplicates_3():
    data = pd.DataFrame({
    'Agents': ['Agent Smith Agent Smith Agent Smith'],
    'Clones': ['Commander Cody Commander Cody Commander Cody'],
    })
    recipe = """
    wrangles:
    - format.remove_duplicates:
        input:
          - Agents
          - Clones
        output:
          - Remove1
          - Remove2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Remove2'] == 'Commander Cody'
    
# if the input and output are not the same type
def test_remove_duplicates_4():
    data = pd.DataFrame({
    'Agents': ['Agent Smith Agent Smith Agent Smith'],
    'Clones': ['Commander Cody Commander Cody Commander Cody'],
    })
    recipe = """
    wrangles:
    - format.remove_duplicates:
        input:
          - Agents
          - Clones
        output: Remove2
    """

    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided."

#
# Trim
#
def test_trim_1():
    data = pd.DataFrame([['         Wilson!         ']], columns=['Alone'])
    recipe = """
    wrangles:
    - format.trim:
        input: 
        - Alone
        output: Trim
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Trim'] == 'Wilson!'

#    
# Prefix
#

# output column defined
def test_prefix_1():
    data = pd.DataFrame({
        'col': ['terrestrial', 'ordinary']
    })
    recipe = """
    wrangles:
      - format.prefix:
          input: col
          output: pre-col
          value: extra-
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['pre-col'][0] == 'extra-terrestrial'
    
# output column not defined
def test_prefix_2():
    data = pd.DataFrame({
        'col': ['terrestrial', 'ordinary']
    })
    recipe = """
    wrangles:
      - format.prefix:
          input: col
          value: extra-
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['col'][0] == 'extra-terrestrial'
    
# if the input is multiple lines
def test_prefix_3():
    data = pd.DataFrame({
        'col': ['terrestrial', 'ordinary'],
        'col2': ['terrestrial', 'ordinary'],
    })
    recipe = """
    wrangles:
      - format.prefix:
          input:
            - col
            - col2
          output:
            - out
            - out2
          value: extra-
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out2'][0] == 'extra-terrestrial'
    
# if the input and output are no the same type
def test_prefix_4():
    data = pd.DataFrame({
        'col': ['terrestrial', 'ordinary'],
        'col2': ['terrestrial', 'ordinary'],
    })
    recipe = """
    wrangles:
      - format.prefix:
          input:
            - col
            - col2
          output: out
          value: extra-
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided."
    
#    
# Suffix
#

# output column defined
def test_suffix_1():
    data = pd.DataFrame({
        'col': ['urgen', 'efficien']
    })
    recipe = """
    wrangles:
      - format.suffix:
          input: col
          output: col-suf
          value: -cy
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['col-suf'][0] == 'urgen-cy'
    
# output column not defined
def test_suffix_2():
    data = pd.DataFrame({
        'col': ['urgen', 'efficien']
    })
    recipe = """
    wrangles:
      - format.suffix:
          input: col
          value: -cy
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['col'][0] == 'urgen-cy'
    
# if the input is multiple columns(a list)
def test_suffix_3():
    data = pd.DataFrame({
        'col': ['urgen', 'efficien'],
        'col2': ['urgen', 'efficien'],
    })
    recipe = """
    wrangles:
      - format.suffix:
          input:
            - col
            - col2
          output:
            - out
            - out2
          value: -cy
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out2'][0] == 'urgen-cy'
    
# if the input and output are not the same type
def test_suffix_4():
    data = pd.DataFrame({
        'col': ['urgen', 'efficien'],
        'col2': ['urgen', 'efficien'],
    })
    recipe = """
    wrangles:
      - format.suffix:
          input:
            - col
            - col2
          output: out
          value: -cy
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == "If providing a list of inputs/outputs, a corresponding list of inputs/outputs must also be provided."
    
#
# date format
#

def test_data_format_1():
    data = pd.DataFrame({
        'col': ['8/13/1992']
    })
    recipe = """
    wrangles:
      - format.dates:
          input: col
          format: "%Y-%m-%d"
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col'] == '1992-08-13'