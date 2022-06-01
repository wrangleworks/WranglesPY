import wrangles
import pandas as pd


#
# Remove Duplicates
#
df_test_remove_duplicates = pd.DataFrame([[['Agent Smith', 'Agent Smith', 'Agent Smith']]], columns=['Agents'])
def test_remove_duplicates():
    recipe = """
    wrangles:
    - format.remove_duplicates:
        input: Agents
        output: Remove
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_remove_duplicates)
    assert df.iloc[0]['Remove'] == ['Agent Smith']

#
# Trim
#
df_test_trim = pd.DataFrame([['         Wilson!         ']], columns=['Alone'])

def test_trim():
    recipe = """
    wrangles:
    - format.trim:
        input: 
        - Alone
        output: Trim
    """
    df = wrangles.pipeline.run(recipe, dataframe=df_test_trim)
    assert df.iloc[0]['Trim'] == 'Wilson!'