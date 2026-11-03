import importlib
from copy import deepcopy
import logging
import json
from pathlib import Path
import runpy
import shutil
from types import SimpleNamespace

import jsonschema
import requests

import pandas as pd
import pytest
import yaml

import wrangles


class TestStandardizeSerializationAliases:
    """Issue #1256: existing serialization behavior through both namespaces."""

    CASES = {
        'to_json': {
            'raw': [{'word': 'café'}, [1, 2], 'plain'],
            'values': ['{"word": "café"}', '[1, 2]', '["plain"]'],
            'other': [{'number': 2}, ['x'], False],
            'other_values': ['{"number": 2}', '["x"]', '[false]'],
        },
        'from_json': {
            'raw': ['{"word":"café"}', '[1,2]', '"plain"'],
            'values': [{'word': 'café'}, [1, 2], 'plain'],
            'other': ['{"number":2}', '["x"]', 'false'],
            'other_values': [{'number': 2}, ['x'], False],
        },
        'to_yaml': {
            'raw': [{'word': 'café'}, [1, 2], {'keep': True}],
            'values': ['word: café\n', '- 1\n- 2\n', 'keep: true\n'],
            'other': [{'number': 2}, ['x'], {'flag': False}],
            'other_values': ['number: 2\n', '- x\n', 'flag: false\n'],
        },
        'from_yaml': {
            'raw': ['word: café', '- 1\n- 2', 'plain'],
            'values': [{'word': 'café'}, [1, 2], 'plain'],
            'other': ['number: 2', '- x', 'false'],
            'other_values': [{'number': 2}, ['x'], False],
        },
    }

    @pytest.fixture(autouse=True)
    def block_http(self, monkeypatch):
        def unexpected(*args, **kwargs):
            pytest.fail('Serialization recipes must not call HTTP services')
        monkeypatch.setattr(requests.sessions.Session, 'request', unexpected)

    @pytest.fixture(params=['standardize', 'convert'])
    def namespace(self, request):
        return request.param

    @pytest.fixture(params=list(CASES))
    def serialization_case(self, request):
        name = request.param
        spec = deepcopy(self.CASES[name])
        frame = pd.DataFrame({'raw': spec['raw'], 'Keep': [3, 1, 2]}, index=pd.Index([7, 2, 9], name='row'))
        return name, spec, frame

    @staticmethod
    def run_alias(namespace, name, frame, **params):
        return wrangles.recipe.run({'wrangles': [{f'{namespace}.{name}': params}]}, dataframe=frame.copy(deep=True))

    @pytest.mark.parametrize('mode', ['scalar', 'overwrite', 'list', 'wildcard', 'list_overwrite'])
    def test_columns_outputs_and_complete_frame(self, namespace, serialization_case, mode):
        name, spec, frame = serialization_case
        frame['raw2'] = spec['other']
        expected = frame.copy(deep=True)
        if mode == 'scalar':
            params = {'input': 'raw', 'output': 'out'}
            expected['out'] = spec['values']
        elif mode == 'overwrite':
            params = {'input': 'raw'}
            expected['raw'] = spec['values']
        elif mode == 'list_overwrite':
            params = {'input': ['raw', 'raw2']}
            expected['raw'] = spec['values']
            expected['raw2'] = spec['other_values']
        else:
            params = {'input': 'raw*' if mode == 'wildcard' else ['raw', 'raw2'], 'output': ['first', 'second']}
            expected['first'] = spec['values']
            expected['second'] = spec['other_values']
        pd.testing.assert_frame_equal(self.run_alias(namespace, name, frame, **params), expected)

    @pytest.mark.parametrize('condition', ['plain', 'list_params', 'dict_params', 'no_rows'])
    @pytest.mark.parametrize('overwrite', [False, True])
    def test_where_and_bound_parameters_preserve_other_rows(self, namespace, serialization_case, condition, overwrite):
        name, spec, frame = serialization_case
        controls = {
            'plain': {'where': 'Keep = 3'},
            'list_params': {'where': 'Keep = ?', 'where_params': [3]},
            'dict_params': {'where': 'Keep = :value', 'where_params': {'value': 3}},
            'no_rows': {'where': 'Keep > 100'},
        }[condition]
        expected = frame.copy(deep=True)
        output = 'raw' if overwrite else 'out'
        if not overwrite:
            expected[output] = ''
        if condition != 'no_rows':
            expected.at[7, output] = spec['values'][0]
        pd.testing.assert_frame_equal(self.run_alias(namespace, name, frame, input='raw', output=output, **controls), expected)

    @pytest.mark.parametrize('enabled', [True, False])
    def test_if_true_and_false(self, namespace, serialization_case, enabled):
        name, spec, frame = serialization_case
        expected = frame.assign(out=spec['values']) if enabled else frame
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, name, frame, input='raw', output='out', **{'if': enabled}), expected,
        )

    @pytest.mark.parametrize('overwrite', [False, True])
    def test_empty_frame_preserves_shape_and_dtype(self, namespace, serialization_case, overwrite):
        name, _, frame = serialization_case
        frame = frame.head(0)
        output = 'raw' if overwrite else 'out'
        expected = frame.copy()
        expected[output] = pd.Series(index=frame.index, dtype='float64')
        pd.testing.assert_frame_equal(self.run_alias(namespace, name, frame, input='raw', output=output), expected)

    def test_mismatched_output_lists_keep_existing_error(self, namespace, serialization_case):
        name, spec, frame = serialization_case
        with pytest.raises(ValueError, match='The lists for input and output must be the same length'):
            self.run_alias(namespace, name, frame, input='raw', output=['one', 'two'])

    @pytest.mark.parametrize('name', ['to_json', 'to_yaml'])
    @pytest.mark.parametrize('rows', [0, 1, 2])
    def test_many_to_one_retains_current_assignment_behavior(self, namespace, name, rows):
        frame = pd.DataFrame({'first': ['A'] * rows, 'second': [2] * rows})
        if rows != 1:
            with pytest.raises(ValueError, match='Columns must be same length as key'):
                self.run_alias(namespace, name, frame, input=['first', 'second'], output='out')
        else:
            text = '{"first": "A", "second": 2}' if name == 'to_json' else 'first: A\nsecond: 2\n'
            pd.testing.assert_frame_equal(
                self.run_alias(namespace, name, frame, input=['first', 'second'], output='out'), frame.assign(out=[text]),
            )

    @pytest.mark.parametrize('name', ['from_json', 'from_yaml'])
    def test_decoding_falsy_null_malformed_and_empty_values(self, namespace, name):
        fallback = {'fallback': True}
        values = ['', None, '[', 'null', '0', 'false', '[]', '{}', '""']
        frame = pd.DataFrame({'raw': values})
        decoded = [fallback, fallback, fallback, '' if name == 'from_json' else fallback, 0, False, [], {}, '']
        expected = pd.DataFrame({'raw': ['' if value is None else value for value in values], 'out': decoded})
        result = self.run_alias(namespace, name, frame, input='raw', output='out', default=fallback)
        pd.testing.assert_frame_equal(result, expected)
        assert type(result.at[4, 'out']) is int
        assert type(result.at[5, 'out']) is bool

    @pytest.mark.parametrize('name', ['from_json', 'from_yaml'])
    @pytest.mark.parametrize('value', ['[', None])
    def test_invalid_text_without_default_raises(self, namespace, name, value):
        with pytest.raises(ValueError, match=f'Unable to load all rows as {name[5:].upper()}'):
            self.run_alias(namespace, name, pd.DataFrame({'raw': [value]}), input='raw', output='out')

    @pytest.mark.parametrize('name', ['from_json', 'from_yaml'])
    @pytest.mark.parametrize('default,first,second', [
        ([], [], []), ([0], 0, 0), ([{'a': 1}, ['b']], {'a': 1}, ['b']),
    ])
    def test_per_column_and_broadcast_defaults(self, namespace, name, default, first, second):
        frame = pd.DataFrame({'raw': ['['], 'raw2': ['[']}, index=[7])
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, name, frame, input=['raw', 'raw2'], output=['first', 'second'], default=default),
            frame.assign(first=[first], second=[second]),
        )

    @pytest.mark.parametrize('name', ['from_json', 'from_yaml'])
    def test_invalid_default_list_length_keeps_context(self, namespace, name):
        with pytest.raises(ValueError, match=f'same length as input/output for convert.{name}'):
            self.run_alias(namespace, name, pd.DataFrame({'raw': ['['], 'raw2': ['[']}), input=['raw', 'raw2'], default=[1, 2, 3])

    def test_json_scalar_wrapping_numpy_and_unicode(self, namespace):
        import numpy as np

        frame = pd.DataFrame({'raw': pd.Series([None, 7, False, '', np.array([1, 2]), np.int64(8), np.float32(2.5)], dtype=object)})
        values = ['[null]', '[7]', '[false]', '[""]', '[1, 2]', '[8]', '[2.5]']
        expected = frame.copy(deep=True)
        expected.at[0, 'raw'] = ''
        expected['out'] = values
        pd.testing.assert_frame_equal(self.run_alias(namespace, 'to_json', frame, input='raw', output='out'), expected)

    def test_yaml_scalars_retain_safe_dumper_representation(self, namespace):
        frame = pd.DataFrame({'raw': pd.Series([None, 7, False, ''], dtype=object)})
        result = self.run_alias(namespace, 'to_yaml', frame, input='raw', output='out')
        assert [value.removesuffix('...\n') for value in result['out']] == ['null\n', '7\n', 'false\n', "''\n"]
        assert [yaml.safe_load(value) for value in result['out']] == [None, 7, False, '']

    def test_json_serialization_kwargs(self, namespace):
        frame = pd.DataFrame({'raw': [{'z': 'Київ', 'a': 1}]})
        result = self.run_alias(namespace, 'to_json', frame, input='raw', output='out', ensure_ascii=True, sort_keys=True, separators=[',', ':'])
        assert result.at[0, 'out'] == '{"a":1,"z":"\\u041a\\u0438\\u0457\\u0432"}'

    def test_yaml_serialization_kwargs(self, namespace):
        frame = pd.DataFrame({'raw': [{'z': 'Київ', 'a': 1}]})
        result = self.run_alias(namespace, 'to_yaml', frame, input='raw', output='out', sort_keys=True, allow_unicode=False, default_flow_style=True)
        text = result.at[0, 'out']
        assert text.startswith('{a: 1, z: ')
        assert 'Київ' not in text
        assert yaml.safe_load(text) == {'a': 1, 'z': 'Київ'}

    def test_json_loading_kwargs_and_strict_errors(self, namespace):
        frame = pd.DataFrame({'raw': ['"line\nbreak"']})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'from_json', frame, input='raw', output='out', strict=False), frame.assign(out=['line\nbreak']),
        )
        with pytest.raises(ValueError, match='Unable to load all rows as JSON'):
            self.run_alias(namespace, 'from_json', frame, input='raw')
        with pytest.raises(ValueError, match='Out of range float values'):
            self.run_alias(namespace, 'to_json', pd.DataFrame({'raw': [float('nan')]}), input='raw', allow_nan=False)

    def test_yaml_loader_remains_safe(self, namespace):
        frame = pd.DataFrame({'raw': ['!!python/tuple [1, 2]']})
        with pytest.raises(ValueError, match='Unable to load all rows as YAML'):
            self.run_alias(namespace, 'from_yaml', frame, input='raw')
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'from_yaml', frame, input='raw', output='out', default={}), frame.assign(out=[{}]),
        )

    def test_direct_modules_share_canonical_implementations(self, serialization_case):
        name, spec, frame = serialization_case
        canonical = importlib.import_module('wrangles.recipe_wrangles.standardize')
        legacy = importlib.import_module('wrangles.recipe_wrangles.convert')
        implementation = getattr(canonical, name)
        assert implementation.__module__ == canonical.__name__
        assert getattr(legacy, name) is implementation
        assert getattr(wrangles.recipe._recipe_wrangles.standardize, name) is implementation
        for module in (canonical, legacy):
            pd.testing.assert_frame_equal(getattr(module, name)(frame.copy(deep=True), input='raw', output='out'), frame.assign(out=spec['values']))

    @pytest.mark.parametrize('name', ['from_json', 'from_yaml'])
    def test_mutable_fallback_identity_is_preserved(self, name):
        canonical = importlib.import_module('wrangles.recipe_wrangles.standardize')
        fallback = {'items': []}
        result = getattr(canonical, name)(pd.DataFrame({'raw': ['[', '[']}), input='raw', output='out', default=fallback)
        assert result.at[0, 'out'] is fallback
        assert result.at[1, 'out'] is fallback

    def test_dataframe_accessors_preserve_original(self, namespace, serialization_case):
        name, spec, frame = serialization_case
        frame = wrangles.DataFrame(frame)
        original = frame.copy(deep=True)
        target = getattr(frame.wrangles, namespace)
        pd.testing.assert_frame_equal(getattr(target, name)(input='raw', output='out'), frame.assign(out=spec['values']))
        pd.testing.assert_frame_equal(frame, original)

    def test_callable_namespace_and_parse_are_preserved(self):
        namespace = wrangles.recipe._recipe_wrangles
        canonical = importlib.import_module('wrangles.recipe_wrangles.standardize')
        main = importlib.import_module('wrangles.recipe_wrangles.main')
        assert namespace.standardize is main.standardize
        assert callable(namespace.standardize)
        for name in ('clean', 'custom', 'replace'):
            assert getattr(namespace.standardize, name) is getattr(canonical, name)
        assert namespace.convert.parse.__module__ == 'wrangles.recipe_wrangles.convert'
        assert not hasattr(namespace.standardize, 'parse')

    def test_generated_schema_preserves_legacy_contracts(self, tmp_path, monkeypatch):
        root = Path(__file__).resolve().parents[3]
        shutil.copyfile(root / 'schema/recipe_base_schema.json', tmp_path / 'recipe_base_schema.json')
        monkeypatch.chdir(tmp_path)
        runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
        schema = json.loads((tmp_path / 'schema.json').read_text(encoding='utf-8'))
        props = schema['$defs']['wrangles']['items']['properties']
        for name in self.CASES:
            assert props[f'standardize.{name}'] == props[f'convert.{name}']
            for namespace in ('standardize', 'convert'):
                jsonschema.validate({'wrangles': [{f'{namespace}.{name}': {
                    'input': 'raw', 'output': 'out', 'where': 'Keep = ?', 'where_params': [3], 'if': 'row_count > 0',
                }}]}, schema)
        assert 'convert.parse' in props
        assert 'standardize.parse' not in props


