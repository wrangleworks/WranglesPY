import wrangles
import pandas as pd
import pytest


class TestFormatRemoveDuplicates:
    """
    Test format.remove_duplicates wrangle
    """
    def test_remove_duplicates_1(self):
        """
        Input column is a list
        """
        data = pd.DataFrame([[['Agent Smith', 'Agent Smith', 'Agent Smith']]], columns=['Agents'])
        recipe = """
        wrangles:
        - format.remove_duplicates:
            input: Agents
            output: Remove
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Remove'] == ['Agent Smith']

    def test_remove_duplicates_2(self):
        """
        Input column is a str
        """
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

    def test_remove_duplicates_3(self):
        """
        If the input is multiple columns (a list)
        """
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

    def test_remove_duplicates_4(self):
        """
        If the input and output are not the same type
        """
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
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "The lists for" in info.value.args[0]
        )

    def test_remove_duplicates_where(self):
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
            where: numbers != 45
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['duplicates'] == 'duplicate' and df.iloc[1]['duplicates'] == 'and another and another'

    def test_remove_duplicates_list_ignore_case(self):
        """
        Test remove_duplicates where input is a list with ignore_case
        """
        data = pd.DataFrame([[['Agent Smith', 'agent smith', 'AGENT SMITH']]], columns=['Agents'])
        recipe = """
        wrangles:
        - format.remove_duplicates:
            input: Agents
            output: Remove
            ignore_case: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Remove'] == ['Agent Smith']

    def test_remove_duplicates_string_ignore_case(self):
        """
        Test remove_duplicates where input is a string with ignore_case
        """
        data = pd.DataFrame([['Agent Smith agent smith AGENT SMITH']], columns=['Agents'])
        recipe = """
        wrangles:
        - format.remove_duplicates:
            input: Agents
            output: Remove
            ignore_case: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Remove'] == 'Agent Smith'

    def test_remove_duplicates_empty_dataframe(self):
        """
        Test remove_duplicates with an empty dataframe
        """
        data = pd.DataFrame(columns=['Agents'])
        recipe = """
        wrangles:
        - format.remove_duplicates:
            input: Agents
            output: Remove
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Agents', 'Remove']


class TestFormatTrim:
    """
    Test format.trim
    """
    def test_trim_1(self):
        data = pd.DataFrame([['         Wilson!         '], ['VAC']], columns=['Alone'])
        recipe = """
        wrangles:
        - format.trim:
            input: 
            - Alone
            output: Trim
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Trim'] == 'Wilson!'

    def test_trim_2(self):
        """
        Trim input is a string
        """
        data = pd.DataFrame([['         Wilson!         ']], columns=['Alone'])
        recipe = """
        wrangles:
        - format.trim:
            input: Alone
            output: Trim
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Trim'] == 'Wilson!'

    def test_trim_where(self):
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
            where: numbers > 5
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['column'] == 'Where' and df.iloc[0]['column'] == '         Wilson!         '

    def test_trim_list_to_list(self):
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

    def test_trim_list_to_single_output(self):
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
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )
    
    def test_trim_invalid_data(self):
        """
        Test that trim fails gracefully with invalid data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - format.trim:
                input: List
            """,
            dataframe=pd.DataFrame({
                'List': [["item1 ", " item2"], "  item3  "]
            })
        )
        assert (
            df['List'][0] == ["item1 ", " item2"] and
            df['List'][1] == "item3"
        )

    def test_trim_empty_dataframe(self):
        """
        Test trim with an empty dataframe
        """
        data = pd.DataFrame(columns=['Alone'])
        recipe = """
        wrangles:
        - format.trim:
            input: Alone
            output: Trim
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Alone', 'Trim']


    def test_trim_various_data_types(self):
        """
        Test trim on various data types
        """
        data = pd.DataFrame({
            'column': ['This is a string     ', 459, ['This', 'is', 'a', 'list'], {'Dict': 'ionary'}, 3.14159265359],
        })
        recipe = """
        wrangles:
        - format.trim:
            input: column
            output: output
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'This is a string' 
        assert df.iloc[1]['output'] == 459
        assert df.iloc[2]['output'] == ['This', 'is', 'a', 'list']
        assert df.iloc[3]['output'] == {'Dict': 'ionary'}
        assert df.iloc[4]['output'] == 3.14159265359


