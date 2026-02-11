"""
Tests for passthrough pandas capabilities
"""
import wrangles
import pandas as pd
import pytest
from numpy import half, single, double, longdouble

class TestPandasHead:
    """
    Test pandas.head
    """
    def test_pandas_head(self):
        """
        Test using pandas head function
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.head:
                parameters:
                    n: 1
            """,
            dataframe=pd.DataFrame(
                {'header': [1, 2, 3, 4, 5]}
            )
        )
        assert df['header'].values[0] == 1 and len(df) == 1

    def test_pandas_head_where(self):
        """
        Test using pandas head function using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.head:
                parameters:
                    n: 2
                where: header > 2
            """,
            dataframe=pd.DataFrame(
                {'header': [1, 2, 3, 4, 5]}
            )
        )
        assert df['header'].to_list() == [3, 4]

    def test_pandas_head_empty(self):
        """
        Test using pandas head function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.head:
                parameters:
                    n: 2
            """,
            dataframe=pd.DataFrame()
        )
        assert df.empty


class TestPandasTail:
    """
    Test pandas.tail
    """
    def test_pandas_tail(self):
        """
        Test using pandas tail function
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.tail:
                parameters:
                    n: 1
            """,
            dataframe=pd.DataFrame(
                {'header': [1, 2, 3, 4, 5]}
            )
        )
        assert df['header'].values[0] == 5 and len(df) == 1

    def test_pandas_tail_where(self):
        """
        Test using pandas tail function using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.tail:
                parameters:
                    n: 2
                where: header < 4
            """,
            dataframe=pd.DataFrame(
                {'header': [1, 2, 3, 4, 5]}
            )
        )
        assert df['header'].to_list() == [2, 3]

    def test_pandas_tail_empty(self):
        """
        Test using pandas tail function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.tail:
                parameters:
                    n: 2
            """,
            dataframe=pd.DataFrame()
        )
        assert df.empty


class TestPandasRound:
    """
    Test pandas.round
    """
    def test_pandas_input_output(self):
        """
        Test a function that has an input and output
        """
        data = pd.DataFrame({
            'numbers': [3.14159265359, 2.718281828]
        })
        recipe = """
        wrangles:
        - pandas.round:
            input: numbers
            output: round_num
            parameters:
                decimals: 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['round_num'].iloc[0] == 3.14

    def test_pandas_input_output_where(self):
        """
        Test a function that has an input and output using where
        """
        data = pd.DataFrame({
            'numbers': [3.14159265359, 2.718281828]
        })
        recipe = """
        wrangles:
        - pandas.round:
            input: numbers
            parameters:
                decimals: 2
            where: numbers > 3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['numbers'][0] == 3.14 and df['numbers'][1] == 2.718281828

    def test_pandas_round_empty(self):
        """
        Test using pandas round function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.round:
                input: numbers
                output: round_num
                parameters:
                    decimals: 2
            """,
            dataframe=pd.DataFrame({'numbers': []})
        )
        assert df.empty and df.columns.to_list() == ['numbers', 'round_num']