class TestStandardizeNamespace:
    def test_core_legacy_function_remains_callable_namespace(self, monkeypatch):
        standardize_module = importlib.import_module('wrangles.standardize')
        calls = []

        def fake_standardize(input, model_id, case_sensitive=False, **kwargs):
            calls.append((input, model_id, case_sensitive, kwargs))
            return 'standardized'

        monkeypatch.setattr(
            standardize_module,
            'standardize',
            fake_standardize
        )

        result = wrangles.standardize.custom(
            'value',
            '12345678-1234-1234',
            case_sensitive=True,
            custom_option='kept'
        )

        assert result == 'standardized'
        assert calls == [(
            'value',
            '12345678-1234-1234',
            True,
            {'custom_option': 'kept'}
        )]

    def test_legacy_and_custom_recipe_names_share_implementation(self, monkeypatch):
        recipe_main = importlib.import_module('wrangles.recipe_wrangles.main')
        calls = []

        def fake_standardize(values, model_id, case_sensitive=False, **kwargs):
            calls.append((values, model_id, case_sensitive, kwargs))
            return [f'clean:{value}' for value in values]

        monkeypatch.setattr(recipe_main, '_standardize', fake_standardize)
        source = pd.DataFrame({'raw': ['one', 'two']})

        legacy = wrangles.recipe.run(
            {
                'wrangles': [{
                    'standardize': {
                        'input': 'raw',
                        'output': 'result',
                        'model_id': '12345678-1234-1234',
                        'case_sensitive': True,
                        'custom_option': 'kept'
                    }
                }]
            },
            dataframe=source.copy()
        )
        explicit = wrangles.recipe.run(
            {
                'wrangles': [{
                    'standardize.custom': {
                        'input': 'raw',
                        'output': 'result',
                        'model_id': '12345678-1234-1234',
                        'case_sensitive': True,
                        'custom_option': 'kept'
                    }
                }]
            },
            dataframe=source.copy()
        )

        assert legacy.equals(explicit)
        assert legacy['result'].to_list() == ['clean:one', 'clean:two']
        assert calls == [
            (
                ['one', 'two'],
                '12345678-1234-1234',
                True,
                {'custom_option': 'kept'}
            ),
            (
                ['one', 'two'],
                '12345678-1234-1234',
                True,
                {'custom_option': 'kept'}
            )
        ]

    def test_recipe_namespace_exposes_parseable_schemas(self):
        namespace = wrangles.recipe._recipe_wrangles.standardize

        assert callable(namespace)
        assert callable(namespace.custom)
        assert callable(namespace.clean)
        for function in (namespace, namespace.custom, namespace.clean):
            schema = yaml.safe_load(function.__doc__)
            assert schema['type'] == 'object'

    def test_dataframe_accessor_preserves_legacy_call_and_dotted_names(
        self,
        monkeypatch
    ):
        recipe_main = importlib.import_module('wrangles.recipe_wrangles.main')

        monkeypatch.setattr(
            recipe_main,
            '_standardize',
            lambda values, model_id, case_sensitive=False, **kwargs: [
                f'model:{value}' for value in values
            ]
        )
        source = wrangles.DataFrame({'raw': ['  one  ']})

        legacy = source.wrangles.standardize(
            input='raw',
            output='result',
            model_id='12345678-1234-1234'
        )
        explicit = source.wrangles.standardize.custom(
            input='raw',
            output='result',
            model_id='12345678-1234-1234'
        )
        cleaned = source.wrangles.standardize.clean(
            input='raw',
            output='result'
        )

        assert legacy['result'].to_list() == ['model:  one  ']
        assert explicit.equals(legacy)
        assert cleaned['result'].to_list() == ['one']
        assert source.columns.to_list() == ['raw']


