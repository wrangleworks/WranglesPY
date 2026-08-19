import pandas as pd
import pytest
from wrangles.dataframe import DataFrame


class TestWranglesAccessor:
    """Tests for the .wrangles DataFrame accessor (issue #873)."""

    def test_select_sample_does_not_mutate_original(self):
        df = DataFrame({'col': range(20)})
        df_sample = df.wrangles.select.sample(rows=5)
        assert len(df) == 20
        assert len(df_sample) == 5

    def test_select_sample_returns_independent_object(self):
        df = DataFrame({'col': range(20)})
        df_sample = df.wrangles.select.sample(rows=5)
        assert df is not df_sample

    def test_convert_case_does_not_mutate_original(self):
        df = DataFrame({'name': ['alice', 'bob', 'carol']})
        df_upper = df.wrangles.convert.case(input='name', case='upper')
        assert df['name'].tolist() == ['alice', 'bob', 'carol']
        assert df_upper['name'].tolist() == ['ALICE', 'BOB', 'CAROL']

    def test_convert_case_returns_independent_object(self):
        df = DataFrame({'name': ['alice', 'bob']})
        df_upper = df.wrangles.convert.case(input='name', case='upper')
        assert df is not df_upper

    def test_split_dictionary_does_not_mutate_original(self):
        df = DataFrame({'data': [{'a': 1, 'b': 2}]})
        df_split = df.wrangles.split.dictionary(input='data')
        assert 'a' not in df.columns
        assert 'a' in df_split.columns

    def test_reassignment_updates_variable(self):
        """Reassigning df = df.wrangles... should still work correctly."""
        df = DataFrame({'col': ['hello', 'world']})
        df = df.wrangles.convert.case(input='col', case='upper')
        assert df['col'].tolist() == ['HELLO', 'WORLD']

    def test_chained_calls_do_not_mutate_original(self):
        """Multiple accessor calls on the same df should each leave it unchanged."""
        df = DataFrame({'col': ['hello', 'world', 'foo', 'bar', 'baz']})
        _ = df.wrangles.convert.case(input='col', case='upper')
        _ = df.wrangles.select.sample(rows=2)
        assert df['col'].tolist() == ['hello', 'world', 'foo', 'bar', 'baz']
        assert len(df) == 5
