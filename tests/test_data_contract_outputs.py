"""Native structured values and positional model-result writes stay explicit."""

import importlib
import json

import numpy as np
import pandas as pd
import pytest

import wrangles


@pytest.mark.parametrize('future', [False, True])
@pytest.mark.parametrize('include_empty', [False, True])
def test_dictionary_output_preserves_literal_markers_and_native_values(future, include_empty):
    values = [True, False, 'True', 'False', 'None', None, np.nan, pd.NA, '', 0]
    source = pd.DataFrame({'value': pd.Series(values, dtype=object)})
    with pd.option_context('future.infer_string', future, 'mode.copy_on_write', future):
        result = wrangles.recipe.run({'wrangles': [{'merge.to_dict': {
            'input': ['value'], 'output': 'payload', 'include_empty': include_empty,
        }}]}, dataframe=source)
    payload = result['payload'].tolist()
    expected = [{'value': value} for value in [True, False, 'True', 'False', 'None', None, None, None]]
    expected += [{'value': ''}, {'value': 0}] if include_empty else [{}, {}]
    assert payload == expected
    assert payload[0]['value'] is True and payload[1]['value'] is False
    assert json.loads(json.dumps(payload, allow_nan=False)) == expected


@pytest.mark.parametrize('skip_empty', [False, True])
def test_key_value_pairs_preserve_structures_and_normalize_nested_nulls(skip_empty):
    nested = {'null': np.nan, 'zero': 0, 'false': False, 'literal': 'None'}
    source = pd.DataFrame({
        'key': ['zero', 'false', 'literal', 'nested', 'missing', 'blank'],
        'value': [0, False, 'False', nested, pd.NA, '  '],
    })
    result = wrangles.recipe.run({'wrangles': [{'merge.key_value_pairs': {
        'input': {'key': 'value'}, 'output': 'payload', 'skip_empty': skip_empty,
    }}]}, dataframe=source)
    payload = result['payload'].tolist()
    assert payload[:4] == [
        {'zero': 0}, {'false': False}, {'literal': 'False'},
        {'nested': {'null': None, 'zero': 0, 'false': False, 'literal': 'None'}},
    ]
    assert payload[4:] == ([{}, {}] if skip_empty else [{'missing': None}, {'blank': '  '}])
    assert np.isnan(nested['null'])
    json.dumps(payload, allow_nan=False)


def test_key_value_pairs_does_not_collapse_distinct_missing_keys():
    """Value normalization must not merge NaN and None keys into one pair."""
    from wrangles.recipe_wrangles.merge import key_value_pairs

    missing_key = float('nan')
    source = pd.DataFrame({
        'key_a': pd.Series([missing_key], dtype=object), 'value_a': ['first'],
        'key_b': pd.Series([None], dtype=object), 'value_b': ['second'],
    })
    result = key_value_pairs(
        source, {'key_a': 'value_a', 'key_b': 'value_b'}, 'payload',
    )
    payload = result['payload'].iloc[0]
    assert len(payload) == 2
    assert payload[None] == 'second'
    assert [(key, value) for key, value in payload.items() if key is not None][0][1] == 'first'
    assert any(isinstance(key, float) and np.isnan(key) for key in payload)


@pytest.mark.parametrize('future', [False, True])
@pytest.mark.parametrize('reverse', [False, True])
def test_matrix_lookup_mixed_results_preserve_duplicate_and_nondefault_indexes(monkeypatch, future, reverse):
    main = importlib.import_module('wrangles.recipe_wrangles.main')
    monkeypatch.setattr(main, '_model', lambda model_id: {
        'purpose': 'lookup', 'settings': {'columns': ['Value']},
    })
    monkeypatch.setattr(main, '_lookup', lambda values, model_id, **kwargs: [
        ['text' if value == 'one' else 7] for value in values
    ])
    permutations = [{'Group': 'a'}, {'Group': 'b'}]
    if reverse:
        permutations.reverse()
    monkeypatch.setattr(main, '_define_permutations', lambda *args, **kwargs: permutations)
    source = pd.DataFrame({'Raw': ['one', 'two', 'one'], 'Group': ['a', 'b', 'a']}, index=[40, 40, 10])
    with pd.option_context('future.infer_string', future, 'mode.copy_on_write', future):
        result = wrangles.recipe.run({'wrangles': [{'lookup': {
            'input': 'Raw', 'output': {'Value': 'Result'}, 'model_id': 'synthetic',
            'lookup_mode': 'by_matrix', 'matrix_variables': ['Group'],
        }}]}, dataframe=source)
    assert result.index.tolist() == [40, 40, 10]
    assert result['Result'].tolist() == ['text', 7, 'text']
