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
            raise wrangles.recipe.run(recipe, dataframe=data)
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
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )


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
            raise wrangles.recipe.run(recipe, dataframe=data)
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
            raise wrangles.recipe.run(recipe, dataframe=data)
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
            raise wrangles.recipe.run(recipe, dataframe=data)
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
