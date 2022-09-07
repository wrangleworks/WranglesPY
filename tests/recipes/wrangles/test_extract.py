import pytest
import wrangles
import pandas as pd

#
# Address
#
df_test_address = pd.DataFrame([['221 B Baker St., London, England, United Kingdom']], columns=['location'])

def test_address_street():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: streets
            dataType: streets
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['streets'] == ['221 B Baker St.']
    
def test_address_cities():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: cities
            dataType: cities
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['cities'] == ['London']
    
def test_address_countries():
    recipe = """
    wrangles:
            - extract.address:
                input: location
                output: country
                dataType: countries
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['country'] == ['United Kingdom']
    
def test_address_regions():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: regions
            dataType: regions
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['regions'] == ['England']
    
#
# Attributes
#

# Testing span
df_test_attributes = pd.DataFrame([['hammer 5kg, 0.5m']], columns=['Tools'])

def test_attributes_span():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes)
    assert df.iloc[0]['Attributes'] == {'length': ['0.5m'], 'mass': ['5kg']}

# Testing Object
def test_attributes_object():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: object
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes)
    assert df.iloc[0]['Attributes'] == {'length': [{'symbol': 'm', 'unit': 'metre', 'value': 0.5}], 'mass': [{'symbol': 'kg', 'unit': 'kilogram', 'value': 5.0}]}

df_test_attributes_all = pd.DataFrame([['hammer 13kg, 13m, 13deg, 13m^2, 13A something random 13hp 13N and 13W, 13psi random 13V 13m^3 stuff ']], columns=['Tools'])

# Testing Angle
def test_attributes_angle():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: angle
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13deg']

# Testing area 
def test_attributes_area():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: area
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13m^2']

# Testing Current
def test_attributes_current():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: current
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13A']

# Testing Force
def test_attributes_force():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: force
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13N']

# Testing Length
def test_attributes_length():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: length
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13m']

# Testing Power
def test_attributes_power():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: power
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13hp', '13W']

# Testing Pressure
def test_attributes_pressure():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: pressure
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13psi']

# Testing electric potential
def test_attributes_voltage():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: electric potential
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13V']

# Testing volume
def test_attributes_volume():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: volume
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13m^3']

# Testing mass
def test_attributes_mass():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: mass
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13kg']
    
# min/mid/max attributes
def test_attributes_MinMidMax():
    data = pd.DataFrame({
        'Tools': ['object mass ranges from 13kg to 14.5kg to 18.2kg']
    })
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: mass
            bound: Minimum
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Invalid boundary setting. min, mid or max permitted.'

#
# Codes
#

# Len input != len output
def test_extract_codes_1():
    data = pd.DataFrame({
        'col1': ['to gain access use Z1ON0101'],
        'col2': ['to gain access use Z1ON0101']
    })
    recipe = """
    wrangles:
      - extract.codes:
          input:
            - col1
            - col2
          output: 
            - code
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'If providing a list of inputs, a corresponding list of outputs must also be provided.'

# Input is string
df_test_codes = pd.DataFrame([['to gain access use Z1ON0101']], columns=['secret'])

def test_extract_codes_2():
    recipe = """
    wrangles:
      - extract.codes:
          input: secret
          output: code
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes)
    assert df.iloc[0]['code'] == ['Z1ON0101']
    
# column is a list
df_test_codes_list = pd.DataFrame([[['to', 'gain', 'access', 'use', 'Z1ON0101']]], columns=['secret'])

def test_extract_codes_list():
    recipe = """
    wrangles:
      - extract.codes:
          input: secret
          output: code
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes_list)
    assert df.iloc[0]['code'] == ['Z1ON0101']
    

# Multiple columns as inputs
df_test_codes_multi_input = pd.DataFrame(
  {
    'code1': ['code Z1ON0101-1'],
    'code2': ['code Z1ON0101-2']
  }
)

def test_extract_codes_milti_input():
    recipe = """
    wrangles:
      - extract.codes:
          input: 
            - code1
            - code2
          output: Codes
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes_multi_input)
    assert df.iloc[0]['Codes'] == ['Z1ON0101-1', 'Z1ON0101-2']

# Multiple outputs and Inputs
def test_extract_codes_milti_input_output():
    recipe = """
    wrangles:
      - extract.codes:
          input: 
            - code1
            - code2
          output:
            - out1
            - out2
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes_multi_input)
    assert df.iloc[0]['out2'] == ['Z1ON0101-2']

    
#
# Custom Extraction
#

# Input is String
df_test_custom = pd.DataFrame([['My favorite pokemon is charizard!']], columns=['Fact'])

