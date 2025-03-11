import pandas as pd
from wrangles.connectors import sqlite

def test_read_sql():
    """
    Test basic read
    """
    df = sqlite.read(
        database = './tests/samples/test.db',
        command = 'SELECT * from df_mock'
    )
    assert df.equals(
        pd.DataFrame(
            {
                'Col1': ['Data1', 'Data2'],
                'Col2': [1, 2]
            }
        )
    )

def test_write_sql():
    """
    Test a basic read
    """
    df = pd.DataFrame({'Col1': ['Data1', 'Data2']})
    sqlite.write(
        df = df,
        database = './tests/temp/temp.db',
        table = 'temp_mock'
    )
    assert sqlite.read(
        database='./tests/temp/temp.db',
        command='SELECT * from temp_mock'
    ).equals(df)

def test_run():
    """
    Test running a command
    """
    df = pd.DataFrame({'Col1': ['Data1', 'Data2']})
    sqlite.write(
        df = df,
        database = './tests/temp/temp_run.db',
        table = 'test_table'
    )

    # copy test_table to test_table_copy
    sqlite.run(
        database = './tests/temp/temp_run.db',
        command = 'CREATE TABLE test_table_copy AS SELECT * FROM test_table'
    )

    # read test_table_copy
    df_copy = sqlite.read(
        database = './tests/temp/temp_run.db',
        command = 'SELECT * from test_table_copy'
    )

    # assert that the two tables are the same
    assert df.equals(df_copy)
