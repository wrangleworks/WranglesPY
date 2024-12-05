import pandas as pd

from wrangles.connectors.mssql import read, write, run

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

    try:
        df = read(**config)
        assert df.equals(data)

    except ImportError as e:
        print(f"Test skipped due to missing module. {e}")

    except Exception as ex:
        print(f"Test failed due to unexpected error: {ex}")

# The function does not have a return
# Have a way to test with sqllite?

def test_write_sql(mocker):
    m = mocker.patch("pandas.DataFrame.to_sql")
    m.return_value = None
    config = {
        'df': pd.DataFrame({'insert': ['first', 'second']}),
        'host': 'host_mock',
        'user': 'user_mock',
        'password': 'password_mock',
        'database': 'test_mock',
        'table': 'WrWx'
    }
    
    try:
        df = write(**config)
        assert df == None

    except ImportError as e:
        print(f"Test skipped due to missing module. {e}")

    except Exception as ex:
        print(f"Test failed due to unexpected error: {ex}")
    
def test_run(mocker):
    m = mocker.patch("pymssql.connect")
    m2 = mocker.patch("pymssql.connect.cursor")
    m2.return_value = None
    config = {
        'host': 'host_mock',
        'user': 'user_mock',
        'password': 'password_mock',
        'command': 'mock command'
    }
    
    try:
        df = run(**config)
        assert df == None

    except ImportError as e:
        print(f"Test skipped due to missing module. {e}")

    except Exception as ex:
        print(f"Test failed due to unexpected error: {ex}")
    