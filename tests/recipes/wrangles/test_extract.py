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
    
# if the input is multiple columns (a list)
def test_address_5():
    data = pd.DataFrame({
        'col1': ['221 B Baker St., London, England, United Kingdom'],
        'col2': ['742 Evergreen St, Springfield, USA']
    })
    recipe = """
    wrangles:
      - extract.address:
          input:
            - col1
            - col2
          output:
            - out1
            - out2
          dataType: streets
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out2'][0] == '742 Evergreen St'
    
# if the input and output are not the same type
def test_address_multi_input():
    data = pd.DataFrame({
        'street': ['221 B Baker St.'],
        'city': ['London'],
        'region': ['England'],
        'country': ['United Kingdom']
    })
    recipe = """
    wrangles:
      - extract.address:
          input:
            - street
            - city
            - region
            - country
          output: out
          dataType: streets
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out'] == ['221 B Baker St.']

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
    assert df.iloc[0]['Attributes'][0] in ['13deg', '13°']

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
    assert df.iloc[0]['Attributes'][0] in ['13m^2', '13sq m']

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
    assert df.iloc[0]['Attributes'][0] in ['13m^3', '13cu m']

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
    
# if the input is multiple columns (a list)
def test_attributes_multi_col():
    data = pd.DataFrame({
        'col1': ['13 something 13kg 13 random'],
        'col2': ['3 something 3kg 3 random'],
    })
    recipe = """
    wrangles:
        - extract.attributes:
            input:
              - col1
              - col2
            output:
              - out1
              - out2
            responseContent: span
            attribute_type: mass
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out2'] == ['3kg']
    
# if the input and output are not the same type
def test_attributes_diff_type():
    data = pd.DataFrame({
        'col1': ['13 something 13kg 13 random'],
        'col2': ['3 something 3kg 3 random'],
    })
    recipe = """
    wrangles:
        - extract.attributes:
            input:
              - col1
              - col2
            output: out
            responseContent: span
            attribute_type: mass
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out'] == ['13kg', '3kg']
    
# if the input and output are different lengths
def test_attributes_single_input_multi_output():
    data = pd.DataFrame({
        'col1': ['13 something 13kg 13 random'],
        'col2': ['3 something 3kg 3 random'],
    })
    recipe = """
    wrangles:
        - extract.attributes:
            input: col1
            output: 
              - out1
              - out2
            responseContent: span
            attribute_type: mass
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Extract must output to a single column or equal amount of columns as input.'

#
# Codes
#
def test_codes_inconsistent_input_output():
    """
    Check error if user provides inconsistent lists for input and output
    """
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
            - code_a
            - code_b
            - code_c
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Extract must output to a single column or equal amount of columns as input.'

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

def test_extract_codes_one_input_multi_output():
    recipe = """
    wrangles:
      - extract.codes:
          input: 
            - code1
          output:
            - out1
            - out2
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=df_test_codes_multi_input)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Extract must output to a single column or equal amount of columns as input.'

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

def test_custom_one_output():
    """
    Test using extract.custom with a single output
    """
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
    df =  wrangles.recipe.run(recipe, dataframe=data)
    assert df['Fact Out'][0] == ['Charizard']

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

def test_extract_custom_labels():
    """
    Test use_labels option to group output
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.custom:
              input: col1
              output: col2
              model_id: 829c1a73-1bfd-4ac0
              use_labels: true
        """,
        dataframe = pd.DataFrame({
            'col1': ['small blue cotton jacket']
        })
    )
    assert (
        df['col2'][0]['colour'] == ['blue'] and
        df['col2'][0]['size'] == ['small']
    )

# Extract Regex Extract
def test_extract_regex():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.regex:
          input: col
          output: col_out
          find: Pikachu
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col_out'] == ['Pikachu']
    
    
# incorrect model_id - forget to use ${}
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

def test_extract_with_standardize_model_id():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: col_out
          model_id: 6ca4ab44-8c66-40e8
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == 'Using standardize model_id 6ca4ab44-8c66-40e8 in an extract function.'

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

def test_extract_custom_multi_input():
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
    assert (
        'Charizard' in df['Fact Output'][0] and
        'Pikachu' in df['Fact Output'][0]
    )

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
    
