import pandas as pd

# Testing sqlite connectors
from wrangles.connectors.sqlite import read, write

def test_read_sql(mocker):
    data = pd.DataFrame({'Col1': ['Data1', 'Data2'], 'Col2': [1, 2]})
    config = {
        'database': './tests/samples/test.db',
        'command': 'SELECT * from df_mock',
    }
    df = read(**config)
    assert df.equals(data)

def test_write_sql(mocker):
    mock_df = pd.DataFrame({'Col1': ['Data1', 'Data2']})
    config = {
        'df': mock_df,
        'database': './tests/temp/temp.db',
        'table': 'temp_mock'
    }
    write(**config)
    assert read(database='./tests/temp/temp.db', command='SELECT * from temp_mock').equals(mock_df)