class TestPandasTranspose:
    """
    Test pandas.transpose
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
        - pandas.transpose: {}
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['Characters']

    def test_transpose_where(self):
        """
        Test transpose with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.transpose:
                where: numbers > 3
            """,
            dataframe=pd.DataFrame({
                'col': ['Mario', 'Luigi', 'Koopa'],
                'col2': ['Luigi', 'Bowser', 'Peach'],
                'numbers': [4, 2, 8]
            })
        )
        assert df.index.to_list() == ['col', 'col2', 'numbers'] and df.columns.to_list() == [0, 2]

    def test_transpose_empty(self):
        """
        Test using pandas transpose function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - pandas.transpose: {}
            """,
            dataframe=pd.DataFrame({
                'col1': [],
                'col2': [],
            })
        )
        assert df.empty


#
# NATIVE RECIPE WRANGLES
#
class TestCopy:
    """
    Test copy
    """
    def test_pd_copy_one_col(self):
        """
        Test one input and output (strings)
        """
        data = pd.DataFrame({
            'col': ['SuperMario']
        })
        recipe = """
        wrangles:
        - copy:
            input: col
            output: col-copy
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col', 'col-copy']
        
    def test_pd_copy_multi_cols(self):
        """
        Test multiple inputs and outputs (list)
        """
        data = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi']
        })
        recipe = """
        wrangles:
        - copy:
            input:
                - col
                - col2
            output:
                - col1-copy
                - col2-copy
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col', 'col2', 'col1-copy', 'col2-copy']
        
    def test_pd_copy_repeated_column(self):
        """
        Test copying one column multiple times
        """
        data = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi']
        })
        recipe = """
        wrangles:
        - copy:
            input:
                - col
                - col
                - col
                - col
            output:
                - col1-copy1
                - col1-copy2
                - col1-copy3
                - col1-copy4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col', 'col2', 'col1-copy1', 'col1-copy2', 'col1-copy3', 'col1-copy4']
        
    def test_pd_copy_multi_cols_with_repetition(self):
        """
        Test multiple inputs and outputs where one column is repeated
        """
        data = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi']
        })
        recipe = """
        wrangles:
        - copy:
            input:
                - col
                - col2
                - col
            output:
                - col1-copy
                - col2-copy
                - not-col1-copy
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col', 'col2', 'col1-copy', 'col2-copy', 'not-col1-copy']

    def test_pd_copy_where(self):
        """
        Test copy using where
        """
        data = pd.DataFrame({
            'col': ['SuperMario', 'Luigi', 'Bowser'],
            'numbers': [4, 2, 8]
        })
        recipe = """
        wrangles:
        - copy:
            input: col
            output: col-copy
            where: numbers > 3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['col-copy'] == 'SuperMario' and df.iloc[1]['col-copy'] == ''
        
    def test_pd_copy_one_to_many(self):
        """
        Test a single input with multiple outputs (list)
        """
        data = pd.DataFrame({
            'col': ['Mario']
        })
        recipe = """
        wrangles:
        - copy:
            input: col
            output:
                - col-copy1
                - col-copy2
                - col-copy3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col', 'col-copy1', 'col-copy2', 'col-copy3'] and df.iloc[0]['col-copy3'] == 'Mario'
        
    def test_pd_copy_len_mismatch(self):
        """
        Test the error when input and output lengths do not match
        """
        data = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi']
        })
        recipe = """
        wrangles:
        - copy:
            input: 
                - col
                - col2
            output:
                - col-copy1
                - col-copy2
                - col-copy3
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe=recipe, dataframe=data)
        assert (
            info.typename == "ValueError" and 
            str(info.value) == "ERROR IN WRANGLE #1 copy - at line 3 - Input and output must be the same length"
        )

    def test_copy_shorthand(self):
        """
        Test copying columns using the shorthand method
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 3
                values:
                    col1: val1
                    col2: val2

            wrangles:
            - copy:
                col1: col3
                col2: col4
            """
        )
        assert list(df['col3'].values) == ['val1', 'val1', 'val1'] and list(df['col4'].values) == ['val2', 'val2', 'val2'] 

    def test_copy_empty(self):
        """
        Test using copy function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - copy:
                input: col
                output: col-copy
            """,
            dataframe=pd.DataFrame({'col': []})
        )
        assert df.empty and df.columns.to_list() == ['col', 'col-copy']


class TestDrop:
    """
    Test drop
    """
    def test_drop_one_column(self):
        """
        Test drop using one column (string)
        """
        data = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi']
        })
        recipe = """
        wrangles:
        - drop:
            columns: col2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col']

    def test_drop_multiple_columns(self):
        """
        Test multiple columns (list)
        """
        data = pd.DataFrame({
            'col': ['Mario'],
            'col2': ['Luigi'],
            'col3': ['Bowser'],
        })
        recipe = """
        wrangles:
        - drop:
            columns:
                - col2
                - col3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col']

    def test_drop_where(self):
        """
        Test drop with where
        """
        with pytest.raises(NotImplementedError, match="where"):
            wrangles.recipe.run(
                """
                wrangles:
                - drop:
                    columns: col2
                    where: numbers > 3
                """,
                dataframe=pd.DataFrame({
                    'col': ['Mario', 'Peach', 'Bowser'],
                    'col2': ['Luigi', 'Toadstool', 'Koopa'],
                    'numbers': [4, 2, 8]
                })
            )

    def test_drop_empty(self):
        """
        Test using drop function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - drop:
                columns: col
            """,
            dataframe=pd.DataFrame({'col': []})
        )
        assert df.empty and df.columns.to_list() == []

    
    def test_drop_unexisting_columns(self):
        """
            Test drop using unexisting column (string)
        """
        data = pd.DataFrame({
                    'col': ['Mario'],
                    'col2': ['Luigi'],
                    'col3': ['Bowser'],
                })
        recipe = """
            wrangles:
            - drop:
                columns:
                    - col3
                    - col4
            """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert list(df.columns) == ['col', 'col2']

