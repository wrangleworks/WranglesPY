import pytest
import wrangles
import pandas as pd
import numpy as np
import time
from datetime import datetime


class TestClassify:
    """
    Test classify
    """
    def test_classify(self):
        """
        Test classify on a single input
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: Chicken
            wrangles:
                - classify:
                    input: Col1
                    output: Class
                    model_id: a62c7480-500e-480c
            """
        )
        assert df['Class'][0] == 'Meat'

    def test_include_confidence(self):
        """
        Test setting include_confidence = True
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: Chicken
            wrangles:
                - classify:
                    input: Col1
                    output: Class
                    model_id: a62c7480-500e-480c
                    include_confidence: True
            """
        )
        assert (
            df['Class'][0]['Label'] == 'Meat' and
            df['Class'][0]['Confidence'] > 0.2
        )

    def test_classify_multi_input_output(self):
        """
        Multiple column input and output
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: Chicken
                    Col2: Cheese
            wrangles:
            - classify:
                input:
                    - Col1
                    - Col2
                output:
                    - Output 1
                    - Output 2
                model_id: a62c7480-500e-480c
            """
        )
        assert df['Output 1'][0] == 'Meat' and df['Output 2'][0] == 'Dairy'

    def test_classify_inconsistent_input_output_lengths(self):
        """
        Test that a clear error is given when multiple inputs are given
        if the output does not match the same length.
        """
        data = pd.DataFrame({
        'Col1': ['Ball Bearing'],
        'Col2': ['Ball Bearing']
        })
        recipe = """
        wrangles:
            - classify:
                input: 
                - Col1
                - Col2
                output: 
                - Class
                model_id: a62c7480-500e-480c
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "The lists for" in info.value.args[0]
        )

    def test_classify_extract_model_id(self):
        """
        Test error message when passing an extract model id into a classify wrangle
        """
        data = pd.DataFrame({
        'Col1': ['Ball Bearing'],
        'Col2': ['Ball Bearing']
        })
        recipe = """
        wrangles:
            - classify:
                input: 
                - Col1
                output: 
                - Class
                model_id: 1eddb7e8-1b2b-4a52
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Using extract model_id 1eddb7e8-1b2b-4a52 in a classify function.' in info.value.args[0]
        )

    def test_classify_invalid_model(self):
        """
        # Incorrect model_id missing "${ }" around value
        """
        data = pd.DataFrame({
        'Col1': ['Ball Bearing'],
        'Col2': ['Ball Bearing']
        })
        recipe = """
        wrangles:
            - classify:
                input: 
                - Col1
                - Col2
                output: 
                - Class
                - Class2
                model_id: noWord
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX' in info.value.args[0]
        )
        
    def test_classify_invalid_variable_syntax(self):
        """
        # Not using ${} in recipe when using a model-id
        """
        data = pd.DataFrame({
        'Col1': ['Ball Bearing'],
        'Col2': ['Ball Bearing']
        })
        recipe = """
        wrangles:
            - classify:
                input: 
                - Col1
                - Col2
                output: 
                - Class
                - Class2
                model_id: {noWord}
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value' in info.value.args[0]
        )

    def test_classify_where(self):
        """
        Test classify using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - classify:
                    input: Col1
                    output: Class1
                    model_id: a62c7480-500e-480c
                    where: number > 25
            """,
            dataframe=pd.DataFrame({
                'Col1': ['Chicken', 'Cheese'],
                'number': [25, 31]
            })
        )
        assert df['Class1'][0] == "" and df['Class1'][1] == 'Dairy'

    def test_classify_empty(self):
        """
        Test classify with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - classify:
                    input: Col1
                    output: Class1
                    model_id: a62c7480-500e-480c
            """,
            dataframe=pd.DataFrame({
                'Col1': [],
            })
        )
        assert df.empty and df.columns.tolist() == ['Col1', 'Class1']


class TestFilter:
    """
    Test filter
    """
    def test_filter_equal(self):
        """
        Equal
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Color': ['red','green', 'orange', 'red']
        })
        recipe = """
        wrangles:
            - filter:
                input: Color
                equal:
                - red
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Fruit'] == 'Strawberry'

    def test_filter_not_equal(self):
        """
        Test not_equal
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Color': ['red','green', 'orange', 'red']
        })
        recipe = """
        wrangles:
            - filter:
                input: Color
                not_equal: red
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Fruit'] == 'Orange'

    def test_filter_in(self):
        """
        Test is_in
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Color': ['red','green', 'orange', 'red']
        })
        recipe = """
        wrangles:
            - filter:
                input: Color
                is_in:
                - red
                - green
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Fruit'] == 'Apple'

    def test_filter_not_in(self):
        """
        Not_in
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Color': ['red','green', 'orange', 'red']
        })
        recipe = """
        wrangles:
            - filter:
                input: Color
                not_in:
                - red
                - green
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Fruit'] == 'Orange'

    def test_filter_greater_than(self):
        """
        Greater_than
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Number': [13, 26, 13, 26]
        })
        recipe = """
        wrangles:
            - filter:
                input: Number
                greater_than: 14
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Fruit'] == 'Apple'

    def test_filter_greater_than_equal_to(self):
        """
        Greater_than or equal to
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Number': [13, 26, 13, 26]
        })
        recipe = """
        wrangles:
            - filter:
                input: Number
                greater_than_equal_to: 13
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 4

    def test_filter_less_than(self):
        """
        Less than
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Number': [13, 26, 13, 26]
        })
        recipe = """
        wrangles:
            - filter:
                input: Number
                less_than: 26
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 2

    def test_filter_less_than_equal_to(self):
        """
        Less than or equal to
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Number': [13, 26, 13, 26]
        })
        recipe = """
        wrangles:
            - filter:
                input: Number
                less_than_equal_to: 25
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 2

    def test_filter_between(self):
        """
        Between
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Number': [13, 26, 52, 52]
        })
        recipe = """
        wrangles:
            - filter:
                input: Number
                between:
                - 14
                - 50
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Fruit'] == 'Apple'

    def test_filter_between_error(self):
        """
        Between, more than two values error
        """
        data = pd.DataFrame({
            'Fruit': ['Apple', 'Apple', 'Orange', 'Strawberry'],
            'Number': [13, 26, 52, 52]
        })
        recipe = """
        wrangles:
            - filter:
                input: Number
                between:
                - 14
                - 50
                - 133
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Can only use "between" with two values' in info.value.args[0]
        )

    def test_filter_contains(self):
        """
        Contains
        """
        data = pd.DataFrame({
            'Random': ['Apples', 'Random', 'App', 'nothing here'],
            'Number': [13, 26, 52, 52]
        })
        recipe = """
        wrangles:
            - filter:
                input: Random
                contains: 'App'
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 2

    def test_filter_not_contains(self):
        """
        Does not contain
        """
        data = pd.DataFrame({
            'Random': ['Apples', 'Applications', 'App', 'nothing here'],
            'Number': [13, 26, 52, 52]
        })
        recipe = """
        wrangles:
            - filter:
                input: Random
                not_contains: App
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 1

    def test_filter_is_null_true(self):
        """
        is_null
        """
        data = pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
        recipe = """
        wrangles:
            - filter:
                input: Random
                is_null: False
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 3

    def test_filter_is_null_false(self):
        """
        not_null, False
        """
        data = pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
        recipe = """
        wrangles:
            - filter:
                input: Random
                is_null: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 1

    def test_filter_multiple(self):
        data = pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
        recipe = """
        wrangles:
            - filter:
                input: Random
                contains: App
                not_contains: les
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 1

    def test_filter_where(self):
        data = pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
        recipe = """
        wrangles:
            - filter:
                where: Random = 'Apples'
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 1

    def test_filter_where_params(self):
        """
        Test a parameterized where condition
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - filter:
                where: Random = ?
                where_params:
                    - Apples
            """,
            dataframe= pd.DataFrame({
                'Random': ['Apples', 'None', 'App', None],
            })
        )
        assert len(df) == 1 and df['Random'][0] == 'Apples'

    def test_filter_where_params_dict(self):
        """
        Test a parameterized where condition
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - filter:
                where: Random = :var
                where_params:
                    var: Apples
            """,
            dataframe= pd.DataFrame({
                'Random': ['Apples', 'None', 'App', None],
            })
        )
        assert len(df) == 1 and df['Random'][0] == 'Apples'

    def test_filter_where_or(self):
        data = pd.DataFrame({
            'Random': ['Apples', 'None', 'App', None],
        })
        recipe = """
        wrangles:
          - filter:
              where: |
                Random = 'Apples'
                OR Random = 'App'
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert len(df) == 2

    def test_filter_input_list(self):
        """
        Test using a list for input. All input columns must match the criteria
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - filter:
                input:
                    - Column1
                    - Column2
                contains: App
            """,
            dataframe = pd.DataFrame({
                'Column1': ['Apples', 'None', 'App', 'Other'],
                'Column2': ['Apples', 'Apples', 'Other', 'Other']
            })
        )
        assert len(df) == 1

    def test_filter_empty(self):
        """
        Test filter with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - filter:
                    input: Random
                    contains: App
            """,
            dataframe=pd.DataFrame({
                'Random': [],
            })
        )
        assert df.empty and df.columns.tolist() == ['Random']


