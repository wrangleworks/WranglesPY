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
          model_id: 94674750-f9e1-44af
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
          model_id: 94674750-f9e1-44af
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
                model_id: 94674750-f9e1-44af
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
            model_id: 94674750-f9e1-44af
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
                model_id: 94674750-f9e1-44af
            """
        )


class TestTrainExtract:
    """
    All tests for training extract wrangles
    """
    def test_extract_read(self):
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

    def test_extract_read_no_optional_label(self):
        """
        Read an extract that does not have (Optional) in Output column
        """
        recipe = """
        read:
          - train.extract:
              model_id: 5313d577-0bb6-4174
        """
        df = wrangles.recipe.run(recipe)
        assert len(df) == 3

    def test_extract_write_backwards_compatible(self):
        """
        Writing data to a wrangle using backwards compatibility
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

    def test_extract_write_backwards_compatible_adding_optional_label(self):
        """
        Adding data to a wrangle that does not have (Optional) in Output column
        """
        recipe="""
        write:
          - train.extract:
              columns:
                - Find
                - Output (Optional)
                - Notes
              model_id: 5313d577-0bb6-4174
        """
        data = pd.DataFrame({
            'Find': ['C#', 'F#', 'D#'],
            'Output (Optional)': ['C Sharp', 'F Sharp', 'D Sharp'],
            'Notes': ['', '', '']
        })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Output (Optional)'] == 'C Sharp'


    def test_extract_write(self):
        """
        Writing data to a wrangle (re-training)
        """
        recipe = """
        write:
        - train.extract:
            columns:
                - Find
                - Output (Optional)
                - Notes
            model_id: ee5f020e-d88e-4bd5
        """
        data = pd.DataFrame({
            'Find': ['Rachel', 'Dolores', 'TARS'],
            'Output (Optional)': ['', '', ''],
            'Notes': ['Blade Runner', 'Westworld', 'Interstellar'],
        })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Find'] == 'Rachel'

    def test_extract_write_no_optional_label(self):
        """
        Writing data to a wrangle re-training without (Optional)
        """
        recipe="""
        write:
          - train.extract:
              columns:
                - Find
                - Output
                - Notes
              model_id: 5313d577-0bb6-4174
        """
        data = pd.DataFrame({
            'Find': ['C#', 'F#', 'D#'],
            'Output': ['C Sharp', 'F Sharp', 'D Sharp'],
            'Notes': ['', '', '']
        })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Output'] == 'C Sharp'

    def test_extract_ai_write(self):
        """
        Writing data to a wrangle (re-training)
        """
        recipe = """
        write:
        - train.extract:
            model_id: d188e7a7-9de8-4565
        """
        data = pd.DataFrame({
            'Find': ['Finish', 'Length', 'Product Type'],
            'Description': ['The finish of the product', 'The length of the item in inches', 'The type of product'],
            'Type': ['string', 'string', 'string'],
            'Default': ['None', 'None', 'None'],
            'Examples': [['Chrome', 'Matte', 'Gloss'], ['12', '24', '36'], ['Furniture', 'Electronics', 'Clothing']],
            'Enum': [[], [], []],
            'Notes': ['Notes here', 'and here', 'and also here']
        })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Find'] == 'Finish'

    def test_extract_ai_write_name_and_model_id(self):
        """
        Writing data to an extract.ai wrangle with both name and model_id
        """
        with pytest.raises(ValueError, match="Name and model_id cannot both be provided, please use name to create a new model or model_id to update an existing model"):
            wrangles.recipe.run(
                """
                write:
                - train.extract:
                    model_id: d188e7a7-9de8-4565
                    name: My Wrangle Has a First Name, It's O-S-C-A-R
                """,
                dataframe=pd.DataFrame({
                    'Find': ['Finish', 'Length', 'Product Type'],
                    'Description': ['The finish of the product', 'The length of the item in inches', 'The type of product'],
                    'Type': ['string', 'string', 'string'],
                    'Default': ['None', 'None', 'None'],
                    'Examples': [['Chrome', 'Matte', 'Gloss'], ['12', '24', '36'], ['Furniture', 'Electronics', 'Clothing']],
                    'Enum': [[], [], []],
                    'Notes': ['Notes here', 'and here', 'and also here']
                })
            )

    def test_extract_ai_write_wrong_variant(self):
        """
        Writing data to an extract.ai wrangle with the wrong variant
        """
        with pytest.raises(ValueError, match="The variant must be either 'pattern' or 'ai'"):
            wrangles.recipe.run(
                """
                write:
                - train.extract:
                    name: My Wrangle
                    variant: WRONG
                """,
                dataframe=pd.DataFrame({
                    'Find': ['Finish', 'Length', 'Product Type'],
                    'Description': ['The finish of the product', 'The length of the item in inches', 'The type of product'],
                    'Type': ['string', 'string', 'string'],
                    'Default': ['None', 'None', 'None'],
                    'Examples': [['Chrome', 'Matte', 'Gloss'], ['12', '24', '36'], ['Furniture', 'Electronics', 'Clothing']],
                    'Enum': [[], [], []],
                    'Notes': ['Notes here', 'and here', 'and also here']
                })
            )

    def test_extract_ai_write_model_and_variant(self):
        """
        Writing data to an extract.ai wrangle with a model id and a variant
        """
        with pytest.raises(ValueError, match="It is not possible to set the variant of an existing model"):
            wrangles.recipe.run(
                """
                write:
                - train.extract:
                    model_id: d188e7a7-9de8-4565
                    variant: ai
                """,
                dataframe=pd.DataFrame({
                    'Find': ['Finish', 'Length', 'Product Type'],
                    'Description': ['The finish of the product', 'The length of the item in inches', 'The type of product'],
                    'Type': ['string', 'string', 'string'],
                    'Default': ['None', 'None', 'None'],
                    'Examples': [['Chrome', 'Matte', 'Gloss'], ['12', '24', '36'], ['Furniture', 'Electronics', 'Clothing']],
                    'Enum': [[], [], []],
                    'Notes': ['Notes here', 'and here', 'and also here']
                })
            )

    def test_extract_ai_write_wrong_columns(self):
        """
        Writing data to an extract.ai wrangle with the wrong variant
        """
        with pytest.raises(ValueError, match="The columns Find, Description, Type, Default, Examples, Enum, Notes must be provided for train.extract"):
            wrangles.recipe.run(
                """
                write:
                - train.extract:
                    model_id: d188e7a7-9de8-4565
                """,
                dataframe=pd.DataFrame({
                    'Default': ['None', 'None', 'None'],
                    'Examples': [['Chrome', 'Matte', 'Gloss'], ['12', '24', '36'], ['Furniture', 'Electronics', 'Clothing']],
                    'Enum': [[], [], []],
                    'Notes': ['Notes here', 'and here', 'and also here']
                })
            )

    def test_extract_write_2(self):
        """
        Incorrect columns for extract write
        """
        with pytest.raises(ValueError, match="must be provided for train.extract"):
            wrangles.recipe.run(
                """
                write:
                - train.extract:
                    columns:
                        - Find2
                        - Output (Optional)2
                        - Notes2
                    model_id: ee5f020e-d88e-4bd5
                """,
                dataframe=pd.DataFrame({
                    'Find2': ['Rachel', 'Dolores', 'TARS'],
                    'Output (Optional)2': ['', '', ''],
                    'Notes2': ['Blade Runner', 'Westworld', 'Interstellar'],
                })
            )

    def test_extract_error(self):
        """
        Not Providing model_id or name in train wrangles
        """
        with pytest.raises(ValueError, match="name or a model id must be provided"):
            wrangles.recipe.run(
                """
                write:
                - train.extract:
                    columns:
                        - Find
                        - Output (Optional)
                        - Notes
                """,
                dataframe=pd.DataFrame({
                    'Find': ['Rachel', 'Dolores', 'TARS'],
                    'Output (Optional)': ['', '', ''],
                    'Notes': ['Blade Runner', 'Westworld', 'Interstellar'],
                })
            )