class TestRound:
    """
    Test round
    """
    def test_round_one_input(self):
        """
        Test round with one input and output. decimals default is 0
        """
        data = pd.DataFrame({
            'col1': [3.13],
            'col2': [1.16],
            'col3': [2.5555],
            'col4': [3.15]
        })
        recipe = """
        wrangles:
        - round:
            input: col1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['col1'][0] == 3

    def test_round_specify_decimals(self):
        """
        Test round with one input and output. decimals default is 0
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    col1: 3.13
                    col2: 1.16

            wrangles:
            - round:
                input:
                    - col1
                    - col2
                decimals: 1
            """
        )
        assert (
            df['col1'][0] == 3.1 and
            df['col2'][0] == 1.2
        )

    def test_round_multi_input(self):
        """
        Test multiple inputs and outputs
        """
        data = pd.DataFrame({
            'col1': [3.13],
            'col2': [1.16],
            'col3': [2.5555],
            'col4': [3.15]
        })
        recipe = """
        wrangles:
        - round:
            input:
                - col1
                - col2
                - col3
            output:
                - out1
                - out2
                - out3
            decimals: 1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df[['out1', 'out2', 'out3']].values.tolist()[0] == [3.1, 1.2, 2.6]
        
    def test_round_where(self):
        """
        Test round using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - round:
                input: col
                where: col > 2.5
                decimals: 1
            """,
            dataframe=pd.DataFrame({
                'col': [3.13, 1.16, 2.5555, 3.15]
            })
        )
        assert df['col'].to_list() == [3.1, 1.16, 2.6, 3.2]

    def test_round_mixed(self):
        """
        Test round with mixed inputs and outputs
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - round:
                input:
                    - col
                decimals: 1
            """,
            dataframe=pd.DataFrame({
                'col': [3.13, "Something else", 1.16, None, "2.5555"]
            })
        )
        assert df['col'].to_list() == [3.1, '', 1.2, '', 2.6]

    def test_round_string(self):
        """
        test round with strings
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - round:
                input: col
                decimals: 1
            """,
            dataframe=pd.DataFrame({
                'col': ["3.13", "1.16", "2.5555", "3.15"]
            })
        )
        assert df['col'].to_list() == [3.1, 1.2, 2.6, 3.2]

    def test_round_floatinf(self):
        """
        test infinity
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - round:
                input: col
                decimals: 1
            """,
            dataframe=pd.DataFrame({
                'col': [float('inf'), float('-inf')]
            })
        )
        assert df['col'].to_list() == [float('inf'), float('-inf')]

    def test_round_int(self):
        """
        test int values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - round:
                input: col
                decimals: 1
            """,
            dataframe=pd.DataFrame({
                'col': [3, 1, 2, 3]
            })
        )
        assert df['col'].to_list() == [3.0, 1.0, 2.0, 3.0]

    def test_round_float(self):
        """
        test float values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - round:
                input: col
                decimals: 1
            """,
            dataframe=pd.DataFrame({
                'col': [half(3.333), single(1003.22), double(489324.2343), longdouble(8948293423.23455)]
            })
        )
        assert df['col'].to_list() == [3.3, 1003.2, 489324.2, 8948293423.2]

    def test_round_empty(self):
        """
        Test using round function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - round:
                input: col
                output: output column
                decimals: 1
            """,
            dataframe=pd.DataFrame({'col': []})
        )
        assert df.empty and df.columns.to_list() == ['col', 'output column']
        

class TestReindex:
    """
    Test reindex
    """
    def test_reindex(self):
        """
        Testing Pandas reindex function
        """
        data = pd.DataFrame(
            {
                'http_status': [200, 200, 404, 404, 301],
                'response_time': [0.04, 0.02, 0.07, 0.08, 1.0]
            },
            index=['Firefox', 'Chrome', 'Safari', 'IE10', 'Konqueror']
        )
        
        rec = """
        wrangles:
        - reindex:
            index:
                - Safari
                - Iceweasel
                - Comodo Dragon
                - IE10
        """
        df = wrangles.recipe.run(recipe=rec, dataframe=data)
        assert df.index.to_list() == ['Safari', 'Iceweasel', 'Comodo Dragon', 'IE10']
        
    def test_reindex_where(self):
        """
        Testing reindex with where
        """
        with pytest.raises(NotImplementedError, match="where"):
            wrangles.recipe.run(
                recipe="""
                wrangles:
                - reindex:
                    index:
                        - 2
                        - 1
                        - 0
                    where: numbers > 3
                """,
                dataframe=pd.DataFrame({
                    'col': ['Mario', 'Luigi', 'Koopa'],
                    'col2': ['Luigi', 'Bowser', 'Peach'],
                    'numbers': [4, 2, 8]
                })
            )