@pytest.mark.usefixtures("caplog")
class TestLog:
    """
    All log tests
    """
    def test_log_columns(self, caplog):
        """
        Test log when specifying columns
        """
        data = pd.DataFrame({
        'Col1': ['Chicken'],
        'Col2': ['Cheese']
        })
        recipe = """
        wrangles:
            - log:
                columns:
                  - Col1
        """
        wrangles.recipe.run(recipe, dataframe=data)
        assert caplog.messages[-1] == ': Dataframe ::\n\n      Col1\n0  Chicken\n'

    def test_log(self, caplog):
        """
        Test default log
        """
        data = pd.DataFrame({
        'Col1': ['Ball Bearing'],
        'Col2': ['Bearing']
        })
        recipe = """
        wrangles:
            - log: {}
        """
        wrangles.recipe.run(recipe, dataframe=data)
        assert caplog.messages[-1] == ': Dataframe ::\n\n           Col1     Col2\n0  Ball Bearing  Bearing\n'

    def test_log_wildcard(self, caplog):
        """
        Test one column with wildcard
        """
        data = pd.DataFrame({
            'Col': ['Hello, Wrangle, Works'],
        })
        recipe = """
        wrangles:
          - split.text:
              input: Col
              output: Col*
              char: ', '

          - log:
              columns:
                - Col*
        """
        wrangles.recipe.run(recipe, dataframe=data)
        assert caplog.messages[-1] == ': Dataframe ::\n\n                     Col   Col1     Col2   Col3\n0  Hello, Wrangle, Works  Hello  Wrangle  Works\n'

    def test_log_escaped_wildcard(self, caplog):
        """
        Test escaping a wildcard when specifying columns.
        """
        data = pd.DataFrame({
            'Col': ['Hello'],
            'Col*': ['WrangleWorks!'],
        })
        recipe = r"""
        wrangles:
          - log:
              columns:
                - Col\*
        """
        wrangles.recipe.run(recipe, dataframe=data)
        assert caplog.messages[-1] == ': Dataframe ::\n\n            Col*\n0  WrangleWorks!\n'

    def test_log_write(self):
        """
        Test using a connector as part of a log
        """
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 5
                  values:
                    header: value
                
            wrangles:
              - log:
                  write:
                    - file:
                        name: tests/temp/temp.csv
            """
        )
        df = wrangles.recipe.run(
            """
            read:
              - file:
                  name: tests/temp/temp.csv
            """
        )
        assert len(df) == 5 and df['header'][0] == 'value'

    def test_log_length(self, caplog):
        """
        Test default log
        """
        data = pd.DataFrame({
        'Col1': ['Ball Bearing'],
        'Col2': ['Bearing']
        })
        recipe = """
        read:
          - test:
              rows: 30
              values:
                Col1: Ball Bearing
                Col2: Bearing
        wrangles:
            - log: {}
        """
        wrangles.recipe.run(recipe, dataframe=data)
        assert 'Bearing\n19' in caplog.messages[-1] and 'Bearing\n20' not in caplog.messages[-1]

    def test_log_where(self, caplog):
        """
        Test log when specifying columns
        """
        data = pd.DataFrame({
        'Col1': ['Pizza', 'Chicken', 'Cheese'],
        'numbers': [2, 4, 3]
        })
        recipe = """
        wrangles:
            - log:
                columns:
                  - Col1
                where: numbers >= 3
        """
        wrangles.recipe.run(recipe, dataframe=data)
        assert caplog.messages[-1] == ': Dataframe ::\n\n      Col1\n1  Chicken\n2   Cheese\n'

    def test_log_empty(self, caplog):
        """
        Test log with empty data
        """
        wrangles.recipe.run(
            """
            wrangles:
                - log: {}
            """,
            dataframe=pd.DataFrame({
                'Col1': [],
            })
        )
        assert caplog.messages[-1] == ': Dataframe ::\n\nEmpty DataFrame\nColumns: [Col1]\nIndex: []\n'


class TestRemoveWords:
    """
    Test remove_words
    """
    def test_remove_words_1(self):
        """
        Input is a string
        """
        data = pd.DataFrame({
        'Description': ['Steel Blue Bottle'],
        'Materials': [['Steel']],
        'Colours': [['Blue']]
        })
        recipe = """
        wrangles:
            - remove_words:
                input: Description
                to_remove:
                    - Materials
                    - Colours
                output: Product
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Product'] == 'Bottle'

    def test_remove_words_2(self):
        """
        Input is a List
        """
        data = pd.DataFrame({
        'Description': [['Steel', 'Blue', 'Bottle']],
        'Materials': [['Steel']],
        'Colours': [['Blue']]
        })
        recipe = """
        wrangles:
            - remove_words:
                input: Description
                to_remove:
                    - Materials
                    - Colours
                output: Product
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Product'] == 'Bottle'

    def test_remove_words_3(self):
        """
        If the input is multiple columns (a list)
        """
        data = pd.DataFrame({
        'Description': [['Steel', 'Blue', 'Bottle']],
        'Description2': [['Steel', 'Blue', 'Bottle']],
        'Materials': [['Steel']],
        'Colours': [['Blue']]
        })
        recipe = """
        wrangles:
            - remove_words:
                input:
                - Description
                - Description2
                to_remove:
                    - Materials
                    - Colours
                output:
                - Product1
                - Product2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Product2'] == 'Bottle'

    def test_remove_words_4(self):
        """
        If the input and output are not the same type
        """
        data = pd.DataFrame({
        'Description': [['Steel', 'Blue', 'Bottle']],
        'Description2': [['Steel', 'Blue', 'Bottle']],
        'Materials': [['Steel']],
        'Colours': [['Blue']]
        })
        recipe = """
        wrangles:
            - remove_words:
                input:
                - Description
                - Description2
                to_remove:
                    - Materials
                    - Colours
                output: Product1
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "The lists for" in info.value.args[0]
        )

    def test_remove_words_tokenize(self):
        """
        Tokenize inputs
        """
        data = pd.DataFrame({
            'col': ['Metal Carbon Water Tank'],
            'materials': ['Metal Carbon']
        })
        recipe = """
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - materials
            output: Out
            tokenize_to_remove: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'Water Tank'

    def test_remove_words_case_sensitive(self):
        """
        Raw inputs, ignore case is False
        """
        data = pd.DataFrame({
            'col': ['METAl CaRBon WateR TaNk'],
            'materials': ['meTAL CaRBon']
        })
        recipe = """
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - materials
            output: Out
            tokenize_to_remove: True
            ignore_case: False
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'METAl WateR TaNk'

    def test_remove_words_tokenize_case_sensitive(self):
        """
        Tokenize inputs and ignore case
        """
        data = pd.DataFrame({
            'col': ['METAl CaRBon WateR TaNk'],
            'materials': ['meTAL carbOn']
        })
        recipe = """
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - materials
            output: Out
            tokenize_to_remove: True
            ignore_case: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'WateR TaNk'

    def test_remove_words_where(self):
        """
        Test remove_words using where
        """
        data = pd.DataFrame({
        'Description': [['Steel', 'Blue', 'Bottle'], ['Aluminum', 'Red', 'Can'], ['Rubber', 'Yellow', 'Tire']],
        'Description2': [['Steel', 'Blue', 'Bottle'], ['Titanium', 'Blue', 'Pipe'], ['Iron', 'Brown', 'Plate']],
        'Materials': [['Steel', 'Rubber', 'Aluminum', 'Titanium', 'Iron'], ['Steel', 'Rubber', 'Aluminum', 'Titanium', 'Iron'], ['Steel', 'Rubber', 'Aluminum', 'Titanium', 'Iron']],
        'Colours': [['Blue', 'Red', 'Yellow', 'Brown'], ['Blue', 'Red', 'Yellow', 'Brown'], ['Blue', 'Red', 'Yellow', 'Brown']],
        'numbers': [4, 3, 2]
        })
        recipe = """
        wrangles:
            - remove_words:
                input:
                - Description
                - Description2
                to_remove:
                - Materials
                - Colours
                output: 
                - Product1
                - Product2
                where: numbers >= 3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Product1'] == 'Bottle' and df.iloc[1]['Product2'] == 'Pipe' and df.iloc[2]['Product1'] == ""

    def test_remove_words_mixed_to_remove(self):
        """
        Having a list and strings in to_remove
        """
        data = pd.DataFrame({
            'col': ['Brand 186 T18 Round Crown Staples, 3/8" x 7/16", 333 Pack'],
            'rem1': [['3/8" x 7/16"']],
            'rem2': ["Round"]
        })
        recipe="""
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - rem1
                - rem2
            output: Out
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'Brand 186 T18 Crown Staples, 333 Pack'
        
    def test_remove_words_mixed_to_remove_2(self):
        """
        Having a list and numbers in to_remove
        """
        data = pd.DataFrame({
            'col': ['Brand 186 T18 Round Crown Staples, 3/8" x 7/16", 333 Pack'],
            'rem1': [['3/8" x 7/16"']],
            'rem2': ["Round"],
            'rem3': [333],
            'rem4': [[186]]
        })
        recipe="""
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - rem1
                - rem2
                - rem3
                - rem4
            output: Out
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'Brand T18 Crown Staples, Pack'
        
    def test_remove_words_mixed_to_remove_3(self):
        """
        remove a mix of strings and numbers and lists using tokenize
        """
        data = pd.DataFrame({
            'col': ['Brand 186 T18 Round Crown Staples, 3/8" x 7/16", 333 Pack express'],
            'rem1': [['3/8" x 7/16"']],
            'rem2': ["Round Crown Staples"],
            'rem3': [333],
            'rem4': [[186]]
        })
        recipe="""
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - rem1
                - rem2
                - rem3
                - rem4
            output: Out
            tokenize_to_remove: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'Brand T18 Pack express'
        
    def test_remove_words_mixed_to_remove_4(self):
        """
        Make sure parts of words are not cut off
        """
        data = pd.DataFrame({
            'col': ['Plus and DataSomething and StringTheory and Relativity and 2288 and 2323'],
            'rem1': [['us']],
            'rem2': ["Data"],
            'rem3': [2],
            'rem4': [["Rela"]],
            'rem5': [["String"]]
        })
        recipe="""
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - rem1
                - rem2
                - rem3
                - rem4
                - rem5
            output: Out
            tokenize_to_remove: False
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'Plus and DataSomething and StringTheory and Relativity and 2288 and 2323'
        
    def test_remove_words_mixed_to_remove_5(self):
        """
        Make sure parts of words are not cut off using tokenize
        """
        data = pd.DataFrame({
            'col': ['Plus and DataSomething and StringTheory and Relativity and 2288 and 2323'],
            'rem1': [['us']],
            'rem2': ["Data"],
            'rem3': [2],
            'rem4': [["Rela"]],
            'rem5': [["String"]]
        })
        recipe="""
        wrangles:
        - remove_words:
            input: col
            to_remove:
                - rem1
                - rem2
                - rem3
                - rem4
                - rem5
            output: Out
            tokenize_to_remove: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['Out'].iloc[0] == 'Plus and DataSomething and StringTheory and Relativity and 2288 and 2323'

    def test_remove_words_empty(self):
        """
        Test remove_words with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - remove_words:
                    input: Random
                    output: output column
                    to_remove: App
            """,
            dataframe=pd.DataFrame({
                'Random': [],
            })
        )
        assert df.empty and df.columns.to_list() == ['Random', 'output column']