class TestStandardizeReplace:
    def test_legacy_alias_and_schema(self):
        namespace = wrangles.recipe._recipe_wrangles
        main = importlib.import_module('wrangles.recipe_wrangles.main')
        module = importlib.import_module('wrangles.recipe_wrangles.standardize')

        assert namespace.replace is namespace.standardize.replace
        assert main.replace is module.replace
        schema = yaml.safe_load(namespace.standardize.replace.__doc__)
        assert schema['required'] == ['input', 'find', 'replace']
        assert set(schema['properties']) == {'input', 'output', 'find', 'replace'}

    def test_generated_schema_supports_both_names(self, tmp_path, monkeypatch):
        root = Path(__file__).resolve().parents[3]
        shutil.copyfile(root / 'schema/recipe_base_schema.json',
                        tmp_path / 'recipe_base_schema.json')
        monkeypatch.chdir(tmp_path)

        def schema_response(url):
            assert url == 'http://json-schema.org/draft-07/schema#'
            return SimpleNamespace(json=lambda: jsonschema.Draft7Validator.META_SCHEMA)

        monkeypatch.setattr(requests, 'get', schema_response)
        runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
        generated = json.loads((tmp_path / 'schema.json').read_text())
        contracts = generated['$defs']['wrangles']['items']['properties']
        assert contracts['replace'] == contracts['standardize.replace']
        assert contracts['standardize.replace']['required'] == ['input', 'find', 'replace']
        assert {'standardize', 'standardize.clean', 'standardize.custom'} <= contracts.keys()

    @pytest.mark.parametrize('dotted', [False, True], ids=['legacy', 'standardize'])
    def test_dataframe_accessor_replaces_without_mutating_source(self, dotted):
        source = wrangles.DataFrame({'raw': ['ETA 12', 'ASAP 34']})
        operation = (source.wrangles.standardize.replace if dotted
                     else source.wrangles.replace)
        result = operation(input='raw', output='result', find=r'\d+', replace='#')

        assert result['result'].to_list() == ['ETA #', 'ASAP #']
        assert result['raw'].to_list() == ['ETA 12', 'ASAP 34']
        assert source.columns.to_list() == ['raw']
        assert source['raw'].to_list() == ['ETA 12', 'ASAP 34']


