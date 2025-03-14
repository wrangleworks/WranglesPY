import wrangles
import pandas as pd
import pytest
import numpy as np
import uuid
import random
from datetime import datetime


class TestCreateColumn:
    """
    Test create.column
    """
    def test_create_column_1(self):
        data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
        recipe = """
        wrangles:
            - create.column:
                output: column3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df.columns) == 3

    def test_create_column_where(self):
        """
        Test create.column using where
        """
        data = pd.DataFrame({
            'col1': ['stuff', 'stuff', 'more stuff'],
            'numbers': [4, 7, 8]
        })
        recipe = """
        wrangles:
            - create.column:
                output: output
                value: this is stuff
                where: numbers > 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == '' and df.iloc[1]['output'] == 'this is stuff'
        
    # Adding a value from test connector
    def test_create_columns_2(self):
        data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
        recipe = """
        wrangles:
            - create.column:
                output: column3
                value: <boolean>
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column3'] in [True, False]
        
    # Adding multiple columns with the same generated value
    def test_create_columns_3(self):
        data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
        recipe = """
        wrangles:
            - create.column:
                output:
                - column3
                - column4
                value: <boolean>
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column4'] in [True, False]
        
    # Adding multiple columns with multiple generated values
    def test_create_columns_4(self):
        data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
        recipe = """
        wrangles:
            - create.column:
                output:
                - column3
                - column4
                value: <number(1-3)>
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column4'] in [1, 2, 3, 4]
        
    # if the output is a list with length one
    def test_create_columns_5(self):
        data = pd.DataFrame([['data1', 'data2']], columns=['column1', 'column2'])
        recipe = """
        wrangles:
            - create.column:
                output:
                - column3
                value: <boolean>
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column3'] in [True, False]
        
    def test_column_exists(self):
        """
        Check error if trying to create a column that already exists
        """
        data = pd.DataFrame({
        'col': ['data1']
        })
        recipe = """
        wrangles:
        - create.column:
            output: col
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            '"col" column already exists in dataFrame.' in info.value.args[0]
        )

    def test_column_exists_list(self):
        """
        Check error if trying to create a list of columns where one already exists
        """
        data = pd.DataFrame({
        'col': ['data1']
        })
        recipe = """
        wrangles:
        - create.column:
            output:
                - col
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "['col'] column(s)" in info.value.args[0]
        )

    def test_create_column_value_number(self):
        """
        Test create.column using a number as the value
        """
        data = pd.DataFrame({
            'col1': ['stuff', 'stuff', 'more stuff'],
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2
                value: ${value}
            """,
            variables={
                "value": 1
            },
            dataframe=data
        )
        assert df['col2'][0] == 1
        
    def test_create_column_value_boolean(self):
        """
        Test create.column using a boolean as the value
        """
        data = pd.DataFrame({
            'col1': ['stuff', 'stuff', 'more stuff'],
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2
                value: ${value}
            """,
            variables={
                "value": True
            },
            dataframe=data
        )
        assert df['col2'][0] == True
        
    def test_create_column_succinct_1(self):
        """
        Create columns using a more succinct format. Dicts for output (col_name: value)
        Value is not None
        """
        data = pd.DataFrame({
            'col1': ['Hello']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2: World
                    - col3: <boolean>
                    - col4: <code(10)>
                    - col5
                value: THIS IS A TEST
            """,
            dataframe=data
        )
        assert len(df["col4"][0]) == 10
        
    def test_create_column_succinct_2(self):
        """
        Create columns using a more succinct format. Dicts for output (col_name: value)
        Value is None
        """
        data = pd.DataFrame({
            'col1': ['Hello']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2
                    - col3: <boolean>
                    - col4: <code(10)>
                    - col5: ""
            """,
            dataframe=data
        )
        assert df["col3"][0] == True or df["col3"][0] == False
        
    def test_create_column_succinct_3(self):
        """
        Cannot mix dictionaries and strings in the output list with no value provided.
        col2 and col5 are strings, the rest are dicts
        """
        data = pd.DataFrame({
            'col1': ['Hello']
        })
        recipe="""
            wrangles:
            - create.column:
                output:
                    - col2 
                    - col3: <boolean>
                    - col4: <code(10)>
                    - col5
            """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['col2'][0] == '' and df['col5'][0] == ''

    def test_create_column_succinct_5(self):
        """
        Testing the column that is not a dict and has no value
        """
        data = pd.DataFrame({
            'col1': ['Hello']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2: World
                    - col3: <boolean>
                    - col4: <code(10)>
                    - col5
                value: THIS IS A TEST
            """,
            dataframe=data
        )
        assert df['col5'][0] == 'THIS IS A TEST'
        
    def test_create_column_succinct_6(self):
        """
        Having a duplicate column in the creation process
        """
        data = pd.DataFrame({
            'col1': ['Hello']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2: World
                    - col2: World2
            """,
            dataframe=data
        )
        assert df['col2'][0] == 'World2'
        
    def test_create_column_succinct_7(self):
        """
        Having a duplicate column in the creation process
        """
        data = pd.DataFrame({
            'col1': ['Hello']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2: World
                    - col2.5: Nothing here
                    - col2: World2
            """,
            dataframe=data
        )
        assert df['col2'][0] == 'World2'
        
    def test_create_column_succinct_8(self):
        """
        Having a dictionary in the output with more than one key:value pair. Should only get the first value
        """
        data = pd.DataFrame({
            'col1': ['Hello']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output:
                    - col2: World
                      col2.5: Nothing here
                    - col3: <boolean>
            """,
            dataframe=data
        )
        assert list(df.columns) == ['col1', 'col2', 'col3']

    def test_create_column_list_value(self):
        """
        Test creating a column with a list as the value
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
            wrangles:
            - create.column:
                output: column
                value:
                    - a
                    - b
                    - c
            """
        )
        assert (
            isinstance(df["column"][0], list) and
            len(df["column"][0]) == 3
        )

    def test_create_empty_column(self):
        """
        Test creating an empty column
        """
        data = pd.DataFrame({
            'col1': []
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - create.column:
                output: col2
            """,
            dataframe=data
        )
        assert df.empty and list(df.columns) == ['col1', 'col2']


class TestCreateIndex:
    """
    Test create.index
    """
    def test_create_index(self):
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 3
                values:
                    header: value
            wrangles:
            - create.index:
                output: index_col
            """
        )
        assert df["index_col"].values.tolist() == [1,2,3]

    def test_create_index_start(self):
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 3
                values:
                    header: value
            wrangles:
            - create.index:
                output: index_col
                start: 0
            """
        )
        assert df["index_col"].values.tolist() == [0,1,2]

    def test_create_index_step(self):
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 3
                values:
                    header: value
            wrangles:
            - create.index:
                output: index_col
                step: 2
            """
        )
        assert df["index_col"].values.tolist() == [1,3,5]

    def test_create_index_where(self):
        """
        Test create.index using where
        """
        data = pd.DataFrame({
            'col1': ['Stuff', 'More stuff', 'Even more stuff than before'],
            'numbers': [3, 8, 12]
        })
        recipe = """
            wrangles:
                - create.index:
                    output: index_col
                    where: numbers > 3
            """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['index_col'] == '' and df.iloc[2]['index_col'] == 2

    def test_create_index_by_columns(self):
        """
        Test an index clustered by multiple columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.index:
                output: grouped_index
                by:
                    - column1
                    - column2
            """,
            dataframe=pd.DataFrame({
                "column1": ["a","a","b","b","a","b"],
                "column2": ["a","a","b","c","a","b"],
            })
        )
        assert df["grouped_index"].values.tolist() == [1,2,1,1,3,2]

    def test_create_index_by_column(self):
        """
        Test an index clustered by a column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.index:
                output: grouped_index
                by: column
            """,
            dataframe=pd.DataFrame({
                "column": ["a","a","b","b","a"]
            })
        )
        assert df["grouped_index"].values.tolist() == [1,2,1,2,3]

    def test_create_index_by_column_start_step(self):
        """
        Test an index clustered by a column
        with start and step
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.index:
                output: grouped_index
                by: column
                start: 0
                step: 2
            """,
            dataframe=pd.DataFrame({
                "column": ["a","a","b","b","a"]
            })
        )
        assert df["grouped_index"].values.tolist() == [0,2,0,2,4]

    def test_create_index_column_empty_dataframe(self):
        """
        Test create.index with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.index:
                output: index_col
            """,
            dataframe=pd.DataFrame({'Col1': []})
        )
        assert df.empty and list(df.columns) == ['Col1', 'index_col']