def test_extract_custom_1():
    recipe = """
    wrangles:
      - extract.custom:
          input: Fact
          output: Fact Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom)
    assert df.iloc[0]['Fact Output'] == ['Charizard']

# Input is String
df_test_custom = pd.DataFrame([['My favorite pokemon is charizard!']], columns=['Fact'])

# Len input != Len output
def test_extract_custom_2():
    data = pd.DataFrame({
        'col1': ['My favorite pokemon is charizard!'],
        'col2': ['My favorite pokemon is charizard2!']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output:
            - Fact Out
          model_id: 1eddb7e8-1b2b-4a52
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'If providing a list of inputs, a corresponding list of outputs must also be provided.'

# Incorrect model_id missing "${ }" around value
def test_extract_custom_3():
    data = pd.DataFrame({
        'col1': ['My favorite pokemon is charizard!'],
        'col2': ['My favorite pokemon is charizard2!']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output:
            - Fact Out
            - Fact Out 2
          model_id: noWork
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX'
    
    
# Mini Extract
def test_extract_custom_4():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: col_out
          find: Pikachu
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col_out'] == ['Pikachu']
    
    
# Mini Extract with model id also included -> Error
def test_extract_custom_5():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: col_out
          find: Pikachu
          model_id: 1eddb7e8-1b2b-4a52
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Extract custom must have model_id or find as parameters'

# incorrect model_id - forget to use ${}
# Mini Extract with model id also included -> Error
def test_extract_custom_6():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: col_out
          model_id: {model_id_here}
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value'

# Input column is list
df_test_custom_list = pd.DataFrame([[['Charizard', 'Cat', 'Pikachu', 'Mew', 'Dog']]], columns=['Fact'])

def test_extract_custom_list():
    recipe = """
    wrangles:
      - extract.custom:
          input: Fact
          output: Fact Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom_list)
    assert df.iloc[0]['Fact Output'][0] in ['Pikachu', 'Mew', 'Charizard']

# Testing Multi column input
df_test_custom_multi_input = pd.DataFrame(
  {
    'col1': ['First Place Pikachu'],
    'col2': ['Second Place Charizard']
  }
)

def test_extract_custom_mulit_input():
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output: Fact Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom_multi_input)
    assert df.iloc[0]['Fact Output'][0] in ['Charizard', 'Pikachu']

# Multiple output and inputs
def test_extract_custom_mulit_input_output():
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output:
            - Fact1
            - Fact2
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom_multi_input)
    assert df.iloc[0]['Fact2'] == ['Charizard']


#
# Properties
#
df_test_properties = pd.DataFrame([['OSHA approved Red White Blue Round Titanium Shield']], columns=['Tool'])

def test_extract_colours():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: colours
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    check_list = ['Blue', 'Red', 'White']
    assert df.iloc[0]['prop'][0] in check_list and df.iloc[0]['prop'][1] in check_list and df.iloc[0]['prop'][2] in check_list
    
def test_extract_materials():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: materials
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['Titanium']
    
def test_extract_shapes():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: shapes
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['Round']
    
def test_extract_standards():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: standards
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['OSHA']
    
    
#
# HTML
#

# text
df_test_html = pd.DataFrame([r'<a href="https://www.wrangleworks.com/">Wrangle Works!</a>'], columns=['HTML'])

def test_extract_html_text():
    recipe = """
    wrangles:
      - extract.html:
          input: HTML
          output: 
            - Text
          data_type: text
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_html)
    assert df.iloc[0]['Text'] == 'Wrangle Works!'
    
# Links
def test_extract_html_links():
    recipe = """
    wrangles:
      - extract.html:
          input: HTML
          output: 
            - Links
          data_type: links
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_html)
    assert df.iloc[0]['Links'] == ['https://www.wrangleworks.com/']
    
#
# Brackets
#

def test_extract_brackets_1():
    data = pd.DataFrame({
        'col': ['[1234]', '{1234}']
    })
    recipe = """
    wrangles:
      - extract.brackets:
          input: col
          output: no_brackets
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['no_brackets'] == '1234'
    
    
#
# Remove Words
#

# tokenize inputs
def test_remove_words_1():
    data = pd.DataFrame({
        'col': ['Metal Carbon Water Tank'],
        'materials': ['Metal Carbon']
    })
    recipe = """
    wrangles:
      - remove_words:
          input: col
          to_remove:
            - materials
          output: Out
          tokenize_to_remove: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == 'Water Tank'
    
    
# tokenize inputs and ignore case
def test_remove_words_2():
    data = pd.DataFrame({
        'col': ['METAl CaRBon WateR TaNk'],
        'materials': ['meTAL carbOn']
    })
    recipe = """
    wrangles:
      - remove_words:
          input: col
          to_remove:
            - materials
          output: Out
          tokenize_to_remove: True
          ignore_case: True
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == 'Water Tank'

# Raw inputs, ignore case is False
def test_remove_words_3():
    data = pd.DataFrame({
        'col': ['METAl CaRBon WateR TaNk'],
        'materials': ['meTAL CaRBon']
    })
    recipe = """
    wrangles:
      - remove_words:
          input: col
          to_remove:
            - materials
          output: Out
          tokenize_to_remove: True
          ignore_case: False
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['Out'].iloc[0] == 'METAl WateR TaNk'