import wrangles
import pandas as pd
import pytest
import json as _json
import numpy as _np


class TestConvertCase:
    """
    Test convert.case wrangles
    """
    def test_default(self):
        """
        Default value -> no case specified
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'a string'

    def test_list(self):
        """
        Input is a list
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input:
                - Data1
                - Data2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'a string' and df.iloc[0]['Data2'] == 'another string'

    def test_output(self):
        """
        Specifying output column
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            output: Column
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Column'] == 'a string'

    def test_list_to_list(self):
        """
        Output and input are a multi columns
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
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
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Column1'] == 'a string' and df.iloc[0]['Column2'] == 'another string'

    def test_multi_input_single_output(self):
        """
        Input is a list of columns and output is a single column
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input:
                - Data1
                - Data2
            output: Column1
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_single_input_multi_output(self):
        """
        Input is a list of columns and output is a single column
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            output:
                - Column1
                - Column2
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_lower(self):
        """
        Test converting to lower case
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            case: lower
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'a string'

    def test_upper(self):
        """
        Test converting to upper case
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            case: upper
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'A STRING'
        
    def test_title(self):
        """
        Test converting to title case
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            case: title
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'A String'

    def test_sentence(self):
        """
        Test converting to sentence case
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'A string'

    def test_where(self):
        """
        Test converting to title case using where
        """
        data = pd.DataFrame({
        'Col1': ['ball bearing', 'roller bearing', 'needle bearing'],
        'number': [25, 31, 22]
        })
        recipe = """
        wrangles:
        - convert.case:
            input: Col1
            case: title
            where: number > 22
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Col1'] == 'Ball Bearing' and df.iloc[2]['Col1'] == "needle bearing"

    def test_where_empty(self):
        """
        Test converting to title case using where
        """
        data = pd.DataFrame({
        'Col1': ['ball bearing', 'roller bearing', 'needle bearing'],
        'number': [25, 31, 22]
        })
        recipe = """
        wrangles:
        - convert.case:
            input: Col1
            case: title
            where: number > 35
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Col1'] == 'ball bearing' and df.iloc[2]['Col1'] == "needle bearing" 

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: column
                output: upper column
                case: upper
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'upper column']


class TestConvertDataType:
    """
    Test convert.data_type wrangles
    """
    def test_str(self):
        """
        Test converting to string data type
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: Data1
            data_type: str
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['Data1'], str)

    def test_list_to_list(self):
        """
        Test using a list of outputs and a list of inputs
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: 
              - Data1
              - Data2
            output:
              - out1
              - out2
            data_type: str
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['out1'], str) and isinstance(df.iloc[0]['out2'], str) 

    def test_error_multi_input_single_output(self):
        """
        Test error when list of inputs given with a single output
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: 
              - Data1
              - Data2
            output: out1
            data_type: str
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_error_single_input_multi_output(self):
        """
        Test error when single input given with list of outputs
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: Data1
            output: 
              - out1
              - out2
            data_type: str
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_where(self):
        """
        Test convert.data_type using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: number
                data_type: str
                where: number > 25
            """,
            dataframe=pd.DataFrame({
                'number': [25, 31, 22]
            })
        )
        assert df['number'].values.tolist() == [25, '31', 22]

    def test_convert_to_datetime(self):
        data = pd.DataFrame({
            'date': ['12/25/2050'],
        })
        recipe = """
        wrangles:
        - convert.data_type:
            input: date
            output: date_type
            data_type: datetime
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['date_type'].week == 51
        
    def test_convert_to_datetime_where(self):
        """
        Test using convert to datetime using where
        """
        data = pd.DataFrame({
            'date': ['12/25/2050', '11/10/1987'],
            'numbers': [4, 2]
        })
        recipe = """
        wrangles:
        - convert.data_type:
            input: date
            output: date_type
            data_type: datetime
            where: numbers > 3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['date_type'] == '0' and df.iloc[0]['date_type'].week == 51

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: column
                output: output column
                data_type: str
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']