class TestCreateGUID:
    """
    Test create.guid
    """
    def test_guid_1(self):
        data = pd.DataFrame({
        'Product': ['A', 'B'],
        })
        recipe = """
        wrangles:
            - create.guid:
                output: GUID Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert 'GUID Col' in list(df.columns)

    def test_guid_where(self):
        data = pd.DataFrame({
        'Product': ['A', 'B', 'C'],
        'numbers': [4, 8, 10]
        })
        recipe = """
        wrangles:
            - create.guid:
                output: GUID Col
                where: numbers < 9
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert (
            df.iloc[2]['GUID Col'] == '' and
            isinstance(df.iloc[0]['GUID Col'], uuid.UUID)
        )

    def test_guid_empty(self):
        data = pd.DataFrame({
        'Product': [],
        })
        recipe = """
        wrangles:
            - create.guid:
                output: GUID Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and list(df.columns) == ['Product', 'GUID Col']


class TestCreateJinja:
    """
    Test create.jinja
    """
    def test_jinja_from_columns(self):
        """
        Tests functionality with template given as a string
        """
        data = pd.DataFrame({
            "type": ['phillips head', 'flat head'],
            'length': ['3 inch', '6 inch']
        })
        recipe = """
        wrangles:
        - create.jinja:
            output: description
            template: 
                string: This is a {{length}} {{type}} screwdriver
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'


    def test_jinja_string_template(self):
        """
        Tests functionality with template given as a string
        """
        data = pd.DataFrame({
            'data column': [
                {'type': 'phillips head', 'length': '3 inch'},
                {'type': 'flat head', 'length': '6 inch'}
            ]
        })
        recipe = """
        wrangles:
        - create.jinja:
            input: data column
            output: description
            template: 
                string: "This is a {{length}} {{type}} screwdriver"
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

    def test_jinja_column_template(self):
        """
        Tests functionality with templates in dataframe column
        """
        data = pd.DataFrame({
            'data column': [
                {'type': 'phillips head', 'length': '3 inch'},
                {'type': 'flat head', 'length': '6 inch'}
            ],
            'template column': [
                'This is a {{length}} {{type}} screwdriver',
                'This is a {{length}} {{type}} screwdriver'
            ]
        })
        recipe = """
        wrangles:
        - create.jinja:
            input: data column
            output: description
            template: 
                column: template column
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

    def test_jinja_file_template(self):
        """
        Tests functionality with a template in a file
        """
        data = pd.DataFrame({
            'data column': [
                {'type': 'phillips head', 'length': '3 inch'},
                {'type': 'flat head', 'length': '6 inch'}
            ]
        })
        recipe = """
        wrangles:
        - create.jinja:
            input: data column
            output: description
            template: 
                file: tests/samples/jinjadescriptiontemplate.jinja
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

    def test_jinja_multiple_templates(self):
        """
        Tests that the appropriate error message is shown when multiple templates are given
        """
        data = pd.DataFrame({
            'data column': [
                {'type': 'phillips head', 'length': '3 inch'},
                {'type': 'flat head', 'length': '6 inch'}
            ],
            'template column': [
                'This is a {{length}} {{type}} screwdriver',
                'This is a {{length}} {{type}} screwdriver'
            ]
        })
        recipe = """
        wrangles:
        - create.jinja:
            input: data column
            output: description
            template: 
                string: This is a {{length}} {{type}} screwdriver
                column: template column
        """
        with pytest.raises(Exception) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'Exception' and
            'Template must have only one key specified' in info.value.args[0]
        )

    def test_jinja_no_template(self):
        """
        Tests that the appropriate error message is shown when no template is given
        """
        with pytest.raises(ValueError, match="requires arguments") as info:
            raise wrangles.recipe.run(
                """
                wrangles:
                - create.jinja:
                    input: data column
                    output: description
                """,
                dataframe=pd.DataFrame({
                    'data column': [
                        {'type': 'phillips head', 'length': '3 inch'},
                        {'type': 'flat head', 'length': '6 inch'}
                    ]
                })
            )

    def test_jinja_unsupported_template_key(self):
        """
        Test that the appropriate error message is shown when template
        is passed a key other than 'file', 'string', 'column'
        """
        data = pd.DataFrame({
            'data column': [{'type': 'phillips head', 'length': '3 inch'}, {'type': 'flat head', 'length': '6 inch'}]
        })
        recipe = """
        wrangles:
        - create.jinja:
            input: data column
            output: description
            template:
                wrong: test
        """
        with pytest.raises(Exception) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'Exception' and
            "'file', 'column' or 'string' not found" in info.value.args[0]
        )

    def test_jinja_output_list(self):
        """
        Tests specifying the output as a list
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.jinja:
                input: data column
                output:
                    - description
                template: 
                    string: "This is a {{length}} {{type}} screwdriver"
            """,
            dataframe = pd.DataFrame({
                'data column': [
                    {'type': 'phillips head', 'length': '3 inch'},
                    {'type': 'flat head', 'length': '6 inch'}
                ]
            })
        )
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

    def test_jinja_output_missing(self):
        """
        Check error if user doesn't specify output
        """
        with pytest.raises(ValueError, match="requires arguments"):
            wrangles.recipe.run(
                """
                wrangles:
                - create.jinja:
                    input: data column
                    template: 
                        string: "This is a {{length}} {{type}} screwdriver"
                """,
                dataframe = pd.DataFrame({
                    'data column': [
                        {'type': 'phillips head', 'length': '3 inch'},
                        {'type': 'flat head', 'length': '6 inch'}
                    ]
                })
            )

    def test_jinja_variable_with_space(self):
        """
        Tests variable with a space
        """
        data = pd.DataFrame({
            'head type': ['phillips head', 'flat head'],
            'length': ['3 inch', '6 inch']
        })
        recipe = """
        wrangles:
        - create.jinja:
            output: description
            template: 
                string: This is a {{length}} {{head_type}} screwdriver
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

    def test_jinja_where(self):
        """
        Tests create.jinja using where
        """
        data = pd.DataFrame({
            'data column': [
                {'type': 'phillips head', 'length': '3 inch'},
                {'type': 'flat head', 'length': '6 inch'},
                {'type': 'combination', 'length': '4 inch'}
            ],
            'numbers': [43, 12, 76]
        })
        recipe = """
        wrangles:
        - create.jinja:
            input: data column
            output: description
            template: 
                string: "This is a {{length}} {{type}} screwdriver"
            where: numbers < 50
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver' and df.iloc[2]['description'] == ''

    def test_jinja_breaking_chars(self):
        """
        Tests functionality with breaking characters included in column name
        """
        data = pd.DataFrame({
            r"t .-!@#$%^&*()+=[]|\:;'<>,?/`~est": ['phillips head', 'flat head'],
            '"': ['3 inch', '6 inch']
        })
        recipe = """
        wrangles:
        - create.jinja:
            output: description
            template: 
                string: This is a {{_}} {{t_____________________________est}} screwdriver
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['description'][0] == 'This is a 3 inch phillips head screwdriver'

    def test_create_jinja_empty(self):
        """
        Test create.jinja with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.jinja:
                output: description
                template: 
                    string: This is a {{length}} {{type}} screwdriver
            """,
            dataframe=pd.DataFrame({'data column': []})
        )
        assert df.empty and list(df.columns) == ['data column', 'description']