class TestRename:
    """
    All rename tests
    """
    def test_rename_dict(self):
        """
        Rename using a dictionary of columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - rename:
                Manufacturer Name: Company
                Part Number: MPN
            """,
            dataframe = pd.DataFrame({
                'Manufacturer Name': ['Delos'],
                'Part Number': ['CH465517080'],
            })
        )
        assert df.iloc[0]['MPN'] == 'CH465517080'

    def test_rename_input_output(self):
        """
        Rename using a single input to a single output
        """
        data = pd.DataFrame({
        'Manufacturer Name': ['Delos'],
        'Part Number': ['CH465517080'],
        })
        recipe = """
        wrangles:
            - rename:
                input: Manufacturer Name
                output: Company
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Company'] == 'Delos'

    def test_rename_missing_output(self):
        """
        Check error if input is provided but not output
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(
                """
                wrangles:
                    - rename:
                        input: Manufacturer Name
                """,
                dataframe = pd.DataFrame({
                    'Manufacturer Name': ['Delos'],
                    'Part Number': ['CH465517080'],
                })
            )
        assert (
            info.typename == 'ValueError' and
            'If an input' in info.value.args[0]
        )

    def test_rename_inconsistent_input_output(self):
        """
        Check error if the lists for input and output are not equal lengths
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(
                """
                wrangles:
                    - rename:
                        input: Manufacturer Name
                        output:
                        - Two
                        - Columns
                """,
                dataframe = pd.DataFrame({
                    'Manufacturer Name': ['Delos'],
                    'Part Number': ['CH465517080'],
                })
            )
        assert (
            info.typename == 'ValueError' and
            "The lists for" in info.value.args[0]
        )

    def test_rename_invalid_input(self):
        """
        Check error if a column specified in input doesn't exist
        """
        with pytest.raises(KeyError) as info:
            wrangles.recipe.run(
                """
                wrangles:
                    - rename:
                        input: doesn't exist
                        output: Column
                """,
                dataframe = pd.DataFrame({
                    'Manufacturer Name': ['Delos'],
                    'Part Number': ['CH465517080'],
                })
            )
        assert info.typename == 'KeyError'

    def test_rename_into_existing_column(self):
        """
        Rename a column to a name that already exists as a column.
        This should overwrite the existing column.
        """
        data = pd.DataFrame({
        'col1': [1, 2, 3, 4],
        'col2': [444, 555, 666, 444],
        })
        df = wrangles.recipe.run(
            """
            wrangles:        
            - rename:
                col2: col1
            """,
            dataframe=data
        )
        assert (
            df["col1"].values.tolist() == [444, 555, 666, 444] and
            df.columns.tolist() == ["col1"]
        )

    def test_rename_into_existing_column_dict(self):
        """
        Rename a column to a name that already exists as a column.
        This should make sure that all columns are pandas Series
        """
        data = pd.DataFrame({
        'col1': [1, 2, 3, 4],
        'col2': [444, 555, 666, 444],
        })

        recipe = """
        wrangles:
        - copy:
            input: col1
            output: col1_copy
            
        - create.column:
            output: col2_copy
            
        - rename:
            col2_copy: col1_copy
            col2: newCol2
        """
        df = wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert [str(type(df[x])) for x in df.columns] == ["<class 'pandas.core.series.Series'>" for _ in range(len(df.columns))]

    def test_rename_into_existing_column_input(self):
        """
        Rename a column to a name that already exists as a column.
        This should make sure that all columns are pandas Series. Using input/output
        """
        data = pd.DataFrame({
        'col1': [1, 2, 3, 4],
        'col2': [444, 555, 666, 444],
        })

        recipe = """
        wrangles:
        - copy:
            input: col1
            output: col1_copy
            
        - create.column:
            output: col2_copy
            
        - rename:
            input:
                - col2_copy
                - col2
            output:
                - col1_copy
                - newCol2
        """
        df = wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert [str(type(df[x])) for x in df.columns] == ["<class 'pandas.core.series.Series'>" for _ in range(len(df.columns))]


    def test_rename_wrangles(self):
        """
        Use wrangles to rename columns
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
                    header2: value2
            wrangles:
            - rename:
                wrangles:
                    - convert.case:
                        input: columns
                        case: upper
            """
        )
        assert df.columns.tolist() == ["HEADER1","HEADER2"]

    def test_rename_custom_function(self):
        """
        Test that a custom function for rename wrangles works correctly
        """
        def func(columns):
            return columns + "_1"
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
                    header2: value2
            wrangles:
            - rename:
                wrangles:
                    - custom.func:
                        output: columns
            """,
            functions=func
        )
        assert df.columns.tolist() == ["header1_1","header2_1"]

    def test_rename_column_named_functions(self):
        """
        Test that a column named functions is still
        renamed correctly.
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    functions: value
            wrangles:
            - rename:
                functions: renamed
            """
        )
        assert df.columns.tolist() == ["renamed"]

    def test_rename_wrangles_columns_missing_error(self):
        """
        If user doesn't return a column named columns
        ensure an appropriate error is show
        """
        with pytest.raises(RuntimeError) as error:
            raise wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 5
                    values:
                        header1: value1
                        header2: value2
                wrangles:
                - rename:
                    wrangles:
                        - rename:
                            columns: cause_error
                """
            )
        assert "column named 'columns' must be returned" in error.value.args[0]

    def test_rename_wrangles_filtered_error(self):
        """
        When renaming, if the user changes the length of the output columns
        by wrangling then ensure an appropriate error is returned.
        """
        with pytest.raises(RuntimeError) as error:
            raise wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 5
                    values:
                        header1: value1
                        header2: value2
                wrangles:
                - rename:
                    wrangles:
                        - filter:
                            where: columns = 'header1'
                """
            )
        assert "same length as the input" in error.value.args[0]

    def test_rename_input_output_equal(self):
        """
        Rename using a single input to a single output where the input and output are the same
        """
        data = pd.DataFrame({
        'Manufacturer Name': ['Delos'],
        'Part Number': ['CH465517080'],
        })
        recipe = """
        wrangles:
            - rename:
                input: Manufacturer Name
                output: Manufacturer Name
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Manufacturer Name'] == 'Delos'

    def test_rename_dict_equal(self):
        """
        Rename using a dictionary of columns where the names are equal
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - rename:
                Manufacturer Name: Manufacturer Name
                Part Number: Part Number
            """,
            dataframe = pd.DataFrame({
                'Manufacturer Name': ['Delos'],
                'Part Number': ['CH465517080'],
            })
        )
        assert df.iloc[0]['Part Number'] == 'CH465517080'
    
    def test_rename_invert_names(self):
        """
        Test a rename that swaps two columns to each other's names
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    column1: value1
                    column2: value2
            wrangles:
              - rename:
                  column1: column2
                  column2: column1
            """
        )
        assert df["column1"][0] == "value2" and df["column2"][0] == "value1"

    def test_rename_dict_where(self):
        """
        Rename using a dictionary of columns with where
        """
        with pytest.raises(NotImplementedError, match="where"):
            wrangles.recipe.run(
                """
                wrangles:
                - rename:
                    Manufacturer Name: Company
                    Part Number: MPN
                    where: numbers > 5
                """,
                dataframe = pd.DataFrame({
                    'Manufacturer Name': ['Delos', 'Timken', 'SKF'],
                    'Part Number': ['CH465517080', 'BR549', '6202-f'],
                    'numbers': [4, 6, 8]
                })
            )

    def test_rename_wrangles_variables(self):
        """
        Use wrangles to rename columns based on a variable
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
                    header2: value2
            wrangles:
            - rename:
                wrangles:
                    - convert.case:
                        input: columns
                        case: ${case}
            """,
            variables={"case": "upper"}
        )
        assert df.columns.tolist() == ["HEADER1","HEADER2"]

    def test_rename_wrangles_variables_if(self):
        """
        Use wrangles to rename columns based on a variable with an if
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
                    header2: value2
            wrangles:
            - rename:
                variables:
                  condition: ${condition}
                wrangles:
                    - convert.case:
                        input: columns
                        case: upper
                        if: ${condition}
            """,
            variables={"condition": True}
        )
        assert df.columns.tolist() == ["HEADER1","HEADER2"]

    def test_rename_empty(self):
        """
        Test rename with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - rename:
                    Manufacturer Name: Company
                    Part Number: MPN
            """,
            dataframe=pd.DataFrame({
                'Manufacturer Name': [],
                'Part Number': [],
            })
        )
        assert df.empty and df.columns.tolist() == ['Company', 'MPN']


class TestSimilarity:
    """
    Test similarity

    (vector similarity - cosine, euclidean etc.)
    """
    def test_similarity_cosine(self):
        """
        Test cosine similarity of a 5 dimension vector using cosine similarity
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,5], [6,7,8,9,10]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: cosine
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Cos Sim'] != 1.0 and df.iloc[1]['Cos Sim'] == 1.0

    def test_similarity_cosine_1_D(self):
        """
        Test similarity of a 1 dimension vector/integer using cosine similarity
        """
        data = pd.DataFrame({
            'col1': [1, 9],
            'col2': [5, 9]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: cosine
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Cos Sim'] == 1.0 and df.iloc[1]['Cos Sim'] == 1.0

    def test_similarity_cosine_np_array(self):
        """
        Test similarity of a two numpy arrays
        """
        data = pd.DataFrame({
            'col1': [np.array([1,2,3,4,5]), np.array([6,7,8,9,10])],
            'col2': [np.array([5,4,3,2,1]), np.array([6,7,8,9,10])]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: cosine
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Cos Sim'] == 0.6363636363636364 and df.iloc[1]['Cos Sim'] == 1.0

    def test_similarity_cosine_different_size(self):
        """
        Test error when passing vectors of different dimension using cosine similarity
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4], [6,7,8,9]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: cosine
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'similarity - shapes (4,) and (5,) not aligned: 4 (dim 0) != 5 (dim 0)' in info.value.args[0]
        )

    def test_similarity_cosine_string(self):
        """
        Test error when passing an invalid data type (string) while using cosine similarity
        """
        data = pd.DataFrame({
            'col1': ['apple', 'orange'],
            'col2': ['orange', 'apple']
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: cosine
        """
        with pytest.raises(TypeError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'TypeError'
        )

    def test_similarity_euclidean(self):
        """
        Test cosine similarity of a 5 dimension vector using euclidean distance
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,5], [6,7,8,9,10]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Euc Sim
                method: euclidean
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Euc Sim'] == 6.324555320336759 and df.iloc[1]['Euc Sim'] == 0.0

    def test_similarity_euclidean_1_D(self):
        """
        Test similarity of a 1 dimension vector/integer using euclidean similarity
        """
        data = pd.DataFrame({
            'col1': [1, 9],
            'col2': [5, 9]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Euc Sim
                method: cosine
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Euc Sim'] == 1.0 and df.iloc[1]['Euc Sim'] == 1.0

    def test_similarity_euclidean_different_size(self):
        """
        Test error when passing vectors of different dimension using euclidean distance
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4], [6,7,8,9]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: euclidean
        """
        with pytest.raises(TypeError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'TypeError' and
            'exceptions must derive from BaseException' in info.value.args[0]
        )

    def test_similarity_euclidean_string(self):
        """
        Test error when passing an invalid data type (string) while using euclidean distance
        """
        data = pd.DataFrame({
            'col1': ['apple', 'orange'],
            'col2': ['orange', 'apple']
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: euclidean
        """
        with pytest.raises(TypeError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'TypeError'
        )

    def test_similarity_adjusted_cosine(self):
        """
        Test cosine similarity of a 5 dimension vector using adjusted cosine similarity
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,5], [6,7,8,9,10]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: adjusted cosine
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Cos Sim'] == 0.119 and df.iloc[1]['Cos Sim'] == 1.0

    def test_similarity_adjusted_cosine_min(self):
        """
        Ensure adjusted cosine does not go below 0
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,-5], [6,7,8,9,10]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: adjusted cosine
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Cos Sim'] == 0.0 and df.iloc[1]['Cos Sim'] == 1.0

    def test_similarity_adjusted_cosine_1_D(self):
        """
        Test similarity of a 1 dimension vector/integer using adjusted cosine similarity
        """
        data = pd.DataFrame({
            'col1': [1, 9],
            'col2': [5, 9]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: adjusted cosine
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Cos Sim'] == 1.0 and df.iloc[1]['Cos Sim'] == 1.0

    def test_similarity_adjusted_cosine_different_size(self):
        """
        Test error when passing vectors of different dimension using cosine similarity
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4], [6,7,8,9]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: adjusted cosine
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'similarity - shapes (4,) and (5,) not aligned: 4 (dim 0) != 5 (dim 0)' in info.value.args[0]
        )

    def test_similarity_adjusted_cosine_string(self):
        """
        Test error when passing an invalid data type (string) while using adjusted cosine
        """
        data = pd.DataFrame({
            'col1': ['apple', 'orange'],
            'col2': ['orange', 'apple']
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: adjusted cosine
        """
        with pytest.raises(TypeError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'TypeError'
        )

    def test_similarity_one_column(self):
        """
        Test similarity error when only passing one column
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,5], [6,7,8,9,10]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input: col1
                output: Cos Sim
                method: cosine
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and 
            'Input must consist of a list of two columns' in info.value.args[0]
        )

    def test_similarity_three_columns(self):
        """
        Test similarity error when passing three columns to input
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,5], [6,7,8,9,10]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]],
            'col3': [[4,5,6,7,8], [3,4,5,6,7]]
        })
        recipe = """
        wrangles:
            - similarity:
                input: 
                - col1
                - col2
                - col3
                output: Cos Sim
                method: cosine
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and 
            'Input must consist of a list of two columns' in info.value.args[0]
        )

    def test_similarity_invalid_method(self):
        """
        Test similarity error when passing the invalid method
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,5], [6,7,8,9,10]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10]]
        })
        recipe = """
        wrangles:
            - similarity:
                input: 
                - col1
                - col2
                output: Tan Sim
                method: tangent
        """
        with pytest.raises(TypeError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'TypeError' and 
            'Invalid method, must be "cosine", "adjusted cosine" or "euclidean"' in info.value.args[0]
        )

    def test_similarity_cosine_where(self):
        """
        Test cosine similarity with where
        """
        data = pd.DataFrame({
            'col1': [[1,2,3,4,5], [6,7,8,9,10], [2, 3, 4, 5, 6]],
            'col2': [[5,4,3,2,1], [6,7,8,9,10], [2, 9, 4, 5, 6]],
            'numbers': [4, 3, 2]
        })
        recipe = """
        wrangles:
            - similarity:
                input:
                - col1
                - col2
                output: Cos Sim
                method: cosine
                where: numbers < 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Cos Sim'] == '' and df.iloc[1]['Cos Sim'] == 1.0

    def test_similarity_empty(self):
        """
        Test similarity with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - similarity:
                    input:
                    - col1
                    - col2
                    output: Cos Sim
                    method: cosine
            """,
            dataframe=pd.DataFrame({
                'col1': [],
                'col2': [],
            })
        )
        assert df.empty and df.columns.to_list() == ['col1', 'col2', 'Cos Sim']


class TestStandardize:
    """
    Test standardize
    """
    def test_standardize_1(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP', 'ETA'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible'

    def test_standardize_2(self):
        """
        Missing ${ } in model_id
        """
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: wrong_model
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect model_id. May be missing "${ }" around value' in info.value.args[0]
        )

    def test_standardize_3(self):
        """
        Missing a character in model_id format
        """
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 6c4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX' in info.value.args[0]
        )

    def test_standardize_4(self):
        """
        Using an extract model with standardize function
        """
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 1eddb7e8-1b2b-4a52
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Using extract model_id 1eddb7e8-1b2b-4a52 in a standardize function.' in info.value.args[0]
        )

    def test_standardize_5(self):
        """
        Using classify model with standardize function
        """
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: a62c7480-500e-480c
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Using classify model_id a62c7480-500e-480c in a standardize function.' in info.value.args[0]
        )

    def test_standardize_where(self):
        """
        Test standardize function using a where clause
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - standardize:
                    input: Product
                    model_id: 6ca4ab44-8c66-40e8
                    where: Price > 10
            """,
            dataframe=pd.DataFrame({
                'Product': ['ASAP', 'ETA', 'omw'],
                'Price': [4.99, 9.99, 14.99]
            })
        )
        assert df['Product'].to_list() == ["ASAP", "ETA", "on my way"]

    def test_standardize_multi_input_single_output(self):
        """
        Test error using multiple input columns and only one output
        """
        data = pd.DataFrame({
        'Abbrev1': ['ASAP'],
        'Abbrev2': ['RSVP']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_standardize_multi_io_single_model(self):
        """
        Test output using multiple input and output columns with a single model_id
        """
        data = pd.DataFrame({
        'Abbrev1': ['ASAP'],
        'Abbrev2': ['ETA']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbreviations1
                - Abbreviations2
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations1'] == 'As Soon As Possible' and df.iloc[0]['Abbreviations2'] == 'Estimated Time of Arrival'

    def test_standardize_multi_io_single_model_where(self):
        """
        Test output using multiple input and output columns with a single model_id with a where filter
        """
        data = pd.DataFrame({
        'Abbrev1': ['FOMO', 'IDK', 'ASAP', 'ETA'],
        'Abbrev2': ['IDK', 'FOMO', 'ASAP', 'ETA']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbreviations1
                - Abbreviations2
                model_id: 6ca4ab44-8c66-40e8
                where: Abbrev1 LIKE Abbrev2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations1'] == "" and df.iloc[2]['Abbreviations1'] == 'As Soon As Possible'

    def test_standardize_case_sensitive(self):
        """
        Test standardize with case sensitivity
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'asap' and df.iloc[1]['Abbreviations'] == 'eta'

    def test_standardize_case_insensitive(self):
        """
        Test standardize with case insensitivity
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                case_sensitive: false
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible' and df.iloc[1]['Abbreviations'] == 'Estimated Time of Arrival'

    def test_standardize_case_default(self):
        """
        Test standardize with case default
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible' and df.iloc[1]['Abbreviations'] == 'Estimated Time of Arrival'

    def test_standardize_case_sensitive_multiple_rows(self):
        """
        Test standardize with case sensitive and multiple inputs and outputs
        """
        data = pd.DataFrame({
        'Abbrev1': ['asap'],
        'Abbrev2': ['eta']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbrev1 output
                - Abbrev2 output
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbrev1 output'] == 'asap' and df.iloc[0]['Abbrev2 output'] == 'eta'

    def test_standardize_case_sensitive_in_place(self):
        """
        Test standardize with case sensitive and no output
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta']
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbrev'] == 'asap' and df.iloc[1]['Abbrev'] == 'eta'

    def test_standardize_case_sensitive_invalid_bool(self):
        """
        Test standardize with case sensitive with an invalid boolean
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta']
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: output
                case_sensitive: Huh?
                model_id: 6ca4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Non-boolean parameter in caseSensitive. Use True/False' in info.value.args[0]
        )

    def test_standardize_case_sensitive_multi_model(self):
        """
        Test standardize with case sensitive with multiple models
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta', 'IDK', 'OMW'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: output
                case_sensitive: true
                model_id: 
                - fc7d46e3-057f-47bd
                - 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'asap' and df.iloc[3]['output'] == 'OMW'

    def test_standardize_case_insensitive_multi_model(self):
        """
        Test standardize with case insensitive with multiple models
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta', 'IDK', 'OMW'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: output
                case_sensitive: false
                model_id: 
                - fc7d46e3-057f-47bd
                - 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'As Soon As Possible' and df.iloc[3]['output'] == 'on my way'

    def test_standardize_empty(self):
        """
        Test standardize with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - standardize:
                    input: Abbrev
                    output: Abbreviations
                    model_id: 6ca4ab44-8c66-40e8
            """,
            dataframe=pd.DataFrame({
                'Abbrev': [],
            })
        )
        assert df.empty and df.columns.to_list() == ['Abbrev', 'Abbreviations']