class TestConvertFractionToDecimal:
    """
    Test convert.fraction_to_decimal wrangle
    """
    def test_default(self):
        """
        Test basic example
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: col1
            output: out1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high"

    def test_list_to_list(self):
        """
        Test using a list of outputs and inputs
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: 
                - col1
                - col2
            output: 
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high" and df.iloc[0]['out2'] == "The length is 0.75 wide 0.125 high"

    def test_list_to_single_output(self):
        """
        Test using a list of inputs and a single output
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: 
                - col1
                - col2
            output: out1
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_single_input_multi_output(self):
        """
        Test using a single input and a list of outputs
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: col1
            output: 
                - out1
                - out2
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )
        
    def test_different_separators(self):
        """
        Testing different separators for mixed fractions
        """
        data = pd.DataFrame({
            'input': [
                '1-1/3',
                '1-1/2 cups',
                '1 1/2 cups',
                '1 1/3',
                'not range 1-1/4',
                'e.g 1-3/4 - 2-1/2',
                'fraction ranges 1/4 - 1/2'
            ]
        })
        
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - convert.fraction_to_decimal:
                input: input
                output: out
                decimals: 2
            """,
            dataframe=data
        )
        assert df['out'].tolist() == ['1.33', '1.5 cups', '1.5 cups', '1.33', 'not range 1.25', 'e.g 1.75 - 2.5', 'fraction ranges 0.25 - 0.5']

    def test_where(self):
        """
        Test using fraction to decimal using where
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'numbers': [13, 12, 11]
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: col1
            output: out1
            where: numbers > 11
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[2]['out1'] == "" and df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high"

    def test_convert_fraction_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.fraction_to_decimal:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']


class TestConvertFromJSON:
    """
    Test convert.from_json wrangles
    """
    def test_array(self):
        """
        Test converting to a JSON array to a list
        """
        data = pd.DataFrame([['["val1", "val2"]']], columns=['header1'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: header1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['header1'], list)

    def test_array_list_to_list(self):
        """
        Test converting to a JSON array to a list using a list of inputs and outputs
        """
        data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: 
                - header1
                - header2
                output:
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['out1'], list) and isinstance(df.iloc[0]['out2'], list)

    def test_array_list_to_single_output(self):
        """
        Test error with a list of inputs and a single output
        """
        data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: 
                - header1
                - header2
                output: out1
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_array_single_input_to_multi_output(self):
        """
        Test error with a single input and a list of outputs
        """
        data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: header1
                output: 
                - out1
                - out2
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_array_where(self):
        """
        Test converting to a JSON array to a list using where
        """
        data = pd.DataFrame({
            'header1': ['["val1", "val2"]', '["val3", "val4"]'],
            'numbers': [5, 7]
        })
        recipe = """
        wrangles:
            - convert.from_json:
                input: header1
                where: numbers > 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['header1'] == '["val1", "val2"]' and isinstance(df.iloc[1]['header1'], list)

    def test_error(self):
        """
        Test that bad values return an appropriate error
        """
        with pytest.raises(ValueError) as error:
            raise wrangles.recipe.run(
                """
                wrangles:
                - convert.from_json:
                    input: header1
                """,
                dataframe=pd.DataFrame({
                    "header1": ["", '[1,2,3]']
                })
            )
        assert "Unable to load all rows as JSON" in error.value.args[0]

    def test_default_array(self):
        """
        Test that a default applies correctly for error values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                default: []
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '[1,2,3]']
            })
        )
        assert (
            df["header1"][0] == [] and
            df["header1"][1] == [1,2,3]
        )

    def test_default_dict_empty(self):
        """
        Test that a default applies correctly for empty values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                default: {}
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '[1,2,3]']
            })
        )
        assert (
            df["header1"][0] == {} and
            df["header1"][1] == [1,2,3]
        )

    def test_default_dict_error(self):
        """
        Test that a default applies correctly for error values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                default: {}
            """,
            dataframe=pd.DataFrame({
                "header1": ['{"a":"b":"c"}', '[1,2,3]']
            })
        )
        assert (
            df["header1"][0] == {} and
            df["header1"][1] == [1,2,3]
        )

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                output: output column
            """,
            dataframe=pd.DataFrame({
                "header1": []
            })
        )
        assert df.empty and df.columns.to_list() == ['header1', 'output column']


