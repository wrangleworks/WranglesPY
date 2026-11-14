"""Offline behavior at adopted text and structured-result boundaries."""
import importlib

import pandas as pd
import pytest
import requests

import wrangles


VALUES = [None, float('nan'), pd.NA, pd.NaT, '', '  ', 0, False, 'nan', 'None', '<NA>', 'A,B', [], {'x': 1}]
TEXT = ['None', 'nan', '<NA>', 'NaT', '', '  ', '0', 'False', 'nan', 'None', '<NA>', 'A,B', '[]', "{'x': 1}"]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail('Data contract boundary tests must not call a live service')

    monkeypatch.setattr(requests.sessions.Session, 'request', no_network)


def _source():
    index = [100 + 3 * row for row in range(len(VALUES))]
    return pd.DataFrame({
        'source': pd.Series(VALUES, index=index, dtype=object),
        'other': ['tail'] * len(VALUES),
    })


@pytest.mark.parametrize('entry', ['first_step', 'later_step', 'accessor'])
def test_split_text_preserves_python_stringification_and_entry_point(entry):
    source = _source()
    options = {'input': 'source', 'output': 'parts', 'char': ','}
    if entry == 'accessor':
        result = wrangles.DataFrame(source).wrangles.split.text(**options)
    else:
        steps = [] if entry == 'first_step' else [{'create.column': {'output': 'marker', 'value': 'x'}}]
        result = wrangles.recipe.run({'wrangles': steps + [{'split.text': options}]}, dataframe=source)
    text = TEXT if entry != 'later_step' else ['', '', '', ''] + TEXT[4:]
    assert result['parts'].tolist() == [value.split(',') for value in text]
    assert result.index.tolist() == source.index.tolist()
    if entry == 'accessor':
        pd.testing.assert_series_equal(source['source'], _source()['source'])


EXTRACT_OPTIONS = {
    'address': {'dataType': 'streets'},
    'attributes': {'attribute_type': 'length'},
    'brackets': {},
    'codes': {},
    'custom': {'model_id': 'synthetic'},
    'html': {'data_type': 'text'},
    'properties': {'property_type': 'Materials'},
}
EXTRACT_CASES = [
    (operation, shape)
    for operation in EXTRACT_OPTIONS
    for shape in ('single', 'columns', 'paired', 'joined')
    if not (operation == 'html' and shape == 'joined')
]


@pytest.mark.parametrize('operation,shape', EXTRACT_CASES)
def test_extraction_branches_prepare_text_without_casting_inputs(monkeypatch, operation, shape):
    extract_module = importlib.import_module('wrangles.recipe_wrangles.extract')
    calls = []

    def backend(values, *args, **kwargs):
        calls.append(list(values))
        assert all(isinstance(value, str) for value in values)
        return [['hit'] for _ in values]

    monkeypatch.setattr(extract_module._extract, operation, backend)
    source = _source()
    original = source['source'].copy()
    options = {'input': 'source', 'output': 'found', **EXTRACT_OPTIONS[operation]}
    if shape == 'columns':
        options.update(output=['found', 'unused'], output_format='columns')
    elif shape == 'paired':
        options.update(input=['source', 'other'], output=['found', 'other_found'])
    elif shape == 'joined':
        options['input'] = ['source', 'other']
    result = wrangles.recipe.run({'wrangles': [{f'extract.{operation}': options}]}, dataframe=source)

    if shape == 'paired' or (shape == 'joined' and operation == 'custom'):
        assert calls == [TEXT, ['tail'] * len(TEXT)]
    elif shape == 'joined':
        separator = ' AAA ' if operation in ('attributes', 'codes') else ' '
        assert calls == [[value + separator + 'tail' for value in TEXT]]
    else:
        assert calls == [TEXT]
    assert len(result) == len(source)
    assert 'found' in result
    if shape == 'columns':
        assert result['found'].tolist() == ['hit'] * len(source)
    pd.testing.assert_series_equal(source['source'], original)


def test_brackets_missing_markers_retain_existing_scalar_behavior():
    source = pd.DataFrame({'text': pd.Series(['(value)', None, float('nan'), pd.NA, '<NA>'], dtype=object)})
    result = wrangles.recipe.run({'wrangles': [{'extract.brackets': {
        'input': 'text', 'output': 'parts',
    }}]}, dataframe=source)
    assert result['parts'].tolist() == [['value'], [], [], ['NA'], ['NA']]