class TestReplace:
    """
    Test replace
    """
    def test_replace(self):
        """
        Test replace
        """
        data = pd.DataFrame({
        'Abbrev': ['random ASAP random', 'random ETA random'],
        })
        recipe = """
        wrangles:
            - replace:
                input: Abbrev
                output: Abbreviations
                find: ETA
                replace: Estimated Time of Arrival
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Abbreviations'] == 'random Estimated Time of Arrival random'

    def test_replace_lists(self):
        """
        Test replace with a list for input and output
        """
        data = pd.DataFrame({
            'Abbrev1': ['random ETA random'],
            'Abbrev2': ['another ETA another']
        })
        recipe = """
        wrangles:
            - replace:
                input:
                - Abbrev1
                - Abbrev2
                output:
                - Abbreviations1
                - Abbreviations2
                find: ETA
                replace: Estimated Time of Arrival
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert (
            df.iloc[0]['Abbreviations1'] == 'random Estimated Time of Arrival random' and
            df.iloc[0]['Abbreviations2'] == 'another Estimated Time of Arrival another'
        )

    def test_replace_regex(self):
        """
        Test replace using a regex pattern
        """
        data = pd.DataFrame({
            'Abbrev': ['random 123 random'],
        })
        recipe = """
        wrangles:
            - replace:
                input: Abbrev
                output: Abbreviations
                find: "[0-9]+"
                replace: found
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'random found random'

    def test_replace_where(self):
        """
        Test replace using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - replace:
                    input: Abbrev
                    find: ETA
                    replace: Estimated Time of Arrival
                    where: numbers > 1
            """,
            dataframe=pd.DataFrame({
            'Abbrev': ['random ETA random', 'random ETA random'],
            'numbers': [1, 2]
            })
        )
        assert df['Abbrev'].to_list() == ["random ETA random", 'random Estimated Time of Arrival random']

    def test_replace_inconsistent_input(self):
        """
        Check error when the lists for input and output are inconsistent
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(
                """
                wrangles:
                - replace:
                    input:
                        - Abbrev1
                    output:
                        - Abbreviations1
                        - Abbreviations2
                    find: ETA
                    replace: Estimated Time of Arrival
                """,
                dataframe = pd.DataFrame({
                    'Abbrev1': ['random ETA random'],
                    'Abbrev2': ['another ETA another']
                })
            )
        assert (
            info.typename == 'ValueError' and
            'The lists for' in info.value.args[0]
        )

    def test_replace_integer(self):
        """
        Test replace with integers
        """
        data = pd.DataFrame({
        'numbers': [555, 252, 355]
        })
        recipe = """
        wrangles:
            - replace:
                input: numbers
                output: replaced numbers
                find: 5
                replace: 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['replaced numbers'] == '222'

    def test_replace_integer_with_string(self):
        """
        Test replacing integers with strings
        """
        data = pd.DataFrame({
        'numbers': [555, 252, 355]
        })
        recipe = """
        wrangles:
            - replace:
                input: numbers
                output: replaced numbers
                find: 5
                replace: five
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['replaced numbers'] == 'fivefivefive'

    def test_replace_string_with_integer(self):
        """
        Test replacing a string with an integer
        """
        data = pd.DataFrame({
        'numbers': ['five', 'fifty-five']
        })
        recipe = """
        wrangles:
            - replace:
                input: numbers
                output: replaced numbers
                find: five
                replace: 5
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['replaced numbers'] == 'fifty-5'

    def test_replace_empty(self):
        """
        Test replace with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - replace:
                    input: Abbrev
                    output: output column
                    find: ETA
                    replace: Estimated Time of Arrival
            """,
            dataframe=pd.DataFrame({
                'Abbrev': [],
            })
        )
        assert df.empty and df.columns.to_list() == ['Abbrev', 'output column']

    def test_replace_list(self):
        """
        Test replace with a list for the input
        """
        data = pd.DataFrame({
        'List': [['random ASAP random', 'random ETA random']],
        })
        recipe = """
        wrangles:
            - replace:
                input: List
                output: Still a List
                find: ETA
                replace: Estimated Time of Arrival
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Still a List'] == ['random ASAP random', 'random ETA random'] and isinstance(df.iloc[0]['Still a List'], list) == True

    def test_replace_bool(self):
        """
        Test replace with a boolean for the input
        """
        data = pd.DataFrame({
        'Bool': [True, False],
        })
        recipe = """
        wrangles:
            - replace:
                input: Bool
                output: Not a Bool
                find: False
                replace: This is so True, there has never ever been anything more True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Not a Bool'] == 'This is so True, there has never ever been anything more True' and isinstance(df.iloc[0]['Not a Bool'], str) == True

    def test_replace_integer(self):
        """
        Test replace with an integer for the input
        """
        data = pd.DataFrame({
        'Integers': [10, 20],
        })
        recipe = """
        wrangles:
            - replace:
                input: Integers
                output: Not Integers
                find: 0
                replace: 9
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Not Integers'] == '29' and isinstance(df.iloc[0]['Not Integers'], str) == True

    def test_replace_dict(self):
        """
        Test replace with a dictionary for the input
        """
        data = pd.DataFrame({
        'Dictionaries': [{'This': 'is a dictionary'}, {'So': 'is this'}],
        })
        recipe = """
        wrangles:
            - replace:
                input: Dictionaries
                output: Not Dictionaries
                find: Doesn't Matter
                replace: That's true, it doesn't
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Not Dictionaries'] == {'So': 'is this'} and isinstance(df.iloc[0]['Not Dictionaries'], dict) == True


class TestTranslate:
    """
    Test translate
    """
    def test_translate_1(self):
        data = pd.DataFrame({
        'Español': ['¡Hola Mundo!'],
        })
        recipe = """
        wrangles:
            - translate:
                input: Español
                output: English
                source_language: ES
                target_language: EN-GB
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['English'] == 'Hello World!'

    def test_translate_2(self):
        """
        Using full language names
        """
        data = pd.DataFrame({
        'Español': ['¡Hola Mundo!'],
        })
        recipe = """
        wrangles:
            - translate:
                input: Español
                output: English
                source_language: Spanish
                target_language: English
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['English'] == 'Hello World!'

    def test_translate_3(self):
        """
        If the input is multiple columns (a list)
        """
        data = pd.DataFrame({
        'Español': ['¡Hola Mundo!'],
        'Español2': ['¡Hola Mundo Dos!'],
        })
        recipe = """
        wrangles:
            - translate:
                input:
                - Español
                - Español2
                output:
                - English
                - English2
                source_language: Spanish
                target_language: English
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['English2'] == 'Hello World Two!'

    def test_translate_4(self):
        """
        If the input and output are not the same
        """
        data = pd.DataFrame({
        'Español': ['¡Hola Mundo!'],
        'Español2': ['¡Hola Mundo Dos!'],
        })
        recipe = """
        wrangles:
            - translate:
                input:
                - Español
                - Español2
                output: English
                source_language: Spanish
                target_language: English
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            "The lists for" in info.value.args[0]
        )
        
    def test_translate_where(self):
        """
        Test translate using where
        """
        data = pd.DataFrame({
        'Español': ['¡Hola Mundo!', 'Me llamo es Johnny Numero Cinco'],
        'numbers': [3, 88]
        })
        recipe = """
        wrangles:
            - translate:
                input: Español
                output: English
                source_language: Spanish
                target_language: English
                where: numbers > 70
        """
        df =  wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['English'] == "" and df.iloc[1]['English'] == 'My name is Johnny Number Five'

    def test_translate_empty(self):
        """
        Test translate with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - translate:
                    input: Español
                    output: English
                    source_language: Spanish
                    target_language: English
            """,
            dataframe=pd.DataFrame({
                'Español': [],
            })
        )
        assert df.empty and df.columns.to_list() == ['Español', 'English']


class TestMath:
    """
    Test math
    """
    def test_maths_1(self):
        """
        Regular use
        """
        data = pd.DataFrame({
            'col1': [1, 1, 1],
            'col2': [2, 2, 2]
        })
        recipe = """
        wrangles:
        - maths:
            input: col1 + col2
            output: result
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['result'] == 3

    def test_maths_column_spaces(self):
        data = pd.DataFrame({
            'col 1': [1, 1, 1],
            'col 2': [2, 2, 2]
        })
        recipe = """
        wrangles:
        - math:
            input: col_1 + col_2
            output: result
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['result'] == 3

    def test_math_1(self):
        """
        US spelling of maths
        """
        data = pd.DataFrame({
            'col1': [1, 1, 1],
            'col2': [2, 2, 2]
        })
        recipe = """
        wrangles:
        - math:
            input: col1 + col2
            output: result
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['result'] == 3
        
    def test_math_where(self):
        """
        Test math using where
        """
        data = pd.DataFrame({
            'col1': [5, 9, 12],
            'col2': [5, 3, 2]
        })
        recipe = """
        wrangles:
        - math:
            input: col1 + col2
            output: result
            where: col1 + col2 > 12
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['result'] == "" and df.iloc[2]['result'] == 14.0

    def test_math_column_spaces(self):
        data = pd.DataFrame({
            'col 1': [1, 1, 1],
            'col 2': [2, 2, 2]
        })
        recipe = """
        wrangles:
        - math:
            input: col_1 + col_2
            output: result
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['result'] == 3

    def test_math_empty(self):
        """
        Test math with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - math:
                    input: col1 + col2
                    output: result
            """,
            dataframe=pd.DataFrame({
                'col1': [],
                'col2': [],
            })
        )
        assert df.empty and df.columns.to_list() == ['col1', 'col2', 'result']


