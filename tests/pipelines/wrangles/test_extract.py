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
    
# Input is list
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

# Output is list
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