def test_custom_extract_distinct_models_prepare_each_input(monkeypatch):
    extract_module = importlib.import_module('wrangles.recipe_wrangles.extract')
    calls = []

    def backend(values, model_id, **kwargs):
        calls.append((model_id, list(values)))
        return [['hit'] for _ in values]

    monkeypatch.setattr(extract_module._extract, 'custom', backend)
    result = wrangles.recipe.run({'wrangles': [{'extract.custom': {
        'input': ['source', 'other'], 'output': ['first', 'second'],
        'model_id': ['one', 'two'],
    }}]}, dataframe=_source())
    assert calls == [('one', TEXT), ('two', ['tail'] * len(TEXT))]
    assert result['first'].tolist() == [['hit']] * len(TEXT)
    assert result['second'].tolist() == [['hit']] * len(TEXT)


def test_regex_retains_none_as_empty_and_other_marker_strings():
    source = pd.DataFrame({'text': pd.Series([None, float('nan'), pd.NA, 'None'], dtype=object)})
    result = wrangles.recipe.run({'wrangles': [{'extract.regex': {
        'input': 'text', 'output': 'parts', 'find': 'nan|None|NA',
    }}]}, dataframe=source)
    assert result['parts'].tolist() == [[], ['nan'], ['NA'], ['None']]


@pytest.mark.parametrize('method', ['difference', 'intersection', 'overlap'])
def test_compare_text_consumers_receive_python_strings(monkeypatch, method):
    compare_module = importlib.import_module('wrangles.recipe_wrangles.compare')
    calls = []

    def backend(input, **kwargs):
        calls.append(input)
        return ['matched'] * len(input)

    monkeypatch.setattr(compare_module._compare, 'overlap' if method == 'overlap' else 'contrast', backend)
    source = _source()
    result = wrangles.recipe.run({'wrangles': [{'compare.text': {
        'input': ['source', 'other'], 'output': 'compared', 'method': method,
    }}]}, dataframe=source)
    assert calls == [[[value, 'tail'] for value in TEXT]]
    assert result['compared'].tolist() == ['matched'] * len(source)


def test_similarity_keeps_typed_missing_values_and_false_zero(monkeypatch):
    compare_module = importlib.import_module('wrangles.recipe_wrangles.compare')
    calls = []

    def similarity(input, **kwargs):
        calls.extend(input)
        return [None] * len(input)

    monkeypatch.setattr(compare_module._compare, 'similarity', similarity)
    source = pd.DataFrame({'left': pd.Series([None, pd.NA, 0, False], dtype=object), 'right': ['x'] * 4})
    wrangles.recipe.run({'wrangles': [{'compare.text': {
        'input': ['left', 'right'], 'output': 'compared', 'method': 'similarity',
    }}]}, dataframe=source)
    assert calls[0][0] is None
    assert calls[1][0] is pd.NA
    assert type(calls[2][0]) is int and calls[2][0] == 0
    assert calls[3][0] is False


def test_similarity_scalar_missing_detection_preserves_false_and_zero():
    compare_module = importlib.import_module('wrangles.compare')
    assert compare_module.similarity([
        [None, 'x'], [float('nan'), 'x'], [pd.NA, 'x'], [pd.NaT, 'x'],
        [0, '0'], [False, 'False'], ['', 'x'], ['  ', 'x'],
    ]) == [None, None, None, None, 1.0, 1.0, None, None]


