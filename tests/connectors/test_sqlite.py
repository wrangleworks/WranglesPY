import pandas as pd

# Testing sqlite connectors
from wrangles.connectors.sqlite import read, write

def test_read_sql(mocker):
    data = pd.DataFrame({'Col1': ['Data1, Data2']})
    m = mocker.patch("pandas.read_sql")
    m.return_value = data
    config = {
        'database': 'database.db',
        'command': 'SELECT * from df_mock',
    }
    df = read(**config)
    assert df.equals(data)

def test_write_sql(mocker):
    m = mocker.patch("pandas.DataFrame.to_sql")
    m.return_value = None
    config = {
        'df': pd.DataFrame({'insert': ['first', 'second']}),
        'database': 'database.db',
        'table': 'WrWx'
    }
    df = write(**config)
    assert df == None