class TestExplode:
    """
    Test explode
    """
    def test_explode(self):
        """
        Test explode basic function
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input:
                    - C
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert df['C'].tolist() == ['a', 'b', 'c', 'NAN', '', 'd', 'e']

    def test_explode_string(self):
        """
        Test explode with input as a string
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input: A
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert df['A'].tolist() == [0, 1, 2, 'foo', '', 3, 4]

    def test_explode_nothing_to_explode(self):
        """
        Test explode where there's nothing to change
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input: B
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert df['A'].tolist() == [[0, 1, 2], 'foo', [], [3, 4]]

    def test_explode_multiple_columns(self):
        """
        Test explode with multiple columns
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input:
                    - A
                    - C
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert len(df['A']) == 7
        
    def test_explode_non_existent_col(self):
        """
        Test explode function with a col that does not exists in df
        """
        with pytest.raises(KeyError) as info:
            df = wrangles.recipe.run(
                recipe="""
                wrangles:
                - explode:
                    input:
                    - AA
                """,
                dataframe=pd.DataFrame({
                    'A': [[0, 1, 2], 'foo', [], [3, 4]],
                    'B': 1,
                    'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
                })
            )
        assert info.typename == 'KeyError'

    def test_explode_multiple_columns_wildcard(self):
        """
        Test explode multiple columns defined
        using a wildcard
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input: A*
            """,
            dataframe=pd.DataFrame({
                'A1': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'A2': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert (
            df['A1'].tolist() == [0, 1, 2, 'foo', '', 3, 4] and
            df['A2'].tolist() == ['a', 'b', 'c', 'NAN', '', 'd', 'e']
        )

    def test_explode_multiple_inconsistent(self):
        """
        Test explode multiple with columns
        but the columns are inconsistent lengths
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(
                recipe="""
                wrangles:
                - explode:
                    input:
                        - A
                        - C
                """,
                dataframe=pd.DataFrame({
                    'A': [[0, 1, 2], 'foo', [], [3, 4]],
                    'B': 1,
                    'C': [['a', 'b'], 'NAN', [], ['d', 'e']]
                })
            )
        assert (
            info.typename == "ValueError" and 
            str(info.value) == "ERROR IN WRANGLE #1 explode - at line 3 - columns must have matching element counts"
        )

    def test_explode_reset_index_default(self):
        """
        Test explode with reset index as default
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input:
                    - C
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert df.index.to_list() == [0, 1, 2, 3, 4, 5, 6]

    def test_explode_reset_index_false(self):
        """
        Test explode with reset index as false
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input:
                    - C
                reset_index: false
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert df.index.to_list() == [0, 0, 0, 1, 2, 3, 3]

    def test_explode_reset_index_true(self):
        """
        Test explode with reset index as true
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input:
                    - C
                reset_index: true
            """,
            dataframe=pd.DataFrame({
                'A': [[0, 1, 2], 'foo', [], [3, 4]],
                'B': 1,
                'C': [['a', 'b', 'c'], 'NAN', [], ['d', 'e']]
            })
        )
        assert df.index.to_list() == [0, 1, 2, 3, 4, 5, 6]

    def test_explode_where(self):
        """
        Test explode using where
        """
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - explode:
                input: column
                where: numbers = 14
            """,
            dataframe=pd.DataFrame({
                'column': [['a', 'b', 'c'], ['f', 't', 'l'], ['w', 'k', 'm', 'b'], ['d', 'e']],
                'numbers': [4, 7, 14, 19]
            })
        )
        assert (
            df['column'].tolist() == [['a', 'b', 'c'], ['f', 't', 'l'], 'w', 'k', 'm', 'b', ['d', 'e']] and
            df['numbers'].tolist() == [4, 7, 14, 14, 14, 14, 19]
        )

    def test_explode_empty(self):
        """
        Test using explode function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - explode:
                input: column
            """,
            dataframe=pd.DataFrame({'column': []})
        )
        assert df.empty