class TestCreateUUID:
    """
    Test create.uuid
    """
    def test_uuid_1(self):
        data = pd.DataFrame({
        'Product': ['A', 'B'],
        })
        recipe = """
        wrangles:
            - create.uuid:
                output: UUID Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert 'UUID Col' in list(df.columns)
        
    def test_uuid_where(self):
        data = pd.DataFrame({
        'Product': ['A', 'B', 'C'],
        'numbers': [32, 65, 22]
        })
        recipe = """
        wrangles:
            - create.uuid:
                output: UUID Col
                where: numbers = 65
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert (
            df.iloc[2]['UUID Col'] == '' and
            isinstance(df.iloc[1]['UUID Col'], uuid.UUID)
        )

    def test_uuid_empty(self):
        data = pd.DataFrame({
        'Product': [],
        })
        recipe = """
        wrangles:
            - create.uuid:
                output: UUID Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and list(df.columns) == ['Product', 'UUID Col']


class TestCreateBins:
    """
    Test create.bins
    """
    def test_create_bins_1(self):
        data = pd.DataFrame({
            'col': [3, 13, 113]
        })
        recipe = """
        wrangles:
        - create.bins:
                input: col
                output: Pricing
                bins:
                    - '-'
                    - 10
                    - 20
                    - 50
                    - 70
                    - '+'
                labels:
                    - 'under 10'
                    - '10-20'
                    - '20-40'
                    - '40-70'
                    - '100 and above'
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Pricing'].iloc[0] == 'under 10'

    def test_create_bins_list_to_list(self):
        """
        Test create.bins using a list of input and output columns
        """
        data = pd.DataFrame({
            'col1': [3, 13, 113],
            'col2': [4, 14, 114]
        })
        recipe = """
        wrangles:
        - create.bins:
                input:
                - col1
                - col2
                output:
                - Pricing1
                - Pricing2
                bins:
                - '-'
                - 10
                - 20
                - 50
                - 70
                - '+'
                labels:
                - 'under 10'
                - '10-20'
                - '20-40'
                - '40-70'
                - '100 and above'
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Pricing1'].iloc[0] == 'under 10' and df['Pricing2'].iloc[0] == 'under 10'

    def test_create_bins_list_to_single_output(self):
        """
        Test create.bins using a list of inputs and a single output column
        """
        data = pd.DataFrame({
            'col1': [3, 13, 113],
            'col2': [4, 14, 114]
        })
        recipe = """
        wrangles:
        - create.bins:
                input:
                - col1
                - col2
                output: Pricing1
                bins:
                - '-'
                - 10
                - 20
                - 50
                - 70
                - '+'
                labels:
                - 'under 10'
                - '10-20'
                - '20-40'
                - '40-70'
                - '100 and above'
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_create_bins_single_input_multi_output(self):
        """
        Test create.bins using a single input and a list of output columns
        """
        data = pd.DataFrame({
            'col1': [3, 13, 113],
            'col2': [4, 14, 114]
        })
        recipe = """
        wrangles:
        - create.bins:
                input: col1
                output: 
                - Pricing1
                - Pricing2
                bins:
                - '-'
                - 10
                - 20
                - 50
                - 70
                - '+'
                labels:
                - 'under 10'
                - '10-20'
                - '20-40'
                - '40-70'
                - '100 and above'
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_create_bins_where(self):
        """
        Test create bins using where
        """
        data = pd.DataFrame({
            'col': [3, 13, 113]
        })
        recipe = """
        wrangles:
        - create.bins:
                input: col
                output: Pricing
                bins:
                    - '-'
                    - 10
                    - 20
                    - 50
                    - 70
                    - '+'
                labels:
                    - 'under 10'
                    - '10-20'
                    - '20-40'
                    - '40-70'
                    - '100 and above'
                where: col > 10
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Pricing'] == '10-20' and df.iloc[0]['Pricing'] == ''

    def test_create_bins_empty(self):
        """
        Test create.bins with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.bins:
                input: col
                output: Pricing
                bins:
                    - '-'
                    - 10
                    - 20
                    - 50
                    - 70
                    - '+'
                labels:
                    - 'under 10'
                    - '10-20'
                    - '20-40'
                    - '40-70'
                    - '100 and above'
            """,
            dataframe=pd.DataFrame({'col': []})
        )
        assert df.empty and list(df.columns) == ['col', 'Pricing']