# multiple different custom extract at the same time
def test_extract_multi_custom():
    data = pd.DataFrame({
        'Pokemon': ['my favorite pokemon is Charizard'],
        'AI':['My favorite AIs are Dolores and TARS both from are great']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - Pokemon
            - AI
          output:
            - Fact1
            - Fact2
          model_id:
            - 1eddb7e8-1b2b-4a52
            - 05f6bb73-de04-4cb6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Fact2'][0] in ['Dolores', 'TARS']

def test_extract_custom_first_only():
    """
    Test that the first only parameter works correctly. use_labels is False
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: Pikachu vs Charizard

        wrangles:
          - extract.custom:
              input: header
              output: results
              model_id: 1eddb7e8-1b2b-4a52
              use_labels: false
              first_element: True
        """
    )
    assert df['results'][0] == 'Pikachu'


# combinations of use_labels and first_element begins
def test_use_labels_true_and_first_element_true():
    """
    Use_labels and first_element set to true. output is a dictionary with only one value (string)    
    """
    data = pd.DataFrame({
        'col': ['colour: blue size: small colour: green']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: true
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'colour': 'blue', 'size': 'small'} or {'colour': 'green', 'size': 'small'}
    
def test_use_labels_false_first_element_true():
    """
    Use labels is false and first element is true. output is a string only
    """
    data = pd.DataFrame({
        'col': ['colour: blue size: small colour: green size: large']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: false
          first_element: true
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == 'size: small' or df['out'][0] == 'colour: green' or df['out'][0] == 'colour: blue'

def test_use_labels_multiple():
    """
    Use labels true and first element is false. output is a dictionary where values are lists
    Testing use labels with multiple same labels and other labels
    """
    data = pd.DataFrame({
        'col': ['colour: blue size: small colour: black']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'size': ['small'], 'colour': ['blue', 'black']} or df['out'][0] == {'colour': ['black', 'blue'], 'size': ['small']}
    
def test_use_labels_same_key():
    """
    Testing use labels where multiple labels that are the same only. 
    This should put all of the values from the same labels in a list
    """
    data = pd.DataFrame({
        'col': ['colour: blue colour: green colour: black']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    df['out'][0]['colour'] == ['green', 'blue', 'black']
    
def test_unlabeled_in_use_labels():
    """
    Testing unlabeled key. This everything that is not specified in the labels
    """
    data = pd.DataFrame({
        'col': ['colour: blue colour: green colour: black red']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    df['out'][0] == {'colour': ['green', 'blue', 'black'], 'Unlabeled': ['red']}
    
def test_unlabeled_only():
    """
    Getting unlabeled only
    """
    data = pd.DataFrame({
        'col': ['my color is red']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'Unlabeled': ['red']}
    
def test_unlabeled_only_with_first_element_true():
    """
    Unlabeled only with first_element set to true
    """
    data = pd.DataFrame({
        'col': ['my color is red']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: true
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'Unlabeled': 'red'}
    
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
    
# if the input is multiple columns (a list)
def test_properties_5():
    data = pd.DataFrame({
        'col1': ['Why is the sky blue?'],
        'col2': ['Temperature of a star if it looks blue'],
    })
    recipe = """
    wrangles:
      - extract.properties:
          input:
            - col1
            - col2
          output:
            - out1
            - out2
          property_type: colours
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out2'] == ['Blue']
    
# if the input and output are not the same type
def test_properties_6():
    data = pd.DataFrame({
        'col1': ['Why is the sky blue?'],
        'col2': ['Temperature of a star if it looks blue'],
    })
    recipe = """
    wrangles:
      - extract.properties:
          input:
            - col1
            - col2
          output: out
          property_type: colours
    """

    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out'] == ['Blue', 'Sky Blue']
    
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
    
# if the input is multi column (a list)
def test_extract_brackets_2():
    data = pd.DataFrame({
        'col': ['[1234]'],
        'col2': ['{1234}'],
    })
    recipe = """
    wrangles:
      - extract.brackets:
          input:
            - col
            - col2
          output:
            - no_brackets
            - no_brackets2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['no_brackets2'] == '1234'
    
# if the input and output are not the same type
def test_extract_brackets_3():
    data = pd.DataFrame({
        'col': ['[12345]'],
        'col2': ['{1234}'],
    })
    recipe = """
    wrangles:
      - extract.brackets:
          input:
            - col
            - col2
          output: output
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == '12345, 1234'

# if the input and output are not the same type
def test_extract_brackets_multi_input():
    data = pd.DataFrame({
        'col': ['[12345]'],
        'col2': ['[6789]'],
    })
    recipe = """
    wrangles:
      - extract.brackets:
          input:
            - col
            - col2
          output: output
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == '12345, 6789'
    
#
# Date Properties
#

# Basic function
def test_date_properties_1():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: col1
          output: out1
          property: quarter
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == 4
    
# not valid property types
def test_date_properties_2():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: col1
          output: out1
          property: millennium
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == '"millennium" not a valid date property.'

# Multiple inputs to single output
def test_date_properties_multi_input():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
        'col2': ['4/24/2023']
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: 
            - col1
            - col2
          output: out1
          property: week_day_name
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == ['Sunday','Monday']

# Multiple inputs and outputs
def test_date_properties_multi_input_multi_output():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
        'col2': ['4/24/2023']
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: 
            - col1
            - col2
          output: 
            - out1
            - out2
          property: week_day_name
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == 'Sunday' and df.iloc[0]['out2'] == 'Monday'
    
#
# Date range
#

# basic function
def test_date_range_1():
    data = pd.DataFrame({
      'date1': ['08-13-1992'],
      'date2': ['08-13-2022'],
    })
    recipe = """
    wrangles:
      - extract.date_range:
          start_time: date1
          end_time: date2
          output: Range
          range: years
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Range'] == 29
    
    
# invalid range
def test_date_range_2():
    data = pd.DataFrame({
      'date1': ['08-13-1992'],
      'date2': ['08-13-2022'],
    })
    recipe = """
    wrangles:
      - extract.date_range:
          start_time: date1
          end_time: date2
          output: Range
          range: millennium
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert info.typename == 'ValueError' and info.value.args[0] == '"millennium" not a valid frequency'