class TestStandardizeCleanCore:
    def test_scalar_and_list_shapes_are_preserved(self):
        assert wrangles.standardize.clean('') == ''
        assert wrangles.standardize.clean('  clean  ') == 'clean'
        assert wrangles.standardize.clean(['  one  ', 'two', 3, None]) == [
            'one',
            'two',
            3,
            None
        ]
        assert wrangles.standardize.clean([]) == []

    def test_repairs_mojibake_and_html_character_references(self):
        assert wrangles.standardize.clean('FranÃ§ais') == 'Français'
        assert wrangles.standardize.clean('ÃƒÂ©') == 'é'
        assert wrangles.standardize.clean('AT&amp;T&nbsp;') == 'AT&T'
        assert (
            wrangles.standardize.clean('<em>AT&amp;T</em>')
            == '<em>AT&amp;T</em>'
        )

    def test_normalization_controls_and_advanced_ftfy_kwargs(self):
        assert wrangles.standardize.clean('e\u0301') == 'é'
        assert wrangles.standardize.clean('①', normalization='NFC') == '①'
        assert wrangles.standardize.clean('①', normalization='NFKC') == '1'
        assert wrangles.standardize.clean('ﬃ') == 'ffi'
        assert (
            wrangles.standardize.clean('ﬃ', fix_latin_ligatures=False)
            == 'ﬃ'
        )
        assert wrangles.standardize.clean('Ａ') == 'A'
        assert (
            wrangles.standardize.clean('Ａ', fix_character_width=False)
            == 'Ａ'
        )

    def test_controls_quotes_surrogates_and_idempotence(self):
        dirty = '\x00\x81“Hello”\x7f\ud800'
        cleaned = wrangles.standardize.clean(dirty)

        assert cleaned == '"Hello"�'
        assert wrangles.standardize.clean(cleaned) == cleaned
        assert wrangles.standardize.clean('\x1b[31mred\x1b[0m') == 'red'
        assert (
            wrangles.standardize.clean('“Hello”', uncurl_quotes=False)
            == '“Hello”'
        )

    def test_whitespace_modes(self):
        dirty = '  one\u00a0\t two\r\n  three  \n\n four  '

        assert wrangles.standardize.clean(dirty) == 'one two three four'
        assert wrangles.standardize.clean(
            dirty,
            preserve_line_breaks=True
        ) == 'one two\nthree\n\nfour'
        assert wrangles.standardize.clean(
            '  one   two  ',
            trim=False
        ) == ' one two '
        assert wrangles.standardize.clean(
            '  one   two  ',
            collapse_whitespace=False,
            trim=False
        ) == '  one   two  '

    def test_invalid_inputs_and_kwargs_fail_clearly(self, monkeypatch):
        with pytest.raises(TypeError, match='string or a list'):
            wrangles.standardize.clean({'value': 'text'})

        standardize_module = importlib.import_module('wrangles.standardize')
        monkeypatch.setattr(
            standardize_module,
            '_fix_text',
            lambda *args, **kwargs: pytest.fail(
                'unknown kwargs must be rejected before calling ftfy'
            )
        )
        with pytest.raises(TypeError, match='unexpected field names'):
            wrangles.standardize.clean('text', unknown_ftfy_option=True)


