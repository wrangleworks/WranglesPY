import pandas as pd

# Testing mysql connectors
from wrangles.connectors.mysql import read, write


def test_read_sql(mocker):
    data = pd.DataFrame({"Col1": ["Data1, Data2"]})
    m = mocker.patch("pandas.read_sql")
    m.return_value = data
    config = {
        "host": "host_mock",
        "user": "user_mock",
        "password": "password_mock",
        "database": "test_mock",
        "command": "SELECT * from df_mock",
    }
    df = read(**config)
    assert df.equals(data)


# The function does not have a return
# Have a way to test with sqllite?
def test_write_sql(mocker):
    m = mocker.patch("pandas.DataFrame.to_sql")
    m.return_value = None
    config = {
        "df": pd.DataFrame({"insert": ["first", "second"]}),
        "host": "host_mock",
        "user": "user_mock",
        "password": "password_mock",
        "database": "test_mock",
        "table": "WrWx",
    }
    df = write(**config)
    assert df == None