class TestFormatPrefix:
    """
    Test format.prefix
    """
    def test_prefix_1(self):
        """
        Output column defined
        """
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

    def test_prefix_2(self):
        """
        Output column not defined
        """
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

    def test_prefix_3(self):
        """
        If the input is multiple lines
        """
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

    def test_prefix_4(self):
        """
        If the input and output are no the same type
        """
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
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "The lists for" in info.value.args[0]
        )

    def test_prefix_where(self):
        """
        Test format.prefix using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - format.prefix:
                input: col
                value: extra-
                where: numbers = 3
            """,
            dataframe=pd.DataFrame({
                'col': ['terrestrial', 'ordinary', 'califragilisticexpialidocious'],
                'numbers': [5, 4, 3]
            })
        )
        assert df['col'][0] == 'terrestrial' and df['col'][2] == 'extra-califragilisticexpialidocious'

    def test_prefix_empty_dataframe(self):
        """
        Test prefix with an empty dataframe
        """
        data = pd.DataFrame(columns=['col'])
        recipe = """
        wrangles:
        - format.prefix:
            input: col
            output: pre-col
            value: extra-
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['col', 'pre-col']

    def test_prefix_numeric_value_integer(self):
        """
        Test prefix with integer variable (fixes issue #683)
        """
        data = pd.DataFrame({
            'col': ['A', 'B', 'C']
        })
        recipe = """
        wrangles:
        - format.prefix:
            input: col
            output: result
            value: ${batch_number}
        """
        df = wrangles.recipe.run(recipe, dataframe=data, variables={'batch_number': 456})
        assert df.iloc[0]['result'] == '456A' and df.iloc[1]['result'] == '456B'

    def test_prefix_numeric_value_float(self):
        """
        Test prefix with float variable (fixes issue #683)
        """
        data = pd.DataFrame({
            'col': ['X', 'Y']
        })
        recipe = """
        wrangles:
        - format.prefix:
            input: col
            output: result
            value: ${version}
        """
        df = wrangles.recipe.run(recipe, dataframe=data, variables={'version': 2.1})
        assert df.iloc[0]['result'] == '2.1X' and df.iloc[1]['result'] == '2.1Y'

    def test_prefix_skip_mult_empty_false(self):
        """
        Testing format.prefix with skip_empty false
        """
        data = pd.DataFrame({
            'col1': ['terrestrial','','ordinary'],
            'col2': ['soft','','cripsy'],
        })
        recipe = """
        wrangles:
            - format.prefix:
                input:
                    - col1
                    - col2
                output: 
                    - out1
                    - out2
                value: extra-
        """   
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['out1'].tolist() == ['extra-terrestrial', 'extra-', 'extra-ordinary']
        assert df['out2'].tolist() == ['extra-soft', 'extra-', 'extra-cripsy']

    def test_prefix_skip_mult_empty_true(self):
        """
        Testing format.prefix with skip_empty true
        """
        data = pd.DataFrame({
            'col1': ['terrestrial','','ordinary'],
            'col2': ['soft','','cripsy'],
        })
        recipe = """
        wrangles:
            - format.prefix:
                input:
                    - col1
                    - col2
                output: 
                    - out1
                    - out2
                value: extra-
                skip_empty: true
        """   
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['out1'].tolist() == ['extra-terrestrial', '', 'extra-ordinary']
        assert df['out2'].tolist() == ['extra-soft', '', 'extra-cripsy']

    def test_prefix_skip_empty_false(self):
        """
        Testing format.prefix with skip_empty false
        """
        data = pd.DataFrame(
            [['Red White Blue Round Titanium Shield'],
            ['300V 1/2" Drive Impact Wrench'],
            [''],
            ['400 torque 1/2" Drive Impact Wrench'],
            [''],
            ['Hard Hat 30in w/ Light'],
            ],
            columns=['Tools']
        )
        recipe = """
        wrangles:
            - format.prefix:
                input: Tools
                output: Tool Output
                value: OSHA approved-
                skip_empty: false
        """   
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Tool Output'].tolist() == ['OSHA approved-Red White Blue Round Titanium Shield', 'OSHA approved-300V 1/2" Drive Impact Wrench', 'OSHA approved-', 'OSHA approved-400 torque 1/2" Drive Impact Wrench', 'OSHA approved-', 'OSHA approved-Hard Hat 30in w/ Light']

    def test_prefix_skip_empty_true(self):
        """
        Testing format.prefix with skip_empty true
        """
        data = pd.DataFrame(
            [['Red White Blue Round Titanium Shield'],
            ['300V 1/2" Drive Impact Wrench'],
            [''],
            ['400 torque 1/2" Drive Impact Wrench'],
            [''],
            ['Hard Hat 30in w/ Light'],
            ],
            columns=['Tools']
        )
        recipe = """
        wrangles:
        - format.prefix:
            input: Tools
            output: Tool Output
            value: OSHA approved-
            skip_empty: true
        """   
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Tool Output'].tolist() == ['OSHA approved-Red White Blue Round Titanium Shield', 'OSHA approved-300V 1/2" Drive Impact Wrench', '', 'OSHA approved-400 torque 1/2" Drive Impact Wrench', '', 'OSHA approved-Hard Hat 30in w/ Light']


class TestFormatSuffix:
    """
    Test format.suffix
    """
    def test_suffix_1(self):
        """
        Output column defined
        """
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

    def test_suffix_2(self):
        """
        Output column not defined
        """
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

    def test_suffix_3(self):
        """
        If the input is multiple columns(a list)
        """
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

    def test_suffix_4(self):
        """
        If the input and output are not the same type
        """
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
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "The lists for" in info.value.args[0]
        )

    def test_suffix_where(self):
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
            value: -cy
            where: numbers = 99
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['col'] == 'urgen' and df.iloc[2]['col'] == 'supercalifragilisticexpialidocious-cy'

    def test_suffix_empty_dataframe(self):
        """
        Test suffix with an empty dataframe
        """
        data = pd.DataFrame(columns=['col'])
        recipe = """
        wrangles:
        - format.suffix:
            input: col
            output: col-suf
            value: -cy
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['col', 'col-suf']

    def test_suffix_numeric_value_integer(self):
        """
        Test suffix with integer variable (fixes issue #683)
        """
        data = pd.DataFrame({
            'col': ['A', 'B', 'C']
        })
        recipe = """
        wrangles:
        - format.suffix:
            input: col
            output: result
            value: ${batch_number}
        """
        df = wrangles.recipe.run(recipe, dataframe=data, variables={'batch_number': 123})
        assert df.iloc[0]['result'] == 'A123' and df.iloc[1]['result'] == 'B123'

    def test_suffix_numeric_value_float(self):
        """
        Test suffix with float variable (fixes issue #683)
        """
        data = pd.DataFrame({
            'col': ['X', 'Y']
        })
        recipe = """
        wrangles:
        - format.suffix:
            input: col
            output: result
            value: ${version}
        """
        df = wrangles.recipe.run(recipe, dataframe=data, variables={'version': 1.5})
        assert df.iloc[0]['result'] == 'X1.5' and df.iloc[1]['result'] == 'Y1.5'
    
    def test_suffix_skip_mult_empty_false(self):
        """
        Testing format.suffix with skip_empty false
        """
        data = pd.DataFrame({
            'col1': ['hard','','soft'],
            'col2': ['quick','','slow'],
        })
        recipe = """
        wrangles:
            - format.suffix:
                input:
                    - col1
                    - col2
                output: 
                    - out1
                    - out2
                value: ly
        """   
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['out1'].tolist() == ['hardly', 'ly', 'softly']
        assert df['out2'].tolist() == ['quickly', 'ly', 'slowly']


    def test_suffix_skip_mult_empty_true(self):
        """
        Testing format.suffix with skip_empty true
        """
        data = pd.DataFrame({
            'col1': ['hard','','soft'],
            'col2': ['quick','','slow'],
        })
        recipe = """
        wrangles:
            - format.suffix:
                input:
                    - col1
                    - col2
                output: 
                    - out1
                    - out2
                value: ly
                skip_empty: true
        """   
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['out1'].tolist() == ['hardly', '', 'softly']
        assert df['out2'].tolist() == ['quickly', '', 'slowly']

class TestFormatDates:
    """
    Test format.dates
    """
    def test_date_format_1(self):
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
        
    def test_date_format_where(self):
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

    def test_date_format_empty_dataframe(self):
        """
        Test date_format with an empty dataframe
        """
        data = pd.DataFrame(columns=['col'])
        recipe = """
        wrangles:
        - format.dates:
            input: col
            output: output column
            format: "%Y-%m-%d"
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['col', 'output column']


class TestFormatPad:
    """
    Test format.pad
    """
    def test_pad_1(self):
        """
        Normal operation left
        """
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
    def test_pad_2(self):
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

    def test_pad_list_to_list(self):
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

    def test_pad_list_to_single_output(self):
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
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_pad_where(self):
        """
        Test using a where clause
        """
        data = pd.DataFrame({
            'col1': ['7', '5', '9'],
            'numbers': [3, 4, 5]
        })
        recipe = """
        wrangles:
            - format.pad:
                input: col1
                pad_length: 3
                side: left
                char: 0
                where: numbers = 3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['col1'] == '007' and df.iloc[2]['col1'] == '9'

    def test_pad_empty_dataframe(self):
        """
        Test pad with an empty dataframe
        """
        data = pd.DataFrame(columns=['col1'])
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
        assert df.empty and df.columns.to_list() == ['col1', 'out1']

    def test_pad_skip_empty_true(self):  
        """  
        Test pad with skip_empty=True - should skip padding empty strings  
        """  
        data = pd.DataFrame({  
            'col1': ['7', '', '9']  
        })  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                output: out1  
                pad_length: 3  
                side: left  
                char: 0  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['out1'] == '007' and  
            df.iloc[1]['out1'] == '' and  
            df.iloc[2]['out1'] == '009'  
        )  
    
    def test_pad_skip_empty_whitespace(self):  
        """  
        Test pad with skip_empty=True - should skip padding whitespace-only strings  
        """  
        data = pd.DataFrame({  
            'col1': ['7', '  ', '\t', '9']  
        })  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                output: out1  
                pad_length: 3  
                side: left  
                char: 0  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['out1'] == '007' and  
            df.iloc[1]['out1'] == '  ' and  
            df.iloc[2]['out1'] == '\t' and  
            df.iloc[3]['out1'] == '009'  
        )  
    
    def test_pad_skip_empty_false(self):  
        """  
        Test pad with skip_empty=False - should pad all values including empty  
        """  
        data = pd.DataFrame({  
            'col1': ['7', '', '9']  
        })  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                output: out1  
                pad_length: 3  
                side: left  
                char: 0  
                skip_empty: false  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['out1'] == '007' and  
            df.iloc[1]['out1'] == '000' and  
            df.iloc[2]['out1'] == '009'  
        )  
    
    def test_pad_skip_empty_default(self):  
        """  
        Test pad without skip_empty parameter - should default to False (pad everything)  
        """  
        data = pd.DataFrame({  
            'col1': ['7', '', '9']  
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
        assert (  
            df.iloc[0]['out1'] == '007' and  
            df.iloc[1]['out1'] == '000' and  
            df.iloc[2]['out1'] == '009'  
        )  
    
    def test_pad_skip_empty_right_side(self):  
        """  
        Test pad with skip_empty=True and side=right  
        """  
        data = pd.DataFrame({  
            'col1': ['7', '', '9']  
        })  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                output: out1  
                pad_length: 3  
                side: right  
                char: 0  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['out1'] == '700' and  
            df.iloc[1]['out1'] == '' and  
            df.iloc[2]['out1'] == '900'  
        )  
    
    def test_pad_skip_empty_list_columns(self):  
        """  
        Test pad with skip_empty=True on multiple columns  
        """  
        data = pd.DataFrame({  
            'col1': ['7', ''],  
            'col2': ['', '8']  
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
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['out1'] == '007' and  
            df.iloc[0]['out2'] == '' and  
            df.iloc[1]['out1'] == '' and  
            df.iloc[1]['out2'] == '008'  
        )  
    
    def test_pad_skip_empty_where_clause(self):  
        """  
        Test pad with skip_empty=True combined with where clause  
        """  
        data = pd.DataFrame({  
            'col1': ['7', '', '9'],  
            'numbers': [3, 4, 5]  
        })  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                pad_length: 3  
                side: left  
                char: 0  
                skip_empty: true  
                where: numbers = 3  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['col1'] == '007' and  
            df.iloc[1]['col1'] == '' and  
            df.iloc[2]['col1'] == '9'  
        )  
    
    def test_pad_skip_empty_overwrite_input(self):  
        """  
        Test pad with skip_empty=True when output is not specified (overwrite input)  
        """  
        data = pd.DataFrame({  
            'col1': ['7', '', '9']  
        })  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                pad_length: 3  
                side: left  
                char: 0  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['col1'] == '007' and  
            df.iloc[1]['col1'] == '' and  
            df.iloc[2]['col1'] == '009'  
        )  
    
    def test_pad_skip_empty_mixed_content(self):  
        """  
        Test pad with skip_empty=True on mixed content (numbers, strings, empty)  
        """  
        data = pd.DataFrame({  
            'col1': [7, '', 'abc', '  ', 9]  
        })  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                output: out1  
                pad_length: 5  
                side: left  
                char: 0  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert (  
            df.iloc[0]['out1'] == '00007' and  
            df.iloc[1]['out1'] == '' and  
            df.iloc[2]['out1'] == '00abc' and  
            df.iloc[3]['out1'] == '  ' and  
            df.iloc[4]['out1'] == '00009'  
        )  
    
    def test_pad_skip_empty_empty_dataframe(self):  
        """  
        Test pad with skip_empty=True on empty dataframe  
        """  
        data = pd.DataFrame(columns=['col1'])  
        recipe = """  
        wrangles:  
            - format.pad:  
                input: col1  
                output: out1  
                pad_length: 3  
                side: left  
                char: 0  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.empty and df.columns.to_list() == ['col1', 'out1']

class TestFormatSignificantFigures:
    """
    Test format.significant_figures
    """
    def test_sig_figs(self):
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

    def test_sig_figs_with_value(self):
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

    def test_sig_figs_where(self):
        """
        Test converting multiple number types to desired
        significant figures with where
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - format.significant_figures:
                input: col1
                where: numbers > 5
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
                ], 
                'numbers': [3, 4, 5, 6, 7, 8, 9]
            })
        )
        assert (
            df['col1'].to_list() == [
                '13.45644 ft',
                'length: 34453.3323ft',
                '34.234234',
                'nothing here',
                13.5,
                1130000,
                ''
            ]
        )

    def test_sig_figs_empty_dataframe(self):
        """
        Test significant_figures with an empty dataframe
        """
        data = pd.DataFrame(columns=['col1'])
        recipe = """
        wrangles:
            - format.significant_figures:
                input: col1
                output: out1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['col1', 'out1']