class TestStandardizeCleanRecipe:
    def test_scalar_output_and_overwrite_in_place(self):
        source = pd.DataFrame({
            'raw': [' FranÃ§ais&nbsp; ', '  already clean  ']
        })

        output = wrangles.recipe.run(
            {
                'wrangles': [{
                    'standardize.clean': {
                        'input': 'raw',
                        'output': 'clean'
                    }
                }]
            },
            dataframe=source.copy()
        )
        overwritten = wrangles.recipe.run(
            {
                'wrangles': [{
                    'standardize.clean': {'input': 'raw'}
                }]
            },
            dataframe=source.copy()
        )

        assert output['clean'].to_list() == ['Français', 'already clean']
        assert overwritten['raw'].to_list() == ['Français', 'already clean']

    def test_multiple_inputs_map_to_equal_outputs_and_warn_once(self, caplog):
        wrapper = wrangles.recipe._recipe_wrangles.standardize.clean
        source = pd.DataFrame({
            'first': [' cafÃ© ', 7],
            'second': [None, ' Ａ ']
        })

        with caplog.at_level(logging.WARNING):
            result = wrapper(
                source,
                input=['first', 'second'],
                output=['first clean', 'second clean']
            )

        assert result['first clean'].to_list() == ['café', 7]
        assert result['second clean'].to_list() == [None, 'A']
        assert sum(
            'preserved non-string values' in message
            for message in caplog.messages
        ) == 1

    def test_multiple_inputs_concatenate_to_one_output(self):
        result = wrangles.recipe.run(
            {
                'wrangles': [{
                    'standardize.clean': {
                        'input': ['first', 'second'],
                        'output': 'clean',
                        'separator': ' | '
                    }
                }]
            },
            dataframe=pd.DataFrame({
                'first': [' A ', None, pd.NA],
                'second': [2, ' B ', ' C ']
            })
        )

        assert result['clean'].to_list() == ['A | 2', 'B', 'C']

    def test_mismatched_multiple_outputs_raise(self):
        wrapper = wrangles.recipe._recipe_wrangles.standardize.clean
        source = pd.DataFrame({'one': ['a'], 'two': ['b']})

        with pytest.raises(ValueError, match='same number of columns'):
            wrapper(
                source,
                input=['one', 'two'],
                output=['one clean', 'two clean', 'extra']
            )

    def test_wildcard_inputs_follow_concatenation_rule(self):
        result = wrangles.recipe.run(
            """
            wrangles:
              - standardize.clean:
                  input: Raw *
                  output: Clean
                  separator: " / "
            """,
            dataframe=pd.DataFrame({
                'Raw A': ['  one  '],
                'Raw B': [' two&nbsp; '],
                'Other': ['kept']
            })
        )

        assert result.iloc[0].to_dict() == {
            'Raw A': '  one  ',
            'Raw B': ' two&nbsp; ',
            'Other': 'kept',
            'Clean': 'one / two'
        }

    def test_where_and_empty_dataframe_behavior(self):
        filtered = wrangles.recipe.run(
            """
            wrangles:
              - standardize.clean:
                  input: Raw
                  output: Clean
                  where: Apply = true
            """,
            dataframe=pd.DataFrame({
                'Raw': ['  one  ', '  two  '],
                'Apply': [True, False]
            })
        )
        empty = wrangles.recipe.run(
            {
                'wrangles': [{
                    'standardize.clean': {
                        'input': 'Raw',
                        'output': 'Clean'
                    }
                }]
            },
            dataframe=pd.DataFrame({'Raw': []})
        )

        assert filtered['Clean'].to_list() == ['one', '']
        assert empty.empty
        assert empty.columns.to_list() == ['Raw', 'Clean']
