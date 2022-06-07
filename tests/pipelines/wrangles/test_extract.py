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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['streets'] == ['221 B Baker St.']
    
def test_address_cities():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: cities
            dataType: cities
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['cities'] == ['London']
    
def test_address_countries():
    recipe = """
    wrangles:
            - extract.address:
                input: location
                output: country
                dataType: countries
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_address)
    print(df.iloc[0]['country'] == ['United Kingdom'])
    
def test_address_regions():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: regions
            dataType: regions
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_address)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes)
    print(df.iloc[0]['Attributes'] == {'length': [{'unit': 'metre', 'value': 0.5}], 'mass': [{'unit': 'kilogram', 'value': 5.0}]})
    

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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13hp', '13W']

# Testing Power
def test_attributes_pressure():
    recipe = """
    wrangles:
        - extract.attributes:
            input: Tools
            output: Attributes
            responseContent: span
            attribute_type: pressure
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_attributes_all)
    assert df.iloc[0]['Attributes'] == ['13kg']

#
# Codes
#

# Input is string
df_test_codes = pd.DataFrame([['to gain access use Z1ON0101']], columns=['secret'])

def test_extract_codes():
    recipe = """
    wrangles:
      - extract.codes:
          input: secret
          output: code
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_codes)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_codes_list)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_codes_multi_input)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_codes_multi_input)
    assert df.iloc[0]['out2'] == ['Z1ON0101-2']

    
#
# Custom Extraction
#

# Input is String
df_test_custom = pd.DataFrame([['My favorite pokemon is charizard!']], columns=['Fact'])

def test_extract_custom():
    recipe = """
    wrangles:
      - extract.custom:
          input: Fact
          output: Fact Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_custom)
    assert df.iloc[0]['Fact Output'] == ['Charizard']

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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_custom_list)
    assert df.iloc[0]['Fact Output'] == ['Pikachu', 'Mew', 'Charizard']

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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_custom_multi_input)
    assert df.iloc[0]['Fact Output'] == ['Charizard', 'Pikachu']

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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_custom_multi_input)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['Blue', 'Red', 'White']
    
def test_extract_materials():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: materials
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['Titanium']
    
def test_extract_shapes():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: shapes
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['Round']
    
def test_extract_standards():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: standards
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_properties)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_html)
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
    df = wrangles.pipeline.run(recipe, dataframe=df_test_html)
    assert df.iloc[0]['Links'] == ['https://www.wrangleworks.com/']