class TestSQL:
    """
    Test sql
    """
    def test_sql_1(self):
        """
        Regular use
        """
        data = pd.DataFrame({
            'header1': [1, 2, 3],
            'header2': ['a', 'b', 'c'],
            'header3': ['x', 'y', 'z'],
        })
        recipe = """
        wrangles:
        - sql:
            command: |
                SELECT header1, header2
                FROM df
                WHERE header1 >= 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['header1'] == 2

    # Using an incorrect sql statement
    def test_sql_2(self):
        data = pd.DataFrame({
            'header1': [1, 2, 3],
            'header2': ['a', 'b', 'c'],
            'header3': ['x', 'y', 'z'],
        })
        recipe = """
        wrangles:
        - sql:
            command: |
                CREATE TABLE header1
                FROM df
                WHERE header1 >= 2
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Only SELECT statements are supported for sql wrangles' in info.value.args[0]
        )

    def test_sql_mixed_objects(self):
        """
        Test SQL with a column that contains a mixture of objects and scalars
        """
        with pytest.raises(ValueError, match="mixed data"):
            wrangles.recipe.run(
                """
                wrangles:
                - sql:
                    command: |
                        SELECT *
                        FROM df
                        WHERE header1 >= 3
                """,
                dataframe=pd.DataFrame({
                    'header1': [1, 2, 3],
                    'header2': ['a', 'b', 'c'],
                    'header3': ['x', 'y', {"Object": "z"}],
                })
            )

    def test_sql_params(self):
        """
        Test sql using params
        """
        data = pd.DataFrame({
            'header1': [1, 2, 3],
            'header2': ['a', 'b', 'c'],
            'header3': ['x', 'y', 'z'],
        })
        recipe = """
        wrangles:
        - sql:
            command: |
                SELECT header1, header2
                FROM df
                WHERE header1 >= ($number)
            params: 
                number: 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['header1'] == 2

    def test_sql_objects(self):
        """
        Test SQL with a column that contains a mixture of objects and scalars
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - sql:
                command: |
                    SELECT *
                    FROM df
                    WHERE header1 >= 3
            """,
            dataframe=pd.DataFrame({
                'header1': [1, 2, 3],
                'header2': [['a'], ['b'], ['c']],
                'header3': [{"Object": "x"}, {"Object": "y"}, {"Object": "z"}],
            })
        )
        assert (
            df.columns.tolist() == ['header1', 'header2', 'header3'] and
            df['header1'][0] == 3 and
            df['header2'][0] == ['c'] and
            df['header3'][0] == {"Object": "z"}
        )

    def test_sql_where(self):
        """
        Test sql with a where
        """
        data = pd.DataFrame({
            'header1': [1, 2, 3],
            'header2': ['a', 'b', 'c'],
            'header3': ['x', 'y', 'z'],
        })
        recipe = """
        wrangles:
        - sql:
            command: |
                SELECT header1, header2
                FROM df
            where: header1 >= 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['header1'] == 2

    def test_sql_empty(self):
        """
        Test sql with empty data
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - sql:
                    command: |
                        SELECT header1
                        FROM df
            """,
            dataframe=pd.DataFrame({
                'header1': [],
                'header2': [],
            })
        )
        assert df.empty and df.columns.to_list() == ['header1']


class TestRecipe:
    """
    Test recipe

    Using a recipe as a wrangle. Recipe-ception
    """
    def test_recipe_wrangle_1(self):
        data = pd.DataFrame({
            'col': ['Mario', 'Luigi']
        })
        recipe = """
        wrangles:
        - recipe:
            name: 'tests/samples/recipe_ception.wrgl.yaml'
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['col'].iloc[0] == 'MARIO'

    def test_recipe_wrangle_where(self):
        """
        Test a recipe wrangle using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - recipe:
                name: 'tests/samples/recipe_ception.wrgl.yaml'
                where: numbers > 4
            """,
            dataframe=pd.DataFrame({
                'col': ['Mario', 'Luigi', 'Peach', 'Toadstool'],
                'numbers': [3, 4, 5, 6]
            })
        )
        assert df['col'].to_list() == ['Mario', 'Luigi', 'PEACH', 'TOADSTOOL']

    def test_recipe_wrangle(self):
        data = pd.DataFrame({
            'col': ['Mario', 'Luigi']
        })
        recipe = """
        wrangles:
        - recipe:
            name: 'tests/samples/recipe_ception.wrgl.yaml'
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['col'].iloc[0] == 'MARIO'

    def test_recipe_input(self):
        """
        Test using a recipe as a wrangle with defined input
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header1: value1
                    header2: value2
            wrangles:
              - recipe:
                  input: header1
                  wrangles:
                    - convert.case:
                        input: "*"
                        case: upper
            """
        )
        assert df['header1'][0] == 'VALUE1' and df['header2'][0] == 'value2'

    def test_recipe_output(self):
        """
        Test using a recipe as a wrangle
        that specifies an output
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header1: value1
                    header2: value2
            wrangles:
              - recipe:
                  output: header1
                  wrangles:
                    - convert.case:
                        input: "*"
                        case: upper
            """
        )
        assert df['header1'][0] == 'VALUE1' and df['header2'][0] == 'value2'

    def test_recipe_where(self):
        """
        Test using a recipe as a wrangle
        that specifies an output
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - recipe:
                  where: header1 = 'b'
                  wrangles:
                    - convert.case:
                        input: "*"
                        case: upper
            """,
            dataframe=pd.DataFrame({
                'header1': ['a', 'b'],
                'header2': ['value1', 'value2']
            })
        )
        assert df.values.tolist() == [['a', 'value1'], ['B', 'VALUE2']]

class TestDateCalculator:
    """
    Test date_calculator
    """
    def test_date_calc_1(self):
        """
        Add time (default)
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - date_calculator:
                input: date1
                output: out1
                time_unit: days
                time_value: 6
            """,
            dataframe = pd.DataFrame({
                'date1': ['12/25/2022'],
            })
        )
        assert df.iloc[0]['out1']._date_repr == '2022-12-31'

    def test_date_calc_2(self):
        """
        Subtract time
        """
        data = pd.DataFrame({
            'date1': ['12/25/2022'],
        })
        recipe = """
        wrangles:
        - date_calculator:
            input: date1
            output: out1
            operation: subtract
            time_unit: days
            time_value: 1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1']._date_repr == '2022-12-24'

    def test_date_calc_3(self):
        """
        Invalid operation
        """
        data = pd.DataFrame({
            'date1': ['12/25/2022'],
        })
        recipe = """
        wrangles:
        - date_calculator:
            input: date1
            output: out1
            operation: matrix-multiplication
            time_unit: days
            time_value: 6
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)

        assert (
            info.typename == 'ValueError' and
            '"matrix-multiplication" is not a valid operation. Available operations: "add", "subtract"' in info.value.args[0]
        )

    def test_date_calc_inconsistent_input(self):
        """
        Check error if input and output provided aren't consistent lengths
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(
                """
                wrangles:
                - date_calculator:
                    input:
                    - date1
                    output:
                    - out1
                    - out2
                    operation: subtract
                    time_unit: days
                    time_value: 1
                """,
                dataframe = pd.DataFrame({
                    'date1': ['12/25/2022'],
                })
            )
        assert (
            info.typename == 'ValueError' and
            'The lists for' in info.value.args[0]
        )

    def test_date_calc_multi_io(self):
        """
        Check output when ran with multiple input and output columns
        """
        recipe = """
        wrangles:
        - date_calculator:
            input:
                - date1
                - date2
            output:
                - out1
                - out2
            operation: subtract
            time_unit: days
            time_value: 5
        """
        data = pd.DataFrame({
                    'date1': ['12/25/2022'],
                    'date2': ['7/4/2023']
                })
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1']._date_repr == '2022-12-20' and df.iloc[0]['out2']._date_repr == '2023-06-29'

    def test_date_calc_where(self):
        data = pd.DataFrame({
            'date1': ['12/25/2022', '12/31/2022'],
            'number': [6, 12]
        })
        recipe = """
        wrangles:
        - date_calculator:
            input: date1
            output: out1
            operation: subtract
            time_unit: days
            time_value: 1
            where: number > 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1'] == '0' and df.iloc[1]['out1']._date_repr == '2022-12-30'