class TestCreateEmbeddings:
    """
    Test create.embeddings
    """
    def test_create_embeddings(self):
        """
        Test generating openai embeddings
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    text: "This is a test"
            wrangles:
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                retries: 1
            """
        )
        assert (
            isinstance(df["embedding"][0], list) and
            len(df["embedding"][0]) == 1536
        )

    def test_create_embeddings_batching(self):
        """
        Test generating openai embeddings
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 150
                values:
                    text: "This is a test"
            wrangles:
            - create.index:
                output: index_col
            - python:
                command: text + " " + str(index_col)
                output: text
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                batch_size: 20
                retries: 1
            """
        )
        assert (
            isinstance(df["embedding"][0], list) and
            len(df["embedding"][0]) == 1536 and
            len(df) == 150
        )

    def test_create_embeddings_empty(self):
        """
        Test generating openai embeddings with an empty string
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    text: ""
            wrangles:
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                retries: 1
            """
        )
        assert (
            isinstance(df["embedding"][0], list) and
            len(df["embedding"][0]) == 1536
        )

    def test_create_embeddings_python_list(self):
        """
        Test generating openai embeddings as a python list
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    text: "This is a test"
            wrangles:
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                output_type: python list
                retries: 1
            """
        )
        assert (
            isinstance(df["embedding"][0], list) and
            len(df["embedding"][0]) == 1536
        )

    def test_create_embeddings_np_array(self):
        """
        Test generating openai embeddings as a numpy array
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    text: "This is a test"
            wrangles:
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                output_type: numpy array
                retries: 1
            """
        )
        assert (
            isinstance(df["embedding"][0], (np.ndarray, np.float32)) and
            len(df["embedding"][0]) == 1536
        )

    def test_create_embeddings_invalid_output_type(self):
        """
        Test create.embeddings gives a clear error
        if an invalid output type is given
        """
        with pytest.raises(ValueError, match="must be of value"):
            raise wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1
                    values:
                        text: "This is a test"
                wrangles:
                - create.embeddings:
                    input: text
                    output: embedding
                    api_key: ${OPENAI_API_KEY}
                    output_type: Something here is not right
                """
            )

    def test_create_embeddings_multi_column(self):
        """
        Test generating openai embeddings
        with multiple inputs/outputs
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    text1: "This is a test"
                    text2: "Something else"
            wrangles:
            - create.embeddings:
                input:
                    - text1
                    - text2
                output:
                    - embedding1
                    - embedding2
                api_key: ${OPENAI_API_KEY}
                retries: 1
            """
        )
        assert (
            isinstance(df["embedding1"][0], list) and
            len(df["embedding1"][0]) == 1536 and
            isinstance(df["embedding2"][0], list) and
            len(df["embedding2"][0]) == 1536
        )

    def test_create_embeddings_np_array_with_where(self):
        """
        Test using where with a numpy array
        created by create.embeddings
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                output_type: numpy array
                retries: 1

            - convert.case:
                input: text
                where: "text LIKE '%not%'"
                case: upper
            """,
            dataframe=pd.DataFrame({
                "text": ["This is a test", "This is not a test"]
            })
        )
        assert (
            isinstance(df["embedding"][0], (np.ndarray, np.float32)) and
            len(df["embedding"][0]) == 1536 and
            df["text"].values.tolist() == ['This is a test', 'THIS IS NOT A TEST']
        )

    def test_create_embeddings_kwargs(self):
        """
        Test passing through any unspecified
        params works correctly
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    text: "This is a test"
            wrangles:
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                retries: 1
                model: text-embedding-3-small
                dimensions: 256
            """
        )
        assert (
            isinstance(df["embedding"][0], list) and
            len(df["embedding"][0]) == 256
        )

    def test_create_embeddings_missing_apikey(self):
        """
        Test create.embeddings gives a clear
        error message when missing an api key
        """
        with pytest.raises(ValueError, match="requires arguments"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1
                    values:
                        text: "This is a test"
                wrangles:
                - create.embeddings:
                    input: text
                    output: embedding
                    retries: 1
                """
            )

    def test_create_embeddings_invalid_apikey(self):
        """
        Test create.embeddings gives a clear
        error message when an invalid api key is given
        """
        with pytest.raises(ValueError, match="API Key"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1
                    values:
                        text: "This is a test"
                wrangles:
                - create.embeddings:
                    input: text
                    output: embedding
                    api_key: INVALID_API_KEY
                    retries: 1
                """
            )

    def test_create_embeddings_where(self):
        """
        Test generating openai embeddings with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.embeddings:
                input: column
                output: embedding
                api_key: ${OPENAI_API_KEY}
                retries: 1
                where: numbers > 7
            """,
            dataframe=pd.DataFrame({
                    "column": [
                            'This is a test',
                            'This is also a test',
                            'Yet another test'
                        ],
                    "numbers": [5, 7, 8]
                })
        )
        assert df['embedding'][0] == '' and len(df['embedding'][2]) == 1536

    def test_float16_precision(self):
        """
        Test generating half precision embeddings
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header: value
            wrangles:
            - create.embeddings:
                input: header
                output: embeddings_16
                api_key: ${OPENAI_API_KEY}
                retries: 1
                output_type: numpy array
                precision: float16
                dimensions: 256
            - create.embeddings:
                input: header
                output: embeddings_32
                api_key: ${OPENAI_API_KEY}
                retries: 1
                output_type: numpy array
                dimensions: 256
            """
        )
        assert (
            df['embeddings_16'][0].dtype == np.float16 and
            df['embeddings_32'][0].dtype == np.float32 and
            round(float(df['embeddings_32'][0][0]), 3) == round(float(df['embeddings_16'][0][0]), 3)
        )

    def test_create_embeddings_empty_dataframe(self):
        """
        Test create.embeddings with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.embeddings:
                input: text
                output: embedding
                api_key: ${OPENAI_API_KEY}
                retries: 1
            """,
            dataframe=pd.DataFrame({'text': []})
        )
        assert df.empty and list(df.columns) == ['text', 'embedding']

class TestCreateHash:
    def test_create_md5_hash(self):
        """
        Test create.hash with md5
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.hash:
                input: text
                output: hash
                method: md5
            """,
            dataframe=pd.DataFrame({
                "text": ["This is a test"]
            })
        )

        assert df["hash"][0] == "ce114e4501d2f4e2dcea3e17b546f339"

    def test_create_sha1_hash(self):
        """
        Test create.hash with sha1
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.hash:
                input: text
                output: hash
                method: sha1
            """,
            dataframe=pd.DataFrame({
                "text": ["This is a test"]
            })
        )

        assert df["hash"][0] == "a54d88e06612d820bc3be72877c74f257b561b19"

    def test_create_sha256_hash(self):
        """
        Test create.hash with sha256
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.hash:
                input: text
                output: hash
                method: sha256
            """,
            dataframe=pd.DataFrame({
                "text": ["Hello, World!"]
            })
        )

        assert df["hash"][0] == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"

    def test_create_sha512_hash(self):
        """
        Test create.hash with sha512
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.hash:
                input: text
                output: hash
                method: sha512
            """,
            dataframe=pd.DataFrame({
                "text": ["Hello, World!"]
            })
        )

        assert df["hash"][0] == "374d794a95cdcfd8b35993185fef9ba368f160d8daf432d08ba9f1ed1e5abe6cc69291e0fa2fe0006a52570ef18c19def4e617c33ce52ef0a6e5fbe318cb0387"

    def test_create_mixed_input_hash(self):
        """
        Test create.hash with multiple inputs
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.hash:
                input: text
                output: hash
                method: sha256
            """,
            dataframe=pd.DataFrame({
                "text": ["This is a test", 256, 3.14]
            })
        )
        assert df["hash"].to_list() == ["c7be1ed902fb8dd4d48997c6452f5d7e509fbcdbe2808b16bcf4edce4c07d14e", 
                                        "51e8ea280b44e16934d4d611901f3d3afc41789840acdff81942c2f65009cd52", 
                                        "2efff1261c25d94dd6698ea1047f5c0a7107ca98b0a6c2427ee6614143500215"]
        
    def test_create_mixed_hash(self):
        """
        Test create.hash with multiple methods
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.hash:
                input: text
                output: hash
                method: sha256
            - create.hash:
                input: text
                output: hash2
                method: md5
            """,
            dataframe=pd.DataFrame({
                "text": ["This is a test"]
            })
        )

        assert df["hash"][0] == "c7be1ed902fb8dd4d48997c6452f5d7e509fbcdbe2808b16bcf4edce4c07d14e"
        assert df["hash2"][0] == "ce114e4501d2f4e2dcea3e17b546f339"

    def test_create_hash_empty(self):
        """
        Test create.hash with an empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - create.hash:
                input: text
                output: hash
                method: sha256
            """,
            dataframe=pd.DataFrame({'text': []})
        )
        assert df.empty and list(df.columns) == ['text', 'hash']