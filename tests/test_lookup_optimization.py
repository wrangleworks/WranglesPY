"""
Unit tests for lookup optimization when all rows have the same value.
These tests verify that lookups are optimized when all rows need the same lookup value.
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import wrangles


class TestLookupOptimization:
    """
    Test lookup optimization for constant values
    """

    @patch('wrangles.recipe_wrangles.main._lookup')
    @patch('wrangles.recipe_wrangles.main._model')
    def test_lookup_constant_value_single_column(self, mock_model, mock_lookup):
        """
        Test that lookup is called only once when all rows have the same value
        and a single column is requested.
        """
        # Setup mock responses
        mock_model.return_value = {
            'purpose': 'lookup',
            'settings': {
                'columns': ['Value']
            }
        }
        mock_lookup.return_value = 42
        
        # Create a DataFrame with 1000 rows all having the same value
        df = pd.DataFrame({
            'input_col': ['constant'] * 1000
        })
        
        # Run the lookup wrangle
        from wrangles.recipe_wrangles.main import lookup
        result_df = lookup(
            df,
            input='input_col',
            output='output_col',
            model_id='12345678-1234-1234'
        )
        
        # Verify lookup was called only once with the constant value
        assert mock_lookup.call_count == 1
        # Check the first argument was the single value, not a list
        assert mock_lookup.call_args[0][0] == 'constant'
        
        # Verify all output rows have the expected value
        assert len(result_df) == 1000
        assert all(result_df['output_col'] == 42)

    @patch('wrangles.recipe_wrangles.main._lookup')
    @patch('wrangles.recipe_wrangles.main._model')
    def test_lookup_constant_value_multiple_columns(self, mock_model, mock_lookup):
        """
        Test that lookup is called only once when all rows have the same value
        and multiple columns are requested.
        """
        # Setup mock responses
        mock_model.return_value = {
            'purpose': 'lookup',
            'settings': {
                'columns': ['Value1', 'Value2']
            }
        }
        mock_lookup.return_value = [10, 20]
        
        # Create a DataFrame with 500 rows all having the same value
        df = pd.DataFrame({
            'input_col': ['constant'] * 500
        })
        
        # Run the lookup wrangle
        from wrangles.recipe_wrangles.main import lookup
        result_df = lookup(
            df,
            input='input_col',
            output=['Value1', 'Value2'],
            model_id='12345678-1234-1234'
        )
        
        # Verify lookup was called only once with the constant value
        assert mock_lookup.call_count == 1
        assert mock_lookup.call_args[0][0] == 'constant'
        
        # Verify all output rows have the expected values
        assert len(result_df) == 500
        # When multiple columns are requested, each column gets the corresponding value from the list
        assert 'Value1' in result_df.columns
        assert 'Value2' in result_df.columns
        assert all(result_df['Value1'] == 10)
        assert all(result_df['Value2'] == 20)

    @patch('wrangles.recipe_wrangles.main._lookup')
    @patch('wrangles.recipe_wrangles.main._model')
    def test_lookup_variable_values_not_optimized(self, mock_model, mock_lookup):
        """
        Test that lookup is called with all values when rows have different values.
        This ensures the optimization doesn't break the standard path.
        """
        # Setup mock responses
        mock_model.return_value = {
            'purpose': 'lookup',
            'settings': {
                'columns': ['Value']
            }
        }
        mock_lookup.return_value = [1, 2, 3, 4, 5]
        
        # Create a DataFrame with different values
        df = pd.DataFrame({
            'input_col': ['a', 'b', 'c', 'd', 'e']
        })
        
        # Run the lookup wrangle
        from wrangles.recipe_wrangles.main import lookup
        result_df = lookup(
            df,
            input='input_col',
            output='output_col',
            model_id='12345678-1234-1234'
        )
        
        # Verify lookup was called once with the list of all values
        assert mock_lookup.call_count == 1
        # Check that it was called with a list, not a single value
        assert mock_lookup.call_args[0][0] == ['a', 'b', 'c', 'd', 'e']
        
        # Verify output
        assert len(result_df) == 5

    @patch('wrangles.recipe_wrangles.main._lookup')
    @patch('wrangles.recipe_wrangles.main._model')
    def test_lookup_constant_value_dict_output(self, mock_model, mock_lookup):
        """
        Test lookup optimization when output is a dict (no specific columns requested).
        """
        # Setup mock responses
        mock_model.return_value = {
            'purpose': 'lookup',
            'settings': {
                'columns': ['Col1', 'Col2']
            }
        }
        mock_lookup.return_value = {'result': 'value'}
        
        # Create a DataFrame with 100 rows all having the same value
        df = pd.DataFrame({
            'input_col': ['same'] * 100
        })
        
        # Run the lookup wrangle with dict output
        from wrangles.recipe_wrangles.main import lookup
        result_df = lookup(
            df,
            input='input_col',
            output='output_col',
            model_id='12345678-1234-1234'
        )
        
        # Verify lookup was called only once
        assert mock_lookup.call_count == 1
        assert mock_lookup.call_args[0][0] == 'same'
        
        # Verify all output rows have the dict
        assert len(result_df) == 100
        assert all(result_df['output_col'] == {'result': 'value'})

    @patch('wrangles.recipe_wrangles.main._lookup')
    @patch('wrangles.recipe_wrangles.main._model')
    def test_lookup_constant_empty_dataframe(self, mock_model, mock_lookup):
        """
        Test that empty dataframe is handled correctly.
        """
        # Setup mock responses
        mock_model.return_value = {
            'purpose': 'lookup',
            'settings': {
                'columns': ['Value']
            }
        }
        
        # Create an empty DataFrame
        df = pd.DataFrame({
            'input_col': []
        })
        
        # Run the lookup wrangle
        from wrangles.recipe_wrangles.main import lookup
        result_df = lookup(
            df,
            input='input_col',
            output='output_col',
            model_id='12345678-1234-1234'
        )
        
        # Verify lookup was not called for empty dataframe
        assert mock_lookup.call_count == 0
        
        # Verify output column was added but empty
        assert 'output_col' in result_df.columns
        assert len(result_df) == 0
