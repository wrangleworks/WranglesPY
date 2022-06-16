import pandas as pd

from wrangles.connectors.postgres import _psql_insert_copy, read, write

def test_read_sql(mocker):
    data = pd.DataFrame({'Col1': ['Data1, Data2']})
    m = mocker.patch("pandas.read_sql")
    m.return_value = data
    config = {
        'host': 'host_mock',
        'user': 'user_mock',
        'password': 'password_mock',
        'database': 'test_mock',
        'command': 'SELECT * from df_mock',
    }
    df = read(**config)
    assert df.equals(data)
    
# The function does not have a return
# Have a way to test with sqllite?

# Action = Insert
def test_write_sql_insert(mocker):
    m = mocker.patch("pandas.DataFrame.to_sql")
    m.return_value = None
    config = {
        'df': pd.DataFrame({'insert': ['first', 'second']}),
        'host': 'host_mock',
        'user': 'user_mock',
        'password': 'password_mock',
        'database': 'test_mock',
        'table': 'WrWx',
    }
    df = write(**config)
    assert df == None
    
# Action = Fail
def test_write_sql_fail(mocker):
    m = mocker.patch("pandas.DataFrame.to_sql")
    m.return_value = None
    config = {
        'df': pd.DataFrame({'insert': ['first', 'second']}),
        'host': 'host_mock',
        'user': 'user_mock',
        'password': 'password_mock',
        'database': 'test_mock',
        'table': 'WrWx',
        'action': 'FAIL'
    }
    df = write(**config)
    assert df == None
    
# Action = Replace
def test_write_sql_replace(mocker):
    m = mocker.patch("pandas.DataFrame.to_sql")
    m.return_value = None
    config = {
        'df': pd.DataFrame({'insert': ['first', 'second']}),
        'host': 'host_mock',
        'user': 'user_mock',
        'password': 'password_mock',
        'database': 'test_mock',
        'table': 'WrWx',
        'action': 'REPLACE'
    }
    df = write(**config)
    assert df == None
    
# Action = experimental
def test_write_sql_experimental(mocker):
    m = mocker.patch("pandas.DataFrame.to_sql")
    m.return_value = None
    config = {
        'df': pd.DataFrame({'insert': ['first', 'second']}),
        'host': 'host_mock',
        'user': 'user_mock',
        'password': 'password_mock',
        'database': 'test_mock',
        'table': 'WrWx',
        'action': 'EXPERIMENTAL'
    }
    df = write(**config)
    assert df == None
    

def test_psql_insert_copy(mocker):
    m = mocker.patch("wrangles.connectors.postgres.write")
    m2 = mocker.patch("psycopg2.connect")
    config = {
        'table': m,
        'conn': m2,
        'keys': 'keys_mock',
        'data_iter': 'data_iter_mock'
    }
    df = _psql_insert_copy(**config)
    assert df == None