class TestPython:
    """
    Test Python Wrangle
    """
    def test_python(self):
        """
        Test a simple python command
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: a
                    header2: b
            wrangles:
            - python:
                command: header1 + " " + header2
                output: result
            """
        )
        assert df["result"][0] == "a b"

    def test_python_list_comprehension(self):
        """
        Test a python list comprehension
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: '["a","b","c"]'
                    header2: '["1","2","3"]'
            wrangles:
            - convert.from_json:
                input:
                    - header1
                    - header2
            - python:
                command: |
                    [
                    x + " " + y
                    for x, y in zip(header1, header2)
                    ]
                output: result
            - convert.to_json:
                input: result
            """
        )
        assert df["result"][0] == '["a 1", "b 2", "c 3"]'

    def test_python_column_with_space(self):
        """
        Test a simple python command
        where a column name includes a space
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header 1: a
                    header 2: b
            wrangles:
            - python:
                command: header_1 + " " + header_2
                output: result
            """
        )
        assert df["result"][0] == "a b"

    def test_python_kwargs(self):
        """
        Test kwargs dict
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: a
                    header2: b
            wrangles:
            - python:
                command: kwargs
                output: result
            - convert.to_json:
                input: result
            """
        )
        assert df["result"][0] == '{"header1": "a", "header2": "b"}'

    def test_python_input(self):
        """
        Test using input to filter columns
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: a
                    header2: b
                    header3: c
            wrangles:
            - python:
                command: kwargs
                input:
                    - header1
                    - header2
                output: result
            - convert.to_json:
                input: result
            """
        )
        assert df["result"][0] == '{"header1": "a", "header2": "b"}'

    def test_python_input_wildcard(self):
        """
        Test using input to filter columns with a wildcard
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: a
                    header2: b
                    not_this: c
            wrangles:
            - python:
                command: kwargs
                input: header*
                output: result
            - convert.to_json:
                input: result
            """
        )
        assert df["result"][0] == '{"header1": "a", "header2": "b"}'

    def test_python_multiple_output(self):
        """
        Test providing multiple outputs
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: a
                    header2: b
            wrangles:
            - python:
                command: kwargs.values()
                output:
                    - result1
                    - result2
            """
        )
        assert df["result1"][0] == "a" and df["result2"][0] == "b"

    def test_python_params(self):
        """
        Test a simple python command
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: a
                    header2: b
            wrangles:
            - python:
                command: header1 + " " + my_param
                output: result
                my_param: my_value
            """
        )
        assert df["result"][0] == "a my_value"

    def test_python_kwargs_scope(self):
        """
        Test to ensure variables
        are correctly declared in scope
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header1: value1
                    header2: value2

            wrangles:
            - python:
                output: test
                command: |-
                    {
                    k: kwargs[k]
                    for k in ["header1"]
                    }
            """
        )
        assert df["test"][0]["header1"] == "value1"

    def test_python_special_characters(self):
        """
        Test to ensure that invalid python variable
        characters are correctly handled by replacing
        with underscores
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header 1: a
                    header (2): b

            wrangles:
            - python:
                output: test
                command: header_1 + header__2_
            """
        )
        assert df["test"][0] == "ab"

    def test_python_special_characters_parameterized(self):
        """
        Test to ensure that special characters are
        correctly handled when passed as parameters
        using kwargs
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header 1: a
                    'header "2"': b

            wrangles:
            - python:
                output: test
                command: header_1 + kwargs[h2]
                h2: 'header "2"'
            """
        )
        assert df["test"][0] == "ab"

    def test_python_no_except(self):
        """
        Test that an exception is raised if no except is provided
        """
        with pytest.raises(SyntaxError):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 5
                    values:
                        header 1: a
                wrangles:
                  - python:
                      command: this should error
                      output: result
                """
            )

    def test_python_except(self):
        """
        Test to ensure that an exception is caught
        and the appropraite value is returned instead
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header 1: a
            wrangles:
              - python:
                  command: this should error
                  output: result
                  except: error
            """
        )
        assert df["result"][0] == "error"

    def test_python_except_array(self):
        """
        Test that an array is returned correctly
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header 1: a
            wrangles:
              - python:
                  command: this should error
                  output: result
                  except:
                    - error1
                    - error2
            """
        )
        assert df["result"][0] == ["error1","error2"]

    def test_python_except_multiple_outputs(self):
        """
        Test that an array is returned correctly
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    header 1: a
            wrangles:
              - python:
                  command: this should error
                  output:
                    - result1
                    - result2
                  except:
                    - error1
                    - error2
            """
        )
        assert df["result1"][0] == "error1" and df["result2"][0] == "error2"

    def test_python_where(self):
        """
        Test a simple python command with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - python:
                command: header1 + " " + header2
                output: result
                where: numbers = 6
            """,
            dataframe=pd.DataFrame({
                'header1': ['a', 'c', 'z'],
                'header2': ['b', 'd', 'p'],
                'numbers': [1, 2, 6]
            })
        )
        assert df["result"][0] == '' and df['result'][2] == 'z p'


class TestAccordion:
    """
    Test accordion

    Apply a series of wrangles
    to lists within a column
    """
    def test_accordion(self):
        """
        Test a basic accordion that overwrites the input column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - convert.case:
                        input: list_column
                        case: upper
            """
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["A","B","C"]
        )

    def test_accordion_json(self):
        """
        Test that accordion works even if
        the input is a json string
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column: '["a","b","c"]'

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - convert.case:
                        input: list_column
                        case: upper
            """
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["A","B","C"]
        )

    def test_accordion_order(self):
        """
        Test a basic accordion that overwrites the input column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c
                    other_column: a

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - convert.case:
                        input: list_column
                        case: upper
            """
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["A","B","C"] and
            df.columns.to_list() == ["list_column","other_column"]
        )

    def test_accordion_new_output(self):
        """
        Test an accordion that creates a new output column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c

            wrangles:
            - accordion:
                input: list_column
                output: list_column_out
                wrangles:
                    - convert.case:
                        input: list_column
                        output: list_column_out
                        case: upper
            """
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["a","b","c"] and
            df["list_column_out"][0] == ["A","B","C"]
        )

    def test_accordion_two_columns(self):
        """
        Test an accordion that modifies two columns
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column_1:
                    - a
                    - b
                    - c
                    list_column_2:
                    - d
                    - e
                    - f

            wrangles:
            - accordion:
                input:
                    - list_column_1
                    - list_column_2
                wrangles:
                    - convert.case:
                        input:
                        - list_column_1
                        - list_column_2
                        case: upper
            """
        )
        assert (
            len(df) == 5 and
            df["list_column_1"][0] == ["A","B","C"] and
            df["list_column_2"][0] == ["D","E","F"]
        )

    def test_accordion_wildcard(self):
        """
        Test an accordion that uses a wildcard
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column_1:
                    - a
                    - b
                    - c
                    list_column_2:
                    - d
                    - e
                    - f

            wrangles:
            - accordion:
                input:
                    - list_column_*
                wrangles:
                    - convert.case:
                        input:
                        - list_column_*
                        case: upper
            """
        )
        assert (
            len(df) == 5 and
            df["list_column_1"][0] == ["A","B","C"] and
            df["list_column_2"][0] == ["D","E","F"]
        )

    def test_accordion_extended_length(self):
        """
        Test an accordion with a wrangle that extends the
        length of the column to be different from the input column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c

            wrangles:
            - accordion:
                input: list_column
                output: final_column
                wrangles:
                    - create.column:
                        output: new_column
                        value:
                        - y
                        - z
                    - explode:
                        input: new_column
                    - merge.concatenate:
                        input:
                        - list_column
                        - new_column
                        output: final_column
                        char: ""
            """
        )
        assert (
            len(df) == 5 and
            df["final_column"][0] == ["ay","az","by","bz","cy","cz"]
        )

    def test_accordion_reduce_length(self):
        """
        Test an accordion with a wrangle that reduces the
        length of the column to be different from the input column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - filter:
                        input: list_column
                        equal: a
            """
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["a"]
        )

    def test_accordion_filter_all(self):
        """
        Test an accordion with a wrangle that removes
        all of the elements from a list
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - ["a","b","c"]
                    - ["x","y","z"]

            wrangles:
            - explode:
                input: list_column
            - accordion:
                input: list_column
                wrangles:
                    - filter:
                        input: list_column
                        equal: z
            """
        )
        assert (
            len(df) == 10 and
            df["list_column"][0] == [] and
            df["list_column"][1] == ["z"]
        )

    def test_accordion_propagate_one_column(self):
        """
        Test an accordion that passes through
        non-list columns for use by the wrangles
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c
                    scalar_column: z

            wrangles:
            - accordion:
                input:
                    - list_column
                output: final_column
                wrangles:
                    - merge.concatenate:
                        input:
                        - list_column
                        - scalar_column
                        output: final_column
                        char: ""
            """
        )
        assert (
            len(df) == 5 and
            df["final_column"][0] == ["az","bz","cz"]
        )

    def test_accordion_propagate_two_columns(self):
        """
        Test an accordion that passes through
        non-list columns for use by the wrangles
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c
                    scalar_column_1: y
                    scalar_column_2: z

            wrangles:
            - accordion:
                input:
                    - list_column
                output: final_column
                wrangles:
                    - merge.concatenate:
                        input:
                        - list_column
                        - scalar_column_1
                        - scalar_column_2
                        output: final_column
                        char: ""
            """
        )
        assert (
            len(df) == 5 and
            df["final_column"][0] == ["ayz","byz","cyz"]
        )

    def test_accordion_custom_function(self):
        """
        Test an accordion passed through custom functions correctly
        """
        def test_fn(list_column):
            return list_column.upper()

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - custom.test_fn:
                        output: list_column
            """,
            functions=test_fn
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["A","B","C"]
        )

    def test_recursive_accordion(self):
        """
        Test an accordion that contains another accordion
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - [a, b, c]
                    - [d, e, f]
                    - [g, h, i]

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - accordion:
                        input: list_column
                        wrangles:
                        - convert.case:
                            input: list_column
                            case: upper
            """
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == [["A","B","C"],["D","E","F"],["G","H","I"]]
        )

    def test_accordion_invalid_wrangles_column(self):
        """
        Test for a clear error if it looks like the user hasn't
        passed the correct column to the wrangles
        """
        with pytest.raises(KeyError) as err:
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 5
                    values:
                        list_column:
                        - a
                        - b
                        - c

                wrangles:
                - accordion:
                    input: list_column
                    wrangles:
                        - convert.case:
                            input: list_column_1
                            case: upper
                """
            )
        assert (
            err.typename == 'KeyError' and
            'accordion - "Did you forget' in err.value.args[0]
        )

    def test_accordion_invalid_wrangles_column_output(self):
        """
        Test for a clear error if it looks like the user hasn't
        passed the correct column output from the wrangles
        """
        with pytest.raises(KeyError) as err:
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 5
                    values:
                        list_column:
                        - a
                        - b
                        - c

                wrangles:
                - accordion:
                    input: list_column
                    wrangles:
                        - convert.case:
                            input: list_column
                            output: list_column_out
                            case: upper
                        - drop:
                            columns: list_column
                """
            )
        assert (
            err.typename == 'KeyError' and
            "accordion - \'Did you forget" in err.value.args[0]
        )

    def test_accordion_inconsistent_lengths(self):
        """
        Test for a clear error if the user passes in lists
        that are not consistent lengths
        """
        with pytest.raises(ValueError) as err:
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 5
                    values:
                      list_column_1:
                        - a
                        - b
                        - c
                      list_column_2:
                        - y
                        - z

                wrangles:
                - accordion:
                    input:
                    - list_column_1
                    - list_column_2
                    wrangles:
                      - convert.case:
                          input: list_column_1
                          case: upper
                """
            )
        assert (
            err.typename == 'ValueError' and
            'matching element counts' in err.value.args[0]
        )

    def test_accordion_propagate_invalid(self):
        """
        Test that a clear error is raised if the user tries to
        use a column that isn't propgated
        """
        with pytest.raises(KeyError) as err:
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 5
                    values:
                      list_column:
                        - a
                        - b
                        - c
                      scalar_value_1: x
                      scalar_value_2: y

                wrangles:
                - accordion:
                    input: list_column
                    propagate: scalar_value_1
                    wrangles:
                        - merge.concatenate:
                            input:
                            - list_column
                            - scalar_value_1
                            - scalar_value_2
                            output: final_column
                            char: ""
                """
            )
        assert (
            err.typename == 'KeyError' and
            'accordion - "Did you forget' in err.value.args[0]
        )

    def test_accordion_empty_list(self):
        """
        Test that an accordion preserves rows with empty lists
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - convert.case:
                        input: list_column
                        case: upper
            """,
            dataframe=pd.DataFrame({
                "list_column": [["a","b","c"], []]
            })
        )
        assert df["list_column"][0] == ["A","B","C"]
        assert df["list_column"][1] == []

    def test_accordion_where(self):
        """
        Test an accordion with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - accordion:
                input: list_column
                where: numbers = 1
                wrangles:
                    - convert.case:
                        input: list_column
                        case: upper
            """,
            dataframe=pd.DataFrame({
                "list_column": [["a","b","c"], ["e","f","g"], ["h","i","j"]],
                "numbers": [1, 2, 3]
            })
        )
        assert df["list_column"][0] == ["A","B","C"] and df["list_column"][1] == ["e","f","g"]

    def test_accordion_variables(self):
        """
        Test an accordion with a variable passed through
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - convert.case:
                        input: list_column
                        case: ${case}
            """,
            variables={"case": "upper"}
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["A","B","C"]
        )

    def test_accordion_variables_if(self):
        """
        Test an accordion with a variable passed through to an if
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    list_column:
                    - a
                    - b
                    - c

            wrangles:
            - accordion:
                input: list_column
                wrangles:
                    - convert.case:
                        input: list_column
                        case: upper
                        if: ${condition}
            """,
            variables={"condition": True}
        )
        assert (
            len(df) == 5 and
            df["list_column"][0] == ["A","B","C"]
        )


