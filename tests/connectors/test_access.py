import pandas as pd
from types import SimpleNamespace
from unittest.mock import Mock

from wrangles.connectors import access


class MockTables:
    def __init__(self, exists):
        self.exists = exists

    def fetchone(self):
        return object() if self.exists else None


class MockCursor:
    def __init__(self, table_exists=False):
        self.table_exists = table_exists
        self.executed = []
        self.executemany_calls = []

    def tables(self, table=None, tableType=None):
        return MockTables(self.table_exists)

    def execute(self, sql, params=()):
        self.executed.append((sql, params))
        return self

    def executemany(self, sql, rows):
        self.executemany_calls.append((sql, list(rows)))
        return self


class MockConnection:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_connection_string_requires_database_or_connection_string():
    try:
        access._connection_string()
        assert False
    except ValueError as e:
        assert str(e) == 'database or connection_string must be provided'


def test_read_sql(monkeypatch):
    data = pd.DataFrame({'Col1': ['Data1', 'Data2']})
    mock_connect = Mock(return_value=MockConnection(MockCursor()))
    monkeypatch.setattr(access, "_pyodbc", SimpleNamespace(connect=mock_connect))
    monkeypatch.setattr(pd, "read_sql", Mock(return_value=data))

    df = access.read(
        database='database.accdb',
        command='SELECT * from df_mock'
    )

    assert df.equals(data)
    mock_connect.assert_called_once_with('DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=database.accdb;')


def test_write_sql_creates_table_and_inserts(monkeypatch):
    cursor = MockCursor(table_exists=False)
    monkeypatch.setattr(access, "_pyodbc", SimpleNamespace(connect=Mock(return_value=MockConnection(cursor))))

    result = access.write(
        df=pd.DataFrame({'Col1': ['Data1', 'Data2'], 'Col2': [1, 2]}),
        database='database.accdb',
        table='WrWx'
    )

    assert result is None
    assert cursor.executed[0][0] == 'CREATE TABLE [WrWx] ([Col1] LONGTEXT, [Col2] INTEGER)'
    assert cursor.executemany_calls[0] == (
        'INSERT INTO [WrWx] ([Col1], [Col2]) VALUES (?, ?)',
        [('Data1', 1), ('Data2', 2)]
    )


def test_run(monkeypatch):
    cursor = MockCursor()
    connection = MockConnection(cursor)
    monkeypatch.setattr(access, "_pyodbc", SimpleNamespace(connect=Mock(return_value=connection)))

    result = access.run(
        database='database.accdb',
        command=['DELETE FROM WrWx WHERE Col1 = ?', 'UPDATE WrWx SET Col1 = ?'],
        params=('Data1',)
    )

    assert result is None
    assert cursor.executed == [
        ('DELETE FROM WrWx WHERE Col1 = ?', ('Data1',)),
        ('UPDATE WrWx SET Col1 = ?', ('Data1',))
    ]
    assert connection.committed