class TestTrainLookup:
    """
    All tests for train.lookup
    """

    def test_lookup_read(self):
        """
        Read lookup wrangle data
        """
        recipe = """
        read:
          - train.lookup:
              model_id: 3c8f6707-2de4-4be3
        """
        df = wrangles.recipe.run(recipe)
        assert len(df) == 3 and df.columns.to_list() == ['Key', 'Value']

    def test_lookup_write(self):
        """
        Writing data to a Lookup Wrangle (re-training)
        """
        recipe = """
        write:
          - train.lookup:
              model_id: 3c8f6707-2de4-4be3
        """
        data = pd.DataFrame({
            'Key': ['Rachel', 'Dolores', 'TARS'],
            'Value': ['Blade Runner', 'Westworld', 'Interstellar'],
        })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Key'] == 'Rachel' and df.iloc[0]['Value'] == 'Blade Runner'

    def test_key_lookup_write_duplicates(self):
        """
        Test the error when attempting to train a lookup with duplicate keys
        """
        with pytest.raises(ValueError, match="Lookup: All Keys must be unique"):
            wrangles.recipe.run(
                """
                write:
                  - train.lookup:
                      name: This is Temporary
                      variant: key
                """,
                dataframe=pd.DataFrame({
                  'Key': ['Rachel', 'Rachel', 'Dolores', 'TARS'],
                  'Value': ['Blade Runner', 'Not Rachel', 'Westworld', 'Interstellar'],
                })
            )

    def test_semantic_lookup_write_duplicates(self):
        """
        Test that semantic lookups are allowed to have duplicate keys
        """
        recipe = """
        write:
          - train.lookup:
              model_id: e8658a6f-c694-45d0
        """
        data = pd.DataFrame({
            'Key': ['Rachel', 'Rachel', 'Dolores', 'TARS'],
            'Value': ['Blade Runner', 'Not Rachel', 'Westworld', 'Interstellar'],
        })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Key'] == 'Rachel' and df.iloc[0]['Value'] == 'Blade Runner'

    def test_lookup_write_columns(self):
        """
        Writing data to a Lookup Wrangle (re-training)
        """
        recipe = """
        write:
          - train.lookup:
              model_id: 3c8f6707-2de4-4be3
              columns:
                - Key
                - Value
        """
        data = pd.DataFrame({
            'Key': ['Rachel', 'Dolores', 'TARS'],
            'Value': ['Blade Runner', 'Westworld', 'Interstellar'],
        })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Key'] == 'Rachel' and df.iloc[0]['Value'] == 'Blade Runner'

    def test_lookup_write_no_key(self):
        """
        Writing data to a Lookup Wrangle (re-training) without Key
        """
        with pytest.raises(ValueError, match="Data must contain one column named Key"):
            wrangles.recipe.run(
                """
                write:
                  - train.lookup:
                      model_id: 3c8f6707-2de4-4be3
                      columns:
                        - Value
                """,
                dataframe=pd.DataFrame({
                  'Key': ['Rachel', 'Dolores', 'TARS'],
                  'Value': ['Blade Runner', 'Westworld', 'Interstellar'],
                })
            )

    def test_lookup_write_model_id_and_name(self):
        """
        Writing data to a Lookup Wrangle (re-training) with both a model_id and name
        """
        with pytest.raises(ValueError, match="Name and model_id cannot both be provided"):
            wrangles.recipe.run(
                """
                write:
                  - train.lookup:
                      model_id: 3c8f6707-2de4-4be3
                      name: My Lookup Wrangle
                      columns:
                        - Key
                        - Value
                """,
                dataframe=pd.DataFrame({
                  'Key': ['Rachel', 'Dolores', 'TARS'],
                  'Value': ['Blade Runner', 'Westworld', 'Interstellar'],
                })
            )

    def test_lookup_write_no_model_id_or_name(self):
        """
        Writing data to a Lookup Wrangle (re-training) without Key
        """
        with pytest.raises(ValueError, match="Either a name or a model id must be provided"):
            wrangles.recipe.run(
                """
                write:
                  - train.lookup:
                      columns:
                        - Key
                        - Value
                """,
                dataframe=pd.DataFrame({
                  'Key': ['Rachel', 'Dolores', 'TARS'],
                  'Value': ['Blade Runner', 'Westworld', 'Interstellar'],
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


