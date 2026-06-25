import importlib.util

import pandas as pd
import pytest

from wrangles.connectors import duckdb


pytestmark = pytest.mark.skipif(
    importlib.util.find_spec('duckdb') is None,
    reason='duckdb optional dependency is not installed'
)


def test_read_sql(tmp_path):
    database = tmp_path / 'test.duckdb'
    duckdb.run(
        database=str(database),
        command='CREATE TABLE df_mock AS SELECT \'Data1\' AS Col1, 1 AS Col2 UNION ALL SELECT \'Data2\', 2'
    )

    df = duckdb.read(
        database=str(database),
        command='SELECT * from df_mock ORDER BY Col2'
    )

    assert df.equals(
        pd.DataFrame(
            {
                'Col1': ['Data1', 'Data2'],
                'Col2': pd.array([1, 2], dtype='int32')
            }
        )
    )


def test_write_sql(tmp_path):
    database = tmp_path / 'write.duckdb'
    df = pd.DataFrame({'Col1': ['Data1', 'Data2']})

    duckdb.write(
        df=df,
        database=str(database),
        table='temp_mock'
    )

    assert duckdb.read(
        database=str(database),
        command='SELECT * from temp_mock'
    ).equals(df)


def test_run(tmp_path):
    database = tmp_path / 'run.duckdb'
    df = pd.DataFrame({'Col1': ['Data1', 'Data2']})
    duckdb.write(
        df=df,
        database=str(database),
        table='test_table'
    )

    duckdb.run(
        database=str(database),
        command='CREATE TABLE test_table_copy AS SELECT * FROM test_table'
    )

    df_copy = duckdb.read(
        database=str(database),
        command='SELECT * from test_table_copy'
    )

    assert df.equals(df_copy)
