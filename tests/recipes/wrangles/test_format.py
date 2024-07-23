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
    assert (
        info.typename == 'ValueError' and
        "The lists for" in info.value.args[0]
    )

def test_remove_duplicates_where():
    """
    Test format.remove_duplicates using where
    """
    data = pd.DataFrame({
        'duplicates': ['duplicate duplicate', 'and another and another', 'last one last one'],
        'numbers': [32, 45, 67]
    })
    recipe = """
    wrangles:
    - format.remove_duplicates:
        input: duplicates
        output: Remove
        where: numbers != 45
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Remove'] == 'duplicate' and df.iloc[1]['Remove'] == ''

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
    
# trim input is a string
def test_trim_2():
    data = pd.DataFrame([['         Wilson!         ']], columns=['Alone'])
    recipe = """
    wrangles:
    - format.trim:
        input: Alone
        output: Trim
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Trim'] == 'Wilson!'

def test_trim_where():
    """
    Test trim using where
    """
    data = pd.DataFrame({
        'column': ['         Wilson!         ', '     Where   ', 'are   ', '    you!?   '], 
        'numbers': [3, 6, 9, 12]
    })
    recipe = """
    wrangles:
    - format.trim:
        input: column
        output: Trim
        where: numbers > 5
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['Trim'] == 'Where' and df.iloc[0]['Trim'] == ''

# Test list of input and output columns
def test_trim_list_to_list():
    """
    Test trim with a list of input and output columns
    """
    data = pd.DataFrame([['         Wilson!         ', '          Where are you?!         ']], columns=['Alone', 'Out To Sea'])
    recipe = """
    wrangles:
      - format.trim:
          input:
            - Alone
            - Out To Sea
          output:
            - Trim1
            - Trim2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Trim1'] == 'Wilson!' and df.iloc[0]['Trim2'] == 'Where are you?!'

# Test error with a list of input columns and a single output
def test_trim_list_to_single_output():
    """
    Test trim with a list of input columns and a single output column
    """
    data = pd.DataFrame([['         Wilson!         ', '          Where are you?!         ']], columns=['Alone', 'Out To Sea'])
    recipe = """
    wrangles:
      - format.trim:
          input:
            - Alone
            - Out To Sea
          output:
            - Trim1
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        'The lists for input and output must be the same length.' in info.value.args[0]
    )

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
    assert (
        info.typename == 'ValueError' and
        "The lists for" in info.value.args[0]
    )

def test_prefix_where():
    """
    Test format.prefix using where
    """
    data = pd.DataFrame({
        'col': ['terrestrial', 'ordinary', 'califragilisticexpialidocious'],
        'numbers': [5, 4, 3]
    })
    recipe = """
    wrangles:
      - format.prefix:
          input: col
          output: pre-col
          value: extra-
          where: numbers = 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['pre-col'] == '' and df.iloc[2]['pre-col'] == 'extra-califragilisticexpialidocious'
    
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
    assert (
        info.typename == 'ValueError' and
        "The lists for" in info.value.args[0]
    )

def test_suffix_where():
    """
    Test formart.suffix using where
    """
    data = pd.DataFrame({
        'col': ['urgen', 'efficien', 'supercalifragilisticexpialidocious'],
        'numbers': [3, 45, 99]
    })
    recipe = """
    wrangles:
      - format.suffix:
          input: col
          output: col-suf
          value: -cy
          where: numbers = 99
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col-suf'] == '' and df.iloc[2]['col-suf'] == 'supercalifragilisticexpialidocious-cy'
    
#
# date format
#

def test_date_format_1():
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
    
def test_date_format_where():
    """
    Test format.date using where
    """
    data = pd.DataFrame({
        'date': ['8/13/1992', '11/10/1987'],
        'people': ['Mario', 'Thomas']
    })
    recipe = """
    wrangles:
      - format.dates:
          input: date
          format: "%Y-%m-%d"
          where: people = 'Mario'
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['date'] == '1992-08-13' and df.iloc[1]['date'] == '11/10/1987'

#
# pad
#

# Normal operation left
def test_pad_1():
  data = pd.DataFrame({
    'col1': ['7']
  })
  recipe = """
  wrangles:
    - format.pad:
        input: col1
        output: out1
        pad_length: 3
        side: left
        char: 0
  """
  df = wrangles.recipe.run(recipe, dataframe=data)
  assert df.iloc[0]['out1'] == '007'
  
# output no specified
def test_pad_2():
  data = pd.DataFrame({
    'col1': ['7']
  })
  recipe = """
  wrangles:
    - format.pad:
        input: col1
        pad_length: 3
        side: left
        char: 0
  """
  df = wrangles.recipe.run(recipe, dataframe=data)
  assert df.iloc[0]['col1'] == '007'
  
# List of output and input columns
def test_pad_list_to_list():
  """
  Test pad with a list of input and output columns
  """
  data = pd.DataFrame({
    'col1': ['7'],
    'col2': ['8']
  })
  recipe = """
  wrangles:
    - format.pad:
        input: 
          - col1
          - col2
        output:
          - out1
          - out2
        pad_length: 3
        side: left
        char: 0
  """
  df = wrangles.recipe.run(recipe, dataframe=data)
  assert df.iloc[0]['out1'] == '007' and df.iloc[0]['out2'] == '008'

