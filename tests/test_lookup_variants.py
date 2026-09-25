"""Offline execution and contract checks for the explicit lookup operations."""
import importlib
import inspect
import json
from pathlib import Path
import runpy
import shutil
from types import SimpleNamespace

import jsonschema
import pandas as pd
import pytest
import requests
import yaml

import wrangles


MODEL_ID = '12345678-1234-1234'
VARIANTS = [('key', 'key', 1000), ('semantic', 'embedding', 20)]
lookup_module = importlib.import_module('wrangles.lookup')
recipe_main = importlib.import_module('wrangles.recipe_wrangles.main')


@pytest.fixture
def backend(monkeypatch):
    metadata = {'purpose': 'lookup', 'variant': 'key', 'settings': {'columns': ['Value']}}
    metadata_calls = []
    calls = []

    def model(model_id):
        metadata_calls.append(model_id)
        return metadata

    def batch(url, params, values, batch_size):
        calls.append((url, params, values, batch_size))
        count = params.get('n') or 1
        if count > 1:
            data = [[[{'Value': f'{value}:{i}'} for i in range(1, count + 1)]] for value in values]
        else:
            data = [[f'found:{value}'] for value in values]
        return {'columns': ['Value'], 'data': data}

    def no_network(*args, **kwargs):
        pytest.fail('Lookup tests must not call a live service')

    monkeypatch.setattr(requests.sessions.Session, 'request', no_network)
    monkeypatch.setattr(lookup_module._data, 'model', model)
    monkeypatch.setattr(recipe_main, '_model', model)
    monkeypatch.setattr(lookup_module._batching, 'batch_api_calls', batch)
    return SimpleNamespace(metadata=metadata, metadata_calls=metadata_calls, calls=calls)


@pytest.mark.parametrize('operation,variant,batch_size', VARIANTS)
@pytest.mark.parametrize('values,columns,expected', [
    ('one', None, {'Value': 'found:one'}),
    ('one', 'Value', 'found:one'),
    (['one', 'two'], ['Value'], [['found:one'], ['found:two']]),
    (['one', 'two'], None, [{'Value': 'found:one'}, {'Value': 'found:two'}]),
    ([], None, []),
])
def test_python_variants_preserve_shapes_and_arguments(backend, operation, variant, batch_size, values, columns, expected):
    backend.metadata['variant'] = variant
    result = getattr(wrangles.lookup, operation)(
        values, MODEL_ID, columns=columns, custom_option='kept'
    )
    assert result == expected
    assert backend.metadata_calls == [MODEL_ID]
    assert backend.calls == [(
        f'{wrangles.config.api_host}/wrangles/lookup',
        {'model_id': MODEL_ID, 'columns': '["Value"]', 'custom_option': 'kept'},
        values if isinstance(values, list) else [values], batch_size,
    )]


@pytest.mark.parametrize('operation,variant,batch_size', VARIANTS)
def test_python_n_keeps_match_dicts_and_batch_override(backend, operation, variant, batch_size):
    backend.metadata.update(variant=variant, batch_size=7)
    result = getattr(wrangles.lookup, operation)('one', MODEL_ID, columns='Value', n=2)
    assert result == [{'Value': 'one:1'}, {'Value': 'one:2'}]
    assert backend.calls[0][1] == {'model_id': MODEL_ID, 'columns': '["Value"]', 'n': 2}
    assert backend.calls[0][3] == 7


@pytest.mark.parametrize('layer', ['python', 'recipe'])
@pytest.mark.parametrize('operation,variant', [
    ('key', 'embedding'), ('semantic', 'key'),
    ('key', None), ('semantic', None),
    ('key', ''), ('semantic', ''),
    ('key', 'recipe'), ('semantic', 'semantic'),
])
def test_explicit_names_reject_incompatible_variants(backend, layer, operation, variant):
    backend.metadata['variant'] = variant
    with pytest.raises(ValueError, match=rf'lookup\.{operation} requires a model with variant'):
        if layer == 'python':
            getattr(wrangles.lookup, operation)('one', MODEL_ID)
        else:
            getattr(wrangles.recipe._recipe_wrangles.lookup, operation)(
                pd.DataFrame({'Raw': ['one']}), 'Raw', MODEL_ID, output='Result'
            )
    assert backend.metadata_calls == [MODEL_ID]
    assert backend.calls == []


@pytest.mark.parametrize('operation', ['key', 'semantic'])
def test_missing_variant_is_not_inferred(backend, operation):
    del backend.metadata['variant']
    with pytest.raises(ValueError, match='got None'):
        getattr(wrangles.lookup, operation)('one', MODEL_ID)
    assert backend.calls == []