class TestBatch:
    """
    Test batch wrangle
    This splits the dataframe into batches
    and executes a series of wrangles against each
    """
    def test_batch(self):
        """
        Test basic batch wrangle
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                    column: a
            wrangles:
              - batch:
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
            """
        )
        assert df['column'].tolist() == ["A"] * 1000

    def test_batch_size(self):
        """
        Test batch size parameter works correctly
        """
        number_of_batches = [0]
        def record_batch(df):
            number_of_batches[0] += 1
            return df

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                    column: a
            wrangles:
              - batch:
                  batch_size: 200
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
                    - custom.record_batch: {}
            """,
            functions=record_batch
        )
        assert (
            df['column'].tolist() == ["A"] * 1000 and
            number_of_batches[0] == 5
        )

    def test_batch_size_one(self):
        """
        Test batch size parameter works correctly
        with a batch size as 1
        """
        number_of_batches = [0]
        def record_batch(df):
            number_of_batches[0] += 1
            return df

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                    column: a
            wrangles:
              - batch:
                  batch_size: 1
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
                    - custom.record_batch: {}
            """,
            functions=record_batch
        )
        assert (
            df['column'].tolist() == ["A"] * 1000 and
            number_of_batches[0] == 1000
        )

    def test_batch_preserves_order(self):
        """
        Test batch preserves
        the order of the input
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                    column: a
            wrangles:
              - create.index:
                  output: idx
              - batch:
                  batch_size: 10
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
            """
        )
        assert (
            df['column'].tolist() == ["A"] * 1000 and
            df['idx'].tolist() == list(range(1, 1001))
        )

    def test_batch_not_exactly_divisible(self):
        """
        Test batch what the total number of rows
        leaves a remainder vs the batch size
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                    column: a
            wrangles:
              - create.index:
                  output: idx
              - batch:
                  batch_size: 220
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
            """
        )
        assert (
            df['column'].tolist() == ["A"] * 1000 and
            df['idx'].tolist() == list(range(1, 1001))
        )

    def test_batch_smaller_than_batch_size(self):
        """
        Test that batch works correctly if the batch
        size exceeds the length of the dataframe
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 10
                values:
                    column: a
            wrangles:
              - batch:
                  batch_size: 20
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
            """
        )
        assert df['column'].tolist() == ["A"] * 10

    def test_batch_threads(self):
        """
        Test a batch with threads > 5
        Ensure results order is maintained
        """
        start_time = datetime.now()

        def sleep(duration):
            time.sleep(duration)
            return "A"

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 25
                values:
                    column: a
            wrangles:
              - create.index:
                  output: idx
              - batch:
                  batch_size: 5
                  threads: 5
                  wrangles:
                    - custom.sleep:
                        output: column
                        duration: 1
            """,
            functions=sleep
        )
        end_time = datetime.now()
        assert (
            (end_time - start_time).seconds == 5 and
            df['column'].tolist() == ["A"] * 25 and
            df['idx'].tolist() == list(range(1, 26))
        )

    def test_batch_non_sequential_index(self):
        """
        Test that a non-sequential index is batched correctly
        """
        number_of_batches = [0]
        def record_batch(df):
            number_of_batches[0] += 1
            return df

        df = wrangles.recipe.run(
            """
            wrangles:
              - batch:
                  batch_size: 5
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
                    - custom.record_batch: {}
            """,
            functions=record_batch,
            dataframe=pd.DataFrame(
                data= {'column':['a'] * 15},
                index= [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600]
            )
        )
        assert (
            list(df.index) == [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600] and
            df['column'].tolist() == ["A"] * 15 and
            number_of_batches[0] == 3
        )

    def test_batch_error(self):
        """
        Test that an error is raised correctly
        """
        with pytest.raises(KeyError, match="column1 does not exist"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1000
                    values:
                        column: a
                wrangles:
                - batch:
                    wrangles:
                        - convert.case:
                            input: column1
                            case: upper
                """
            )

    def test_batch_error_multiprocess(self):
        """
        Test that an error is raised correctly when using multiprocessing
        """
        with pytest.raises(KeyError, match="column1 does not exist"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1000
                    values:
                        column: a
                wrangles:
                - batch:
                    use_multiprocessing: true
                    wrangles:
                        - convert.case:
                            input: column1
                            case: upper
                """
            )

    def test_batch_error_catch(self):
        """
        Test that an error is caught and
        the appropriate values are returned
        for a variety of data types
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                  column: a
            wrangles:
            - batch:
                on_error:
                  str: string
                  int: 1
                  float: 1.5
                  array: [1,2,3]
                  dict:
                    a: 1
                    b: 2
                  boolean: true
                wrangles:
                  - convert.case:
                      input: column1
                      case: upper
            """
        )
        
        assert len(df) == 1000
        assert df["str"][0] == "string"
        assert df["int"][0] == 1
        assert df["float"][0] == 1.5
        assert df["array"][0] == [1,2,3]
        assert df["dict"][0] == {"a": 1, "b": 2}
        assert df["boolean"][0] == True

    def test_batch_error_catch_mixed(self):
        """
        Test that an error is caught and
        the appropriate values are returned
        when some batches fail and some succeed
        """
        number_of_batches = [0]
        def record_batch(df, input):
            number_of_batches[0] += 1
            if number_of_batches[0] > 3:
                raise Exception("test error")
            else:
                df[input] = "b"
                return df

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 5
                values:
                    column: a
            wrangles:
            - batch:
                batch_size: 1
                on_error:
                  column: err
                wrangles:
                  - custom.record_batch:
                      input: column
            """,
            functions=record_batch
        )
        
        assert len(df) == 5
        assert df["column"][0] == "b"
        assert df["column"][4] == "err"

    def test_batch_where(self):
        """
        Test batch with where.
        This doesn't output data to the output column,
        just empty strings
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - batch:
                  where: numbers IN (1, 3)
                  wrangles:
                    - convert.case:
                        input: column
                        output: output col
                        case: upper
            """,
            dataframe=pd.DataFrame({
                "column": ["a", "b", "c"],
                "numbers": [1, 2, 3]
            })
        )     
        assert df['output col'].to_list() == ["A","","C"]

    def test_batch_variables(self):
        """
        Test batch wrangle with a variable passed through
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                    column: a
            wrangles:
              - batch:
                  wrangles:
                    - convert.case:
                        input: column
                        case: ${case}
            """,
            variables={"case": "upper"}
        )
        assert df['column'].tolist() == ["A"] * 1000

    def test_batch_variable_if(self):
        """
        Test batch wrangle with a variable passed to an if
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1000
                values:
                    column: a
            wrangles:
              - batch:
                  wrangles:
                    - convert.case:
                        input: column
                        case: upper
                        if: ${condition}
            """,
            variables={"condition": True}
        )
        assert df['column'].tolist() == ["A"] * 1000


class TestLookup:
    """
    Test lookup wrangle
    """
    # def test_lookup(self):
    #     """
    #     Test lookup function
    #     """
    #     data = pd.DataFrame({
    #         'Col1': ['One', 'Two', 'Three', 'Four'],
    #     })
    #     recipe = """
    #     wrangles:
    #     - lookup:
    #         input: Col1
    #         output: Col2
    #         reference:
    #             One: Eleven
    #             Two: Twelve
    #             Four: Fourteen
    #     """
    #     df = wrangles.recipe.run(recipe, dataframe=data)
    #     assert df.iloc[0]['Col2'] == 'Eleven' and df.iloc[1]['Col2'] == 'Twelve'

    # def test_lookup_multiple_outputs(self):
    #     """
    #     Test lookup function with multiple output columns
    #     """
    #     data = pd.DataFrame({
    #         'Col1': ['One', 'Two', 'Three', 'Four'],
    #         'Col2': ['Four', 'Three', 'Two', 'One']
    #     })
    #     recipe = """
    #     wrangles:
    #     - lookup:
    #         input: Col1
    #         output: 
    #             - Col3
    #             - Col4
    #         reference:
    #             One: Eleven
    #             Two: Twelve
    #             Four: Fourteen
    #     """
    #     df = wrangles.recipe.run(recipe, dataframe=data)
    #     assert df.iloc[0]['Col3'] == 'Eleven' and df.iloc[2]['Col4'] == ''

    # def test_lookup_multiple_inputs_error(self):
    #     """
    #     Test error when attempting to pass multiple input columns
    #     """
    #     data = pd.DataFrame({
    #         'Col1': ['One', 'Two', 'Three', 'Four'],
    #         'Col2': ['Four', 'Three', 'Two', 'One']
    #     })
    #     recipe = """
    #     wrangles:
    #     - lookup:
    #         input: 
    #             - Col1
    #             - Col2
    #         output: 
    #             - Col3
    #             - Col4
    #         reference:
    #             One: Eleven
    #             Two: Twelve
    #             Four: Fourteen
    #     """
    #     with pytest.raises(ValueError) as info:
    #         wrangles.recipe.run(recipe, dataframe=data)

    #     assert (
    #         info.typename == "ValueError" and 
    #         str(info.value) == "lookup - The input must be a string."
    #     )

    # def test_lookup_no_output(self):
    #     """
    #     Test lookup function without an output
    #     """
    #     data = pd.DataFrame({
    #         'Col1': ['One', 'Two', 'Three', 'Four'],
    #         'Col2': ['Four', 'Three', 'Two', 'One']
    #     })
    #     recipe = """
    #     wrangles:
    #     - lookup:
    #         input: Col1
    #         reference:
    #             One: Eleven
    #             Two: Twelve
    #             Four: Fourteen
    #     """
    #     df = wrangles.recipe.run(recipe, dataframe=data)
    #     assert df.iloc[0]['Col1'] == 'Eleven'
        
    # def test_lookup_default(self):
    #     """
    #     Test lookup function using a default
    #     """
    #     data = pd.DataFrame({
    #         'Col1': ['One', 'Two', 'Three', 'Four']
    #     })
    #     recipe = """
    #     wrangles:
    #     - lookup:
    #         input: Col1
    #         output: Col2
    #         reference:
    #             One: Eleven
    #             Two: Twelve
    #             Four: Fourteen
    #         default: This is a default
    #     """
    #     df = wrangles.recipe.run(recipe, dataframe=data)
    #     assert df.iloc[2]['Col2'] == 'This is a default'


    def test_lookup_model_unrecognized_column(self):
        """
        Test lookup using a saved lookup wrangle
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: a
            wrangles:
            - lookup:
                input: Col1
                output: Col2
                model_id: fe730444-1bda-4fcd
            """
        )
        assert df['Col2'][0] == {"Value": 1}

    def test_lookup_model_named_column(self):
        """
        Test lookup using a saved lookup wrangle
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: a
            wrangles:
            - lookup:
                input: Col1
                output: Value
                model_id: fe730444-1bda-4fcd
            """
        )
        assert df['Value'][0] == 1

    def test_lookup_model_input_list(self):
        """
        Test lookup using a single named output column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: a
            wrangles:
            - lookup:
                input:
                - Col1
                output: Value
                model_id: fe730444-1bda-4fcd
            """
        )
        assert df['Value'][0] == 1

    def test_lookup_model_named_columns(self):
        """
        Test lookup using multiple named output columns
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: a
            wrangles:
            - lookup:
                input: Col1
                output:
                - Value1
                - Value2
                model_id: 6e97bb6c-bfab-402b
            """
        )
        assert df['Value1'][0] == 1 and df['Value2'][0] == "z"

    def test_lookup_rename_outputs_single(self):
        """
        Test renaming a single output column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: a
            wrangles:
            - lookup:
                input: Col1
                output:
                  Value: XYZ_Value
                model_id: fe730444-1bda-4fcd
            """
        )
        assert df['XYZ_Value'][0] == 1

    def test_lookup_rename_outputs_list_all(self):
        """
        Test renaming multiple output columns
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: a
            wrangles:
            - lookup:
                input: Col1
                output:
                - Value1: XYZ_Value1
                - Value2: XYZ_Value2
                model_id: 6e97bb6c-bfab-402b
            """
        )
        assert (
            df['XYZ_Value1'][0] == 1
            and "Value1" not in df.columns
            and df['XYZ_Value2'][0] == "z"
            and "Value2" not in df.columns
        )

    def test_lookup_rename_outputs_list_partial(self):
        """
        Test renaming some of multiple output columns
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: a
            wrangles:
            - lookup:
                input: Col1
                output:
                - Value1: XYZ_Value1
                - Value2
                model_id: 6e97bb6c-bfab-402b
            """
        )
        assert (
            df['XYZ_Value1'][0] == 1
            and "Value1" not in df.columns
            and df['Value2'][0] == "z"
        )

    def test_lookup_rename_outputs_where(self):
        """
        Test renaming some of multiple output columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - lookup:
                input: Col1
                output:
                - Value1: XYZ_Value1
                - Value2
                model_id: 6e97bb6c-bfab-402b
                where: "[where] = 'x'"
            """,
            dataframe=pd.DataFrame({
                "Col1": ["a", "a"],
                "where": ["x", "y"]
            })
        )
        assert (
            "Value1" not in df.columns and
            df['XYZ_Value1'][0] == 1 and df['Value2'][0] == "z" and
            df['XYZ_Value1'][1] == "" and df['Value2'][1] == ""
        )

    def test_lookup_model_unrecognized_value_unnamed_column(self):
        """
        Test lookup using a saved lookup wrangle
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: aaa
            wrangles:
            - lookup:
                input: Col1
                output: Col2
                model_id: fe730444-1bda-4fcd
            """
        )
        assert df['Col2'][0] == {"Value": ""}

    def test_lookup_model_unrecognized_value_named_column(self):
        """
        Test lookup using a saved lookup wrangle
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    Col1: aaa
            wrangles:
            - lookup:
                input: Col1
                output: Value
                model_id: fe730444-1bda-4fcd
            """
        )
        assert df['Value'][0] == ""

    def test_lookup_wrong_model_id_type(self):
        """
        Test the error message when passing through a model_id for a different wrangle type
        """
        with pytest.raises(ValueError, match="Using recipe model_id 1e13e845-bc3f-4b27 in a lookup function"):
            wrangles.recipe.run(
                """
                wrangles:
                    - lookup:
                        input: Stuff
                        model_id: 1e13e845-bc3f-4b27
                """,
                dataframe=pd.DataFrame({'Stuff': ['This is stuff', 'This is also stuff', 'This is more stuff']})
            )


class TestMatrix:
    """
    Test matrix wrangle
    """
    def test_basic(self):
        """
        Test a basic matrix with a variable defined by a list
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    Col1: a
            wrangles:
              - matrix:
                  variables:
                    var: [a,b,c]
                  wrangles:
                    - format.suffix:
                        input: Col1
                        output: out_${var}
                        value: ${var}
            """
        )
        assert (
            df['out_a'][0] == "aa" and
            df['out_b'][0] == "ab" and
            df['out_c'][0] == "ac"
        )

    def test_where(self):
        """
        Test a matrix with a where clause
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - matrix:
                  variables:
                    var: set(col2)
                  wrangles:
                    - convert.case:
                        input: col1
                        case: ${var}
                        where: col2 = ?
                        where_params:
                          - ${var}
            """,
            dataframe=pd.DataFrame({
                "col1": ["aaa", "bbb", "ccc"],
                "col2": ["upper", "lower", "title"]
            })
        )

        assert (
            df['col1'][0] == "AAA" and
            df['col1'][1] == "bbb" and
            df['col1'][2] == "Ccc"
        )

    def test_matrix_where(self):
        """
        Test a matrix with a where clause, but different than above
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - matrix:
                  where: numbers IN (1, 3)
                  variables:
                    var: set(case)
                  wrangles:
                    - convert.case:
                        input: col1
                        case: ${var}
                        where: '"case" = ?'
                        where_params:
                          - ${var}
            """,
            dataframe=pd.DataFrame({
                "col1": ["aaa", "BBB", "ccc"],
                "case": ["upper", "lower", "title"],
                "numbers": [1, 2, 3]
            })
        )
        assert df['col1'].to_list() == ["AAA","BBB","Ccc"]

    def test_variable_custom_function(self):
        """
        Test using a custom function to define a variable values
        """
        def test_fn():
            return ["a", "b", "c"]

        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    Col1: a
            wrangles:
              - matrix:
                  variables:
                    var: custom.test_fn
                  wrangles:
                    - format.suffix:
                        input: Col1
                        output: out_${var}
                        value: ${var}
            """,
            functions=test_fn
        )
        assert (
            df['out_a'][0] == "aa" and
            df['out_b'][0] == "ab" and
            df['out_c'][0] == "ac"
        )
    
    def test_custom_function(self):
        """
        Test using a custom function in the wrangles
        """
        def test_fn(Col1, value):
            return Col1 + value
        
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    Col1: a
            wrangles:
              - matrix:
                  variables:
                    var: [a,b,c]
                  wrangles:
                    - custom.test_fn:
                        input: Col1
                        output: out_${var}
                        value: ${var}
            """,
            functions=test_fn
        )
        assert (
            df['out_a'][0] == "aa" and
            df['out_b'][0] == "ab" and
            df['out_c'][0] == "ac"
        )

    def test_error(self):
        """
        Test that an error is raised correctly
        """
        with pytest.raises(KeyError, match="Col2 does not exist"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1
                    values:
                        Col1: a
                wrangles:
                - matrix:
                    variables:
                        var: [a,b,c]
                    wrangles:
                        - format.suffix:
                            input: Col2
                            output: out_${var}
                            value: ${var}
                """
            )

    def test_extract_ai(self):
        """
        Test using extract.ai within a matrix
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - matrix:
                  variables:
                    Category: set(Category)
                  wrangles:
                    - extract.ai:
                        input: Description
                        api_key: ${OPENAI_API_KEY}
                        seed: 1
                        retries: 2
                        output:
                          ${Category}:
                            type: string
                            description: The type of ${Category}
                        where: Category = ?
                        where_params:
                          - ${Category}
            """,
            dataframe=pd.DataFrame({
                "Category": ["Animal", "Mineral", "Vegetable"],
                "Description": ["Tiger", "Gold", "Carrot"]
            })
        )
        assert (
            df['Animal'].values.tolist() == ['Tiger', '', ''] and
            df['Mineral'].values.tolist() == ['', 'Gold', ''] and
            df['Vegetable'].values.tolist() == ['', '', 'Carrot']
        )


def wait_then_update(df, duration, input, output, value):
    """
    Wait and then add suffix to value
    """
    time.sleep(duration)
    df[output] = df[input] + value
    return df
    
class TestConcurrent:
    """
    Test concurrent wrangle
    """
    def test_multithreaded(self):
        """
        Test concurrent wrangle with multiple threads
        """
        start = datetime.now()

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    column: a
            wrangles:
              - concurrent:
                  wrangles:
                    - custom.wait_then_update:
                        input: column
                        output: column_a
                        duration: 3
                        value: a
                    - custom.wait_then_update:
                        input: column
                        output: column_b
                        duration: 2
                        value: b
                    - custom.wait_then_update:
                        input: column
                        output: column_c
                        duration: 5
                        value: c
            """,
            functions=wait_then_update
        )

        end = datetime.now()

        assert (
            df['column_a'][0] == 'aa' and
            df['column_b'][0] == 'ab' and
            df['column_c'][0] == 'ac' and
            5 <= (end - start).seconds < 10
        )

    def test_multiprocess(self):
        """
        Test concurrent wrangle with multiple processes
        """
        start = datetime.now()

        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    column: a
            wrangles:
              - concurrent:
                  use_multiprocessing: true
                  wrangles:
                    - custom.wait_then_update:
                        input: column
                        output: column_a
                        duration: 3
                        value: a
                    - custom.wait_then_update:
                        input: column
                        output: column_b
                        duration: 2
                        value: b
                    - custom.wait_then_update:
                        input: column
                        output: column_c
                        duration: 5
                        value: c
            """,
            functions=wait_then_update
        )

        end = datetime.now()

        assert (
            df['column_a'][0] == 'aa' and
            df['column_b'][0] == 'ab' and
            df['column_c'][0] == 'ac' and
            5 <= (end - start).seconds < 10
        )

    def test_output_error(self):
        """
        Check that a clear error is given if the
        user tries to use a wrangle that doesn't
        specify an output column.
        """
        with pytest.raises(ValueError, match="specify output"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 1
                    values:
                      column: a
                wrangles:
                - concurrent:
                    wrangles:
                      - convert.case:
                          input: column
                """
            )

    def test_multithreaded_where(self):
        """
        Test concurrent wrangle with where
        """
        start = datetime.now()

        df = wrangles.recipe.run(
            """
            wrangles:
              - concurrent:
                  where: numbers > 1
                  wrangles:
                    - custom.wait_then_update:
                        input: column
                        output: column_a
                        duration: 3
                        value: a
                    - custom.wait_then_update:
                        input: column
                        output: column_b
                        duration: 2
                        value: b
                    - custom.wait_then_update:
                        input: column
                        output: column_c
                        duration: 5
                        value: c
            """,
            dataframe=pd.DataFrame({
            "column": ["a","b","c"],
            "numbers": [1, 2, 3]
            }),
            functions=wait_then_update
        )

        end = datetime.now()

        assert (
            df['column_a'][0] == '' and
            df['column_b'][1] == 'bb' and
            df['column_c'][2] == 'cc' and
            5 <= (end - start).seconds < 10
        )


class TestTranspose:
    """
    All transpose tests
    """
    def test_pd_transpose(self):
        """
        Test transpose
        """
        data = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi'],
            'col3': ['Bowser'],
        }, index=['Characters'])
        recipe = """
        wrangles:
          - transpose:
              header_column: null
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['Characters']

    def test_transpose_where(self):
        """
        Test transpose with where
        """
        data = pd.DataFrame({
            'col': ['Mario', 'Luigi', 'Koopa'],
            'col2': ['Luigi', 'Bowser', 'Peach'],
            'numbers': [4, 2, 8]
        })
        recipe = """
        wrangles:
          - transpose:
              header_column: null
              where: numbers > 3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.index.to_list() == ['col', 'col2', 'numbers'] and df.columns.to_list() == [0, 2]

    def test_transpose_set_headings(self):
        """
        Choose column that will become the headings of the transposed dataframe
        """
        original_df = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi'],
            'col3': ['Bowser'],
        })

        df = wrangles.recipe.run(
            """
            wrangles:
            - transpose:
                header_column: col
            """,
            dataframe=original_df
        )

        df = wrangles.recipe.run(
            """
            wrangles:
            - transpose:
                header_column: col
            """,
            dataframe=df
        )

        assert original_df.to_dict(orient="records") == df.to_dict(orient="records")

    def test_transpose_set_headings_index(self):
        """
        Choose column that will become the headings of the
        transposed dataframe as a column index
        """
        original_df = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi'],
            'col3': ['Bowser'],
        })

        df = wrangles.recipe.run(
            """
            wrangles:
            - transpose:
                header_column: 0
            """,
            dataframe=original_df
        )

        df = wrangles.recipe.run(
            """
            wrangles:
            - transpose:
                header_column: 0
            """,
            dataframe=df
        )

        assert original_df.to_dict(orient="records") == df.to_dict(orient="records")

class TestTry:
    """
    Test try
    """
    def test_try_fail(self):
        """
        Test a try that fails
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header: value
            wrangles:
              - try:
                  wrangles:
                    - math:
                        input: header * 2
                        output: should_fail
            """
        )
        assert (
            df.columns.tolist() == ['header'] and
            df['header'][0] == 'value'
        )

    def test_try_pass(self):
        """
        Test a try that passes
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header: 1
            wrangles:
              - try:
                  wrangles:
                    - math:
                        input: header * 2
                        output: should_not_fail
            """
        )
        assert (
            df.columns.tolist() == ['header', 'should_not_fail'] and
            df['header'][0] == 1 and
            df['should_not_fail'][0] == 2
        )

    def test_try_except_dict(self):
        """
        Test a try that has an except
        containing a dictionary
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header: value
            wrangles:
              - try:
                  except:
                    should_fail: failed
                  wrangles:
                    - math:
                        input: header * 2
                        output: should_fail
            """
        )
        assert (
            df.columns.tolist() == ['header', 'should_fail'] and
            df['header'][0] == 'value' and
            df['should_fail'][0] == 'failed'
        )

    def test_try_except_dict_list(self):
        """
        Test a try that has an except
        containing a dictionary with a list as a value
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header: value
            wrangles:
              - try:
                  except:
                    should_fail: [failed, failed]
                  wrangles:
                    - math:
                        input: header * 2
                        output: should_fail
            """
        )
        assert (
            df.columns.tolist() == ['header', 'should_fail'] and
            df['header'][0] == 'value' and
            df['should_fail'][0] == ['failed', 'failed']
        )


    def test_try_except_wrangles(self):
        """
        Test a try that has an except
        containing wrangles
        """
        df = wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header: value
            wrangles:
              - try:
                  wrangles:
                    - math:
                        input: header * 2
                        output: should_fail
                  except:
                    - convert.case:
                         input: header
                         output: should_fail
                         case: upper
            """
        )
        assert (
            df.columns.tolist() == ['header', 'should_fail'] and
            df['header'][0] == 'value' and
            df['should_fail'][0] == 'VALUE'
        )

    def test_try_fail_where(self):
        """
        Test a try that fails using where.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - try:
                  where: numbers = 8
                  wrangles:
                    - math:
                        input: header * 2
                        output: should_fail
            """,
            dataframe=pd.DataFrame({
                "header": ["value1", "value2", 'value3'],
                "numbers": [5, 8, 18]
            })
        )
        assert (
            df['header'].to_list() == ['value1','value2','value3'] and 
            df['numbers'].to_list() == [5, 8, 18] and 
            list(df.columns) == ['header', 'numbers']
        )

    def test_try_pass_where(self):
        """
        Test a try that passes using where.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - try:
                  where: numbers = 8
                  wrangles:
                    - math:
                        input: numbers * 2
                        output: numbers
            """,
            dataframe=pd.DataFrame({
                "header": ["value1", "value2", 'value3'],
                "numbers": [5, 8, 18]
            })
        )
        assert (
            df['header'].to_list() == ['value1','value2','value3'] and 
            df['numbers'].to_list() == [5, 16, 18] and 
            list(df.columns) == ['header', 'numbers']
        )

    def test_retries(self):
        """
        Test a try with retries
        """
        global retry_count
        retry_count = 0

        def retry_fn(df):
            global retry_count
            retry_count += 1
            raise Exception("This is an error")
        
        wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: value
            wrangles:
            - try:
                retries: 3
                wrangles:
                    - custom.retry_fn: {}
            """,
            functions=retry_fn
        )
        
        assert retry_count == 4

    def test_retries_zero(self):
        """
        Test a try with no retries
        """
        global retry_count_zero
        retry_count_zero = 0

        def retry_fn(df):
            global retry_count_zero
            retry_count_zero += 1
            raise Exception("This is an error")
        
        wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: value
            wrangles:
            - try:
                wrangles:
                    - custom.retry_fn: {}
            """,
            functions=retry_fn
        )
        
        assert retry_count_zero == 1