# List of input columns to a single output column
def test_pad_list_to_single_output():
  """
  Test error with a list of input columns and a single output column
  """
  data = pd.DataFrame({
    'col1': ['7'],
    'col2': ['8']
  })
  recipe = """
  wrangles:
    - format.pad:
        input: 
          - col1
          - col2
        output: out1
        pad_length: 3
        side: left
        char: 0
  """
  with pytest.raises(ValueError) as info:
    raise wrangles.recipe.run(recipe, dataframe=data)
  assert (
      info.typename == 'ValueError' and
      'The lists for input and output must be the same length.' in info.value.args[0]
  )

def test_pad_where():
  data = pd.DataFrame({
    'col1': ['7', '5', '9'],
    'numbers': [3, 4, 5]
  })
  recipe = """
  wrangles:
    - format.pad:
        input: col1
        output: out1
        pad_length: 3
        side: left
        char: 0
        where: numbers = 3
  """
  df = wrangles.recipe.run(recipe, dataframe=data)
  assert df.iloc[0]['out1'] == '007' and df.iloc[2]['out1'] == ''
  
#
# Significant Figures
#
def test_sig_figs():
    """
    Test converting multiple number types to desired
    significant figures using default settings
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
        - format.significant_figures:
            input: col1
            output: out1
        """,
        dataframe=pd.DataFrame({
            'col1': [
                '13.45644 ft',
                'length: 34453.3323ft',
                '34.234234',
                'nothing here',
                13.4565,
                1132424,
                ''
            ]
        })
    )
    assert (
        df['out1'].to_list() == [
            '13.5 ft',
            'length: 34500ft',
            '34.2',
            'nothing here',
            13.5,
            1130000,
            ''
        ]
    )

def test_sig_figs_with_value():
    """
    Test converting multiple number types to desired
    significant figures with a specified value
    """
    df = wrangles.recipe.run(
        recipe="""
        wrangles:
        - format.significant_figures:
            input: col1
            output: out1
            significant_figures: 4
        """,
        dataframe=pd.DataFrame({
            'col1': [
                '13.45644 ft',
                'length: 34453.3323ft',
                '34.234234',
                'nothing here',
                13.4565,
                1132424,
                ''
            ]
        })
    )
    assert (
        df['out1'].to_list() == [
            '13.46 ft',
            'length: 34450ft',
            '34.23',
            'nothing here',
            13.46,
            1132000,
            ''
        ]
    )

class TestFormatAttributes:
    """
    Format (standardize) attributes or remove them
    """

    def test_format_attributes_all(self):
        """
        Testing standardizing all attributes in text
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters of gasoline with a battery of 14 volts"]
        })

        df = wrangles.recipe.run(
            recipe="""
            wrangles:
                - format.attributes:
                    input: input
                    output: output
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 ft car has a mass of 190 kg and it holds 13 l of gasoline with a battery of 14 V']

    def test_format_attributes_non_existing_units(self):
        """
        Testing a non existent units
        """
        data = pd.DataFrame({
            'input': ["my 13 metre car has a quantonium of 13Rx and that's random 13 number"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - format.attributes:
                input: input
                output: output
            """,
            dataframe=data
        )
        assert df['output'][0] == ["my 13 m car has a quantonium of 13Rx and that's random 13 number"]


    def test_format_specific_attribute_length(self):
        """
        Standardize a specific attribute in text
        Length
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters and the wheel is 4cm wide with 10 mm of thread left"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - format.attributes:
                input: input
                output: output
                attribute_type: length
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 ft car has a mass of 190kg and it holds 13 liters and the wheel is 4 cm wide with 10 mm of thread left']

    def test_format_specific_attribute_mass(self):
        """
        Standardize a specific attribute in text
        Mass
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters and the wheel is 4cm wide with 10 mm of thread left"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - format.attributes:
                input: input
                output: output
                attribute_type: mass
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 foot car has a mass of 190 kg and it holds 13 liters and the wheel is 4cm wide with 10 mm of thread left']

    def test_format_specific_attribute_volume(self):
        """
        Attribute specified not present in text
        Volume
        """
        data = pd.DataFrame({
            'input': ['My 13 foot car has a mass of 190kg and the wheel is 4cm']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - format.attributes:
                input: input
                output: output
                attribute_type: volume
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 foot car has a mass of 190kg and the wheel is 4cm']

    # Testing remive attributes

    def test_remove_attributes_all(self):
        """
        Testing remove all attributes. Using the remove_attributes function
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters of gasoline with a battery of 14 volts"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - format.remove_attributes:
                input: input
                output: output
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a mass of and it holds of gasoline with a battery of ']

    def test_remove_attributes_specific_attribute_length(self):
        """
        remove a specific attribute (length)
        Using attributes function
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters of gasoline with a battery of 14 volts and 10cm of thread left"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - format.attributes:
                input: input
                output: output
                attribute_type: length
                removeAttributes: True
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a mass of 190kg and it holds 13 liters of gasoline with a battery of 14 volts and of thread left']