@pytest.mark.parametrize('operation,variant,batch_size', VARIANTS)
@pytest.mark.parametrize('layer', ['python', 'recipe'])
def test_wrong_purpose_and_missing_model_fail_before_execution(backend, operation, variant, batch_size, layer):
    backend.metadata.update(purpose='extract', variant=variant)

    def call():
        if layer == 'python':
            return getattr(wrangles.lookup, operation)('one', MODEL_ID)
        return getattr(wrangles.recipe._recipe_wrangles.lookup, operation)(
            pd.DataFrame({'Raw': ['one']}), 'Raw', MODEL_ID
        )

    with pytest.raises(ValueError, match='Using extract model_id'):
        call()
    backend.metadata.clear()
    backend.metadata['message'] = 'error'
    with pytest.raises(ValueError, match='Incorrect model_id'):
        call()
    assert backend.calls == []


@pytest.mark.parametrize('variant,batch_size', [('key', 1000), ('embedding', 20), (None, 1000), ('recipe', 1000)])
def test_legacy_lookup_keeps_model_dispatch(backend, variant, batch_size):
    backend.metadata['variant'] = variant
    assert wrangles.lookup('one', MODEL_ID, columns='Value') == 'found:one'
    result = wrangles.recipe.run(
        {'wrangles': [{'lookup': {'input': 'Raw', 'output': 'Value', 'model_id': MODEL_ID}}]},
        dataframe=pd.DataFrame({'Raw': ['one', 'two']}),
    )
    assert result.to_dict('list') == {'Raw': ['one', 'two'], 'Value': ['found:one', 'found:two']}
    assert [call[3] for call in backend.calls] == [batch_size, batch_size]


def test_legacy_n_and_passthrough_stay_supported(backend):
    expected = [{'Value': 'one:1'}, {'Value': 'one:2'}]
    assert wrangles.lookup('one', MODEL_ID, n=2, custom_option='kept') == expected
    result = wrangles.recipe.run(
        {'wrangles': [{'lookup': {
            'input': 'Raw', 'output': 'Result', 'model_id': MODEL_ID,
            'n': 2, 'custom_option': 'kept',
        }}]},
        dataframe=pd.DataFrame({'Raw': ['one']}),
    )
    assert result.to_dict('list') == {'Raw': ['one'], 'Result': [expected]}
    assert [call[1] for call in backend.calls] == [
        {'model_id': MODEL_ID, 'columns': '["Value"]', 'n': 2, 'custom_option': 'kept'},
        {'model_id': MODEL_ID, 'columns': '["Value"]', 'n': 2, 'custom_option': 'kept'},
    ]


@pytest.mark.parametrize('operation,variant,batch_size', VARIANTS)
@pytest.mark.parametrize('mode,expected_inputs', [
    ('by_row', [['one', 'one', 'two']]),
    ('by_dataframe', [['one', 'two']]),
    ('by_matrix', [['one'], ['two']]),
])
def test_recipe_variants_execute_existing_modes(backend, operation, variant, batch_size, mode, expected_inputs):
    backend.metadata['variant'] = variant
    result = wrangles.recipe.run(
        {'wrangles': [{f'lookup.{operation}': {
            'input': 'Raw', 'output': {'Value': 'Result'}, 'model_id': MODEL_ID,
            'lookup_mode': mode, 'matrix_variables': ['Group'], 'custom_option': 'kept',
        }}]},
        dataframe=pd.DataFrame({'Raw': ['one', 'one', 'two'], 'Group': ['a', 'a', 'b']}),
    )
    assert result.to_dict('list') == {
        'Raw': ['one', 'one', 'two'], 'Group': ['a', 'a', 'b'],
        'Result': ['found:one', 'found:one', 'found:two'],
    }
    assert [call[2] for call in backend.calls] == expected_inputs
    assert all(call[1] == {
        'model_id': MODEL_ID, 'columns': '["Value"]', 'custom_option': 'kept'
    } for call in backend.calls)
    assert [call[3] for call in backend.calls] == [batch_size] * len(expected_inputs)


@pytest.mark.parametrize('operation,variant,batch_size', VARIANTS)
def test_recipe_n_and_empty_behavior(backend, operation, variant, batch_size):
    backend.metadata['variant'] = variant
    params = {'input': 'Raw', 'output': 'Match *', 'model_id': MODEL_ID, 'n': 2}
    result = wrangles.recipe.run(
        {'wrangles': [{f'lookup.{operation}': params}]},
        dataframe=pd.DataFrame({'Raw': ['one', 'two']}),
    )
    assert result.to_dict('list') == {
        'Raw': ['one', 'two'],
        'Match 1': [{'Value': 'one:1'}, {'Value': 'two:1'}],
        'Match 2': [{'Value': 'one:2'}, {'Value': 'two:2'}],
    }
    assert backend.calls[0][1]['n'] == 2
    backend.calls.clear()
    backend.metadata_calls.clear()
    empty = getattr(wrangles.recipe._recipe_wrangles.lookup, operation)(
        pd.DataFrame({'Raw': []}), **params
    )
    assert empty.to_dict('list') == {'Raw': [], 'Match 1': [], 'Match 2': []}
    assert backend.metadata_calls == []
    assert backend.calls == []