class TestSort:
    """
    Test sort
    """
    def test_sort(self):
        """
        Test default sort
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 100
                values:
                    column: <number(1.00-1000.00)>
            wrangles:
            - sort:
                by: column
            """
        )

        assert (
            df["column"][0] <= df["column"][1]
            and df["column"].tolist()[-2] <= df["column"].tolist()[-1]
        )

    def test_sort_descending(self):
        """
        Test sort with a single column descending
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 100
                values:
                    column: <number(1.00-1000.00)>
            wrangles:
            - sort:
                by: column
                ascending: false
            """
        )

        assert (
            df["column"][0] >= df["column"][1]
            and df["column"].tolist()[-2] >= df["column"].tolist()[-1]
        )

    def test_sort_where(self):
        """
        Test default sort with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - sort:
                by: column
                where: numbers > 2
            """,
            dataframe=pd.DataFrame({
                'column': [3, 1, 5, 2, 4],
                'numbers': [1, 2, 3, 4, 5]
            })
        )
        assert df["column"].tolist() == [2, 4, 5]

    def test_sort_empty(self):
        """
        Test using sort function with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - sort:
                by: column
            """,
            dataframe=pd.DataFrame({'column': []})
        )
        assert df.empty

    def test_sort_float16_conversion(self):  
        """  
        Test sort with float16 columns that need conversion  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - sort:  
                by: column
                ascending: true
            """,  
            dataframe=pd.DataFrame({  
                'column': pd.array([3.5, 1.2, 2.8, 4.1], dtype='float16')  
            })  
        )  
        assert df['column'].tolist() == pytest.approx([1.2, 2.8, 3.5, 4.1], rel=1e-3)

    def test_sort_float16_descending(self):  
        """  
        Test sort with float16 columns in descending order  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - sort:  
                by: column  
                ascending: false  
            """,  
            dataframe=pd.DataFrame({  
                'column': pd.array([3.5, 1.2, 2.8, 4.1], dtype='float16')  
            })  
        )  
        assert df['column'].tolist() == pytest.approx([4.1, 3.5, 2.8, 1.2], rel=1e-3)

    def test_sort_float16_multiple_columns(self):  
        """  
        Test sort with multiple float16 columns  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - sort:  
                by: [col1, col2]  
            """,  
            dataframe=pd.DataFrame({  
                'col1': pd.array([2.0, 1.0, 2.0, 1.0], dtype='float16'),  
                'col2': pd.array([4.0, 3.0, 2.0, 1.0], dtype='float16')  
            })  
        )  
        assert (  
            df['col1'].tolist() == [1.0, 1.0, 2.0, 2.0] and  
            df['col2'].tolist() == [1.0, 3.0, 2.0, 4.0]  
    )  
    
    def test_sort_mixed_dtypes(self):  
        """  
        Test sort with mixed float16 and other dtypes  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - sort:  
                by: [float_col, int_col]  
            """,  
            dataframe=pd.DataFrame({  
                'float_col': pd.array([2.5, 1.5, 2.5], dtype='float16'),  
                'int_col': [3, 2, 1]  
            })  
        )  
        assert (  
            df['float_col'].tolist() == [1.5, 2.5, 2.5] and  
            df['int_col'].tolist() == [2, 1, 3]  
        )  

    def test_sort_float16_with_where(self):  
        """  
        Test sort with float16 columns using where clause  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - sort:  
                by: column  
                where: numbers > 2  
            """,  
            dataframe=pd.DataFrame({  
                'column': pd.array([3.5, 1.2, 5.8, 2.1, 4.3], dtype='float16'),  
                'numbers': [1, 2, 3, 4, 5]  
            })  
        )  
        assert df['column'].tolist() == pytest.approx([2.1, 4.3, 5.8], rel=1e-3)

    def test_sort_mixed_data_types(self):  
        """  
        Test sorting with mixed float and string columns  
        """  
        df = wrangles.recipe.run(  
            """  
            wrangles:  
            - sort:  
                by:  
                  - float_col  
                  - str_col  
                ascending:  
                  - false  
                  - true  
            """,  
            dataframe=pd.DataFrame({  
                "float_col": [1.2, 2.8, 1.2, 3.5],  
                "str_col": ["banana", "apple", "zebra", "qux"]  
            })  
        )  
        assert df["float_col"].tolist() == [3.5, 2.8, 1.2, 1.2]  
        assert df["str_col"].tolist() == ["qux", "apple", "banana", "zebra"]
