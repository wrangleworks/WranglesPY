import wrangles
import pandas as pd


#
# CASE
#
df_test_case = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])

def test_case_default():
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Data1'] == 'a string'

def test_case_input_list():
    recipe = """
    wrangles:
      - convert.case:
          input:
            - Data1
            - Data2
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Data1'] == 'a string' and df.iloc[0]['Data2'] == 'another string'

def test_case_output():
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          output: Column
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Column'] == 'a string'

def test_case_output_list():
    recipe = """
    wrangles:
      - convert.case:
          input:
            - Data1
            - Data2
          output:
            - Column1
            - Column2
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Column1'] == 'a string' and df.iloc[0]['Column2'] == 'another string'

def test_case_lower():
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: lower
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Data1'] == 'a string'

def test_case_upper():
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: upper
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Data1'] == 'A STRING'
    
def test_case_title():
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: title
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Data1'] == 'A String'

def test_case_sentence():
    recipe = """
    wrangles:
      - convert.case:
          input: Data1
          case: sentence
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_case)
    assert df.iloc[0]['Data1'] == 'A string'

#
# Data Type
#
df_test_data_type = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])

def test_data_type_str():
    recipe = """
    wrangles:
      - convert.data_type:
          input: Data1
          data_type: str
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_data_type)
    assert isinstance(df.iloc[0]['Data1'], str)


#
# To JSON
#
df_test_to_json = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])

def test_to_json_array():
    recipe = """
    
    """