@pytest.mark.parametrize('dtype,values,expected', [
    ('float16', [1.23456789, float('nan')], ['1.234', 'nan']),
    ('float32', [1.23456789, float('nan')], ['1.2345679', 'nan']),
    ('datetime64[ns]', ['2026-01-01', None], ['2026-01-01', 'NaT']),
    ('timedelta64[ns]', ['1 day', None], ['1 days', 'NaT']),
])
def test_text_consumers_preserve_typed_column_formatting(monkeypatch, dtype, values, expected):
    extract_module = importlib.import_module('wrangles.recipe_wrangles.extract')
    calls = []

    def backend(values, *args, **kwargs):
        calls.append(list(values))
        return [['hit'] for _ in values]

    monkeypatch.setattr(extract_module._extract, 'address', backend)
    source = pd.DataFrame({'typed': pd.Series(values, dtype=dtype), 'flag': [True, False]})
    # Use the direct accessor so recipe-wide fillna does not obscure the input
    # formatting boundary for datetime/timedelta extension columns.
    result = wrangles.DataFrame(source).wrangles.extract.address(
        input=['typed', 'flag'], output='found', dataType='streets',
    )
    assert calls == [[value + ' ' + flag for value, flag in zip(expected, ['True', 'False'])]]
    assert result['found'].tolist() == [['hit'], ['hit']]


@pytest.mark.parametrize('operation', ['prefix', 'suffix', 'pad'])
def test_formatting_stringification_keeps_markers_and_row_labels(operation):
    source = _source()
    original = source['source'].copy()
    options = {'input': 'source', 'output': 'formatted'}
    if operation == 'pad':
        options.update(pad_length=8, side='left', char='_', skip_empty=True)
        expected = [value if not value.strip() else value.rjust(8, '_') for value in TEXT]
    else:
        options['value'] = 'X'
        expected = ['X' + value if operation == 'prefix' else value + 'X' for value in TEXT]
    result = wrangles.recipe.run({'wrangles': [{f'format.{operation}': options}]}, dataframe=source)
    assert result['formatted'].tolist() == expected
    assert result.index.tolist() == source.index.tolist()
    pd.testing.assert_series_equal(source['source'], original)


@pytest.mark.parametrize('operation,word', [('prefix', 'Xa'), ('suffix', 'aX')])
def test_affix_skip_empty_preserves_false_zero_and_empty_lists(operation, word):
    source = pd.DataFrame({'text': pd.Series([None, float('nan'), pd.NA, '', 0, False, [], 'a'], dtype=object)})
    result = wrangles.recipe.run({'wrangles': [{f'format.{operation}': {
        'input': 'text', 'output': 'formatted', 'value': 'X', 'skip_empty': True,
    }}]}, dataframe=source)
    assert result['formatted'].tolist() == ['', '', '', '', 0, False, [], word]
    assert type(result['formatted'].iloc[4]) is int
    assert result['formatted'].iloc[5] is False


def test_structured_extract_results_preserve_values_and_overwrite_text(monkeypatch):
    extract_module = importlib.import_module('wrangles.recipe_wrangles.extract')
    payloads = [{'flag': False, 'number': 0, 'missing': None}, {'items': [], 'value': 'None'}]
    monkeypatch.setattr(extract_module._extract, 'attributes', lambda *args, **kwargs: payloads)
    source = pd.DataFrame({'text': ['a', 'b'], 'payload': ['old', 'old']}, index=[7, 7])
    result = wrangles.recipe.run({'wrangles': [{'extract.attributes': {
        'input': 'text', 'output': 'payload', 'output_format': 'dictionary',
    }}]}, dataframe=source)
    assert result['payload'].tolist() == payloads
    assert result['payload'].iloc[0]['flag'] is False
    assert result['payload'].iloc[0]['missing'] is None
    assert result.index.tolist() == [7, 7]


def test_split_dictionary_lists_preserve_structured_values():
    source = pd.DataFrame({'data': [{'zero': 0, 'flag': False, 'missing': None, 'nested': []}]})
    result = wrangles.recipe.run({'wrangles': [{'split.dictionary': {
        'input': 'data', 'output_format': 'to_lists',
    }}]}, dataframe=source)
    assert result['Keys'].iloc[0] == ['zero', 'flag', 'missing', 'nested']
    assert result['Values'].iloc[0] == [0, False, None, []]
    assert result['Values'].iloc[0][1] is False


def test_tokenize_retains_list_cells_instead_of_stringifying_them():
    source = pd.DataFrame({'text': [['red bolt', 'steel'], 'blue nut']})
    result = wrangles.recipe.run({'wrangles': [{'split.tokenize': {
        'input': 'text', 'output': 'tokens',
    }}]}, dataframe=source)
    assert result['tokens'].tolist() == [['red', 'bolt', 'steel'], ['blue', 'nut']]