class TestConvertFromYAML:
    """
    Test convert.from_yaml wrangle
    """
    def test_default(self):
        """
        Test converting YAML to an object
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": ["key: val\nkey2:\n- list1\n- list2\n"]
            })
        )
        assert (
            _json.dumps(df['column'][0]) == 
            _json.dumps({"key": "val", "key2": ["list1", "list2"]})
        )

    def test_empty_default_list(self):
        """
        Test converting a YAML to an object
        with a default for empty values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                default: []
            """,
            dataframe=pd.DataFrame({
                "column": ["", "key: val\nkey2:\n- list1\n- list2\n"]
            })
        )
        assert (
            df["column"][0] == [] and
            df["column"][1]["key"] == "val"
        )

    def test_empty_default_dict(self):
        """
        Test converting a YAML to an object
        with a default for empty values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                default: {}
            """,
            dataframe=pd.DataFrame({
                "column": ["", "key: val\nkey2:\n- list1\n- list2\n"]
            })
        )
        assert (
            df["column"][0] == {} and
            df["column"][1]["key"] == "val"
        )

    def test_error_default_dict(self):
        """
        Test converting YAML to an object
        with a default for error values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                default: {}
            """,
            dataframe=pd.DataFrame({
                "column": [
                    " key: val\nkey2:\n- list1\n- list2\n",
                    "key: val\nkey2:\n- list1\n- list2\n"
                ]
            })
        )
        assert (
            df["column"][0] == {} and
            df["column"][1]["key"] == "val"
        )

    def test_where(self):
        """
        Test converting YAML to an object with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                output: output col
                where: numbers > 6
            """,
            dataframe=pd.DataFrame({
                "column": [
                    "key: val\nkey2:\n- list1\n- list2\n",
                    "key3: val\nkey4:\n- list1\n- list2\n",
                    "key5: val\nkey6:\n- list1\n- list2\n",
                    ],
                "numbers": [5, 7, 8]
            })
        )
        assert (
            df['output col'][0]== '' and
            df['output col'][1]["key3"] == "val"
        )

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']


class TestConvertToJSON:
    """
    Test convert.to_json wrangles
    """
    def test_array(self):
        """
        Test converting to a list to a JSON array
        """
        data = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - merge.to_list:
                input:
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == '["val1", "val2"]'

    def test_array_list_to_list(self):
        """
        Test converting to a list to a JSON array with a list of input and output columns
        """
        data = pd.DataFrame([[["val1", "val2"], ["val3", "val4"]]], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.to_json:
                input: 
                - header1
                - header2
                output: 
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1'] == '["val1", "val2"]' and df.iloc[0]['out2'] == '["val3", "val4"]'

    def test_array_single_input_to_multi_output(self):
        """
        Test converting to a list to a JSON array with a single input and a list of output columns
        """
        data = pd.DataFrame([[["val1", "val2"], ["val3", "val4"]]], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.to_json:
                input: header1
                output: 
                - out1
                - out2
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_array_where(self):
        """
        Test converting to a list to a JSON array using where
        """
        data = pd.DataFrame({
            'header1': ['val1', 'val2', 'val3'],
            'header2': ['val4', 'val5', 'val6'],
            'numbers': [2, 7, 4]
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input:
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
                where: numbers > 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == "" and df.iloc[1]['headers_json'] == '["val2", "val5"]'

    def test_array_indent(self):
        """
        Test converting to a list to a JSON array using indent
        """
        data = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - merge.to_list:
                input:
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
                indent: 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == '[\n    "val1",\n    "val2"\n]'

    def test_array_sort_keys(self):
        """
        Test converting to a list to a JSON array using sort_keys
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        wrangles:
            - merge.to_dict:
                input:
                - header3
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
                sort_keys: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == '{"header1": "val1", "header2": "val2", "header3": "val3"}'

    def test_ensure_ascii_true(self):
        """
        Test uncommon characters that require UTF encoding.
        With ascii as True these should show the encoded version.
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        read:
            - test:
                rows: 5
                values: 
                    column: this is a ° symbol
        wrangles:
            - merge.to_dict:
                input:
                - column
                output: column dict

            - convert.to_json:
                input: column dict
                output: column dict
                ensure_ascii: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column dict'] == '{"column": "this is a \\u00b0 symbol"}'

    def test_ensure_ascii_false(self):
        """
        Test uncommon characters that require UTF encoding.
        With ascii as false, these should not be encoded.
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        read:
            - test:
                rows: 5
                values: 
                    column: this is a ° symbol
        wrangles:
            - merge.to_dict:
                input:
                - column
                output: column dict

            - convert.to_json:
                input: column dict
                output: column dict
                ensure_ascii: False
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column dict'] == '{"column": "this is a ° symbol"}'

    def test_ensure_ascii_default(self):
        """
        Test uncommon characters that require UTF encoding.
        With default settings, these should not be encoded.
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        read:
            - test:
                rows: 5
                values: 
                    column: this is a ° symbol
        wrangles:
            - merge.to_dict:
                input:
                - column
                output: column dict

            - convert.to_json:
                input: column dict
                output: column dict
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column dict'] == '{"column": "this is a ° symbol"}'

    def test_numpy_array(self):
        """
        Test converting a numpy array to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [_np.array([1, "a"], dtype=object)]
            })
        )
        assert df['column'][0] == '[1, "a"]'

    def test_datetime(self):
        """
        Test converting a datetime to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [pd.Timestamp('2020-01-01')]
            })
        )
        assert df['column'][0][:22] == '"2020-01-01T00:00:00.0'

    def test_numpy_float(self):
        """
        Test converting a numpy float to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [[_np.float32(1)]]
            }, dtype=object)
        )
        assert df['column'][0] == '[1.0]'

    def test_numpy_int(self):
        """
        Test converting a numpy float to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [[_np.int32(1)]]
            }, dtype=object)
        )
        assert df['column'][0] == '[1]'

    def test_multiple_input_single_output(self):
        """
        Test providing multiple inputs but only one output
        Should merge to a dictionary before converting to JSON
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  column1: a
                  column2:
                    b: 1
            wrangles:
            - convert.to_json:
                input:
                  - column1
                  - column2
                output: result
            """
        )
        assert df['result'][0] == r'{"column1": "a", "column2": {"b": 1}}'

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']


class TestConvertToYAML:
    """
    Test convert.to_yaml wrangle
    """
    def test_default(self):
        """
        Test converting an object to YAML
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [{"key": "val", "key2": ["list1", "list2"]}]
            })
        )
        assert df['column'][0] == "key: val\nkey2:\n- list1\n- list2\n"

    def test_sort_order_default(self):
        """
        Test that an object converted to YAML
        maintains its order using the default settings
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [{"key2": "val", "key1": ["list1", "list2"]}]
            })
        )
        assert df['column'][0] == "key2: val\nkey1:\n- list1\n- list2\n"

    def test_sort_keys_true(self):
        """
        Test specifying sort_keys: true
        for convert.to_yaml
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
                sort_keys: true
            """,
            dataframe=pd.DataFrame({
                "column": [{"key2": "val", "key1": ["list1", "list2"]}]
            })
        )
        assert df['column'][0] == "key1:\n- list1\n- list2\nkey2: val\n"

    def test_multi_input_single_output(self):
        """
        Test providing multiple inputs but only one output
        Should merge to a dictionary before converting to YAML
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  column1: a
                  column2:
                    b: 1
            wrangles:
            - convert.to_yaml:
                input:
                  - column1
                  - column2
                output: result
            """
        )
        assert df['result'][0] == 'column1: a\ncolumn2:\n  b: 1\n'

    def test_unicode_characters(self):
        """
        Test that unicode characters are encoded correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [{"key": "this is a ° symbol"}]
            })
        )
        assert df['column'][0] == 'key: this is a ° symbol\n'

    def test_where(self):
        """
        Test converting an object to YAML with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
                output: output col
                where: numbers > 6
            """,
            dataframe=pd.DataFrame({
                "column": [
                        {"key": "val", "key2": ["list1", "list2"]},
                        {"key3": "val", "key4": ["list1", "list2"]},
                        {"key5": "val", "key6": ["list1", "list2"]},
                ],
                "numbers": [5, 7, 8]
            })
        )
        assert (
            df['output col'][0] == "" and
            df['output col'][1] == "key3: val\nkey4:\n- list1\n- list2\n"
        )

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']