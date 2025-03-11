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