@pytest.mark.parametrize('operation', ['key', 'semantic'])
@pytest.mark.parametrize('mode', ['by_dataframe', 'by_matrix'])
def test_explicit_recipe_rejects_silently_ignored_n(backend, operation, mode):
    with pytest.raises(ValueError, match='n is only supported with lookup_mode=by_row'):
        getattr(wrangles.recipe._recipe_wrangles.lookup, operation)(
            pd.DataFrame({'Raw': ['one']}), 'Raw', MODEL_ID, n=2, lookup_mode=mode
        )
    assert backend.metadata_calls == []
    assert backend.calls == []


@pytest.mark.parametrize('operation,variant,batch_size', VARIANTS)
def test_dataframe_accessor_preserves_source(backend, operation, variant, batch_size):
    backend.metadata['variant'] = variant
    source = wrangles.DataFrame({'Raw': ['one', 'two']})
    result = getattr(source.wrangles.lookup, operation)('Raw', MODEL_ID, output='Value')
    legacy = source.wrangles.lookup(input='Raw', model_id=MODEL_ID, output='Value')
    assert result.to_dict('list') == {'Raw': ['one', 'two'], 'Value': ['found:one', 'found:two']}
    assert legacy.equals(result)
    assert source.to_dict('list') == {'Raw': ['one', 'two']}


@pytest.mark.parametrize('operation,variant,batch_size', VARIANTS)
def test_recipe_where_only_executes_selected_rows(backend, operation, variant, batch_size):
    backend.metadata['variant'] = variant
    result = wrangles.recipe.run(
        {'wrangles': [{f'lookup.{operation}': {
            'input': 'Raw', 'output': 'Value', 'model_id': MODEL_ID,
            'where': 'Apply = true',
        }}]},
        dataframe=pd.DataFrame({'Raw': ['one', 'two'], 'Apply': [True, False]}),
    )
    assert result.to_dict('list') == {
        'Raw': ['one', 'two'], 'Apply': [True, False], 'Value': ['found:one', ''],
    }
    assert [call[2] for call in backend.calls] == [['one']]


def test_generated_schema_preserves_legacy_and_explicit_contracts(tmp_path, monkeypatch, backend):
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / 'schema/recipe_base_schema.json', tmp_path / 'recipe_base_schema.json')
    monkeypatch.chdir(tmp_path)

    def schema_response(url):
        assert url == 'http://json-schema.org/draft-07/schema#'
        return SimpleNamespace(json=lambda: jsonschema.Draft7Validator.META_SCHEMA)

    monkeypatch.setattr(requests, 'get', schema_response)
    runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
    generated = json.loads((tmp_path / 'schema.json').read_text())
    contracts = generated['$defs']['wrangles']['items']['properties']
    assert {'lookup', 'lookup.key', 'lookup.semantic'} <= contracts.keys()
    assert contracts['lookup']['description'] == (
        'Deprecated: Use lookup.key for key lookup models or lookup.semantic '
        'for semantic lookup models instead. Lookup values from a saved lookup wrangle.'
    )
    for operation, variant, _ in VARIANTS:
        method = getattr(wrangles.recipe._recipe_wrangles.lookup, operation)
        contract = contracts[f'lookup.{operation}']
        raw = yaml.safe_load(method.__doc__)
        assert f'stored variant {variant}' in contract['description']
        assert contract['required'] == ['input', 'model_id']
        assert set(inspect.signature(method).parameters) - {'df', 'kwargs'} <= contract['properties'].keys()
        for name in ['output', 'lookup_mode', 'n']:
            assert contract['properties'][name]['default'] == inspect.signature(method).parameters[name].default
        jsonschema.Draft7Validator.check_schema(raw)
        validator = jsonschema.Draft7Validator(raw)
        validator.validate(raw['examples'][0])
        with pytest.raises(jsonschema.ValidationError, match='model_id'):
            validator.validate({'input': 'Raw'})
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({'input': ['First', 'Second'], 'model_id': MODEL_ID})
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({'input': 'Raw', 'model_id': MODEL_ID, 'n': 2, 'lookup_mode': 'by_dataframe'})
        with pytest.raises(jsonschema.ValidationError, match='matrix_variables'):
            validator.validate({'input': 'Raw', 'model_id': MODEL_ID, 'lookup_mode': 'by_matrix'})
        validator.validate({
            'input': 'Raw', 'model_id': MODEL_ID, 'lookup_mode': 'by_matrix',
            'matrix_variables': ['Group'], 'n': None,
        })
        assert {'if', 'where', 'where_params'} <= contract['properties'].keys()
    assert backend.calls == []
