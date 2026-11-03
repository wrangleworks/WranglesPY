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


class TestStandardizeScalarAliases:
    """Issue #1255: shared implementations, with independent behavior oracles."""

    CASES = {
        'case': {
            'legacy': 'convert.case', 'raw': ['Red APPLE', 'bLUE sky', ''],
            'options': {'case': 'upper'}, 'values': ['RED APPLE', 'BLUE SKY', ''],
            'other': ['Green', 'Black', 'White'], 'other_values': ['GREEN', 'BLACK', 'WHITE'],
        },
        'data_type': {
            'legacy': 'convert.data_type', 'raw': ['12', 'bad', '3.5'],
            'options': {'data_type': 'float', 'default': -1}, 'values': [12.0, -1.0, 3.5],
            'other': ['2', '7.5', 'oops'], 'other_values': [2.0, 7.5, -1.0],
        },
        'fraction_to_decimal': {
            'legacy': 'convert.fraction_to_decimal', 'raw': ['1/2 in', '1-1/4 in', 'plain'],
            'options': {}, 'values': ['0.5 in', '1.25 in', 'plain'],
            'other': ['3/4', '2-1/2', 'other'], 'other_values': ['0.75', '2.5', 'other'],
        },
        'remove_words': {
            'legacy': 'remove_words', 'raw': ['red apple', 'blue berry', 'keep'],
            'options': {'to_remove': ['remove']}, 'values': ['apple', 'berry', 'keep'],
            'other': ['red desk', 'blue chair', 'table'], 'other_values': ['desk', 'chair', 'table'],
        },
        'round': {
            'legacy': 'round', 'raw': ['2.5', '3.5', 'bad'],
            'options': {}, 'values': [2.0, 4.0, ''],
            'other': ['10.2', '11.8', '13.5'], 'other_values': [10.0, 12.0, 14.0],
        },
    }

    @pytest.fixture(autouse=True)
    def block_http(self, monkeypatch):
        def unexpected_http(*args, **kwargs):
            pytest.fail('Scalar standardization must not call HTTP services')
        monkeypatch.setattr(requests.sessions.Session, 'request', unexpected_http)

    @pytest.fixture(params=['legacy', 'canonical'])
    def namespace(self, request):
        return request.param

    @pytest.fixture(params=list(CASES))
    def scalar_case(self, request):
        name = request.param
        spec = deepcopy(self.CASES[name])
        frame = pd.DataFrame({
            'raw': spec['raw'], 'remove': [['RED'], ['BLUE'], []], 'Keep': [3, 1, 2],
        }, index=pd.Index([7, 2, 9], name='row'))
        return name, spec, frame

    def run_alias(self, namespace, name, frame, **options):
        operation = f'standardize.{name}' if namespace == 'canonical' else self.CASES[name]['legacy']
        return wrangles.recipe.run(
            {'wrangles': [{operation: options}]}, dataframe=frame.copy(deep=True),
        )

    @pytest.mark.parametrize('mode', ['scalar', 'overwrite', 'list', 'wildcard', 'list_overwrite'])
    def test_columns_outputs_and_complete_frame(self, namespace, scalar_case, mode):
        name, spec, frame = scalar_case
        frame['raw2'] = spec['other']
        expected = frame.copy(deep=True)
        if mode == 'overwrite':
            options = {'input': 'raw'}
            expected['raw'] = spec['values']
        elif mode == 'scalar':
            options = {'input': 'raw', 'output': 'out'}
            expected['out'] = spec['values']
        elif mode == 'list_overwrite':
            options = {'input': ['raw', 'raw2']}
            expected['raw'] = spec['values']
            expected['raw2'] = spec['other_values']
        else:
            options = {'input': 'raw*' if mode == 'wildcard' else ['raw', 'raw2'], 'output': ['first', 'second']}
            expected['first'] = spec['values']
            expected['second'] = spec['other_values']
        pd.testing.assert_frame_equal(self.run_alias(namespace, name, frame, **spec['options'], **options), expected)

    @pytest.mark.parametrize('condition', ['plain', 'list_params', 'dict_params', 'no_rows'])
    @pytest.mark.parametrize('overwrite', [False, True])
    def test_where_and_bound_parameters_preserve_other_rows(self, namespace, scalar_case, condition, overwrite):
        name, spec, frame = scalar_case
        controls = {
            'plain': {'where': 'Keep = 3'},
            'list_params': {'where': 'Keep = ?', 'where_params': [3]},
            'dict_params': {'where': 'Keep = :value', 'where_params': {'value': 3}},
            'no_rows': {'where': 'Keep > 100'},
        }[condition]
        expected = frame.copy(deep=True)
        output = 'raw' if overwrite else 'out'
        if not overwrite:
            expected['out'] = ''
        if condition != 'no_rows':
            expected.at[7, output] = spec['values'][0]
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, name, frame, input='raw', output=output, **spec['options'], **controls), expected,
        )

    @pytest.mark.parametrize('enabled', [True, False])
    def test_if_true_and_false(self, namespace, scalar_case, enabled):
        name, spec, frame = scalar_case
        expected = frame.assign(out=spec['values']) if enabled else frame
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, name, frame, input='raw', output='out', **spec['options'], **{'if': enabled}), expected,
        )

    @pytest.mark.parametrize('overwrite', [False, True])
    def test_empty_frame_keeps_shape_and_dtypes(self, namespace, scalar_case, overwrite):
        name, spec, frame = scalar_case
        frame = frame.head(0)
        output = 'raw' if overwrite else 'out'
        expected = frame.copy()
        dtype = object if name in ('case', 'remove_words') else 'int64' if name == 'round' else 'float64'
        expected[output] = pd.Series(index=frame.index, dtype=dtype)
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, name, frame, input='raw', output=output, **spec['options']), expected,
        )

    @pytest.mark.parametrize('name', ['case', 'data_type', 'fraction_to_decimal', 'remove_words'])
    def test_mismatched_outputs_raise_existing_error(self, namespace, name):
        spec = self.CASES[name]
        frame = pd.DataFrame({'raw': spec['raw'], 'raw2': spec['other'], 'remove': [['RED'], ['BLUE'], []]})
        with pytest.raises(ValueError, match='The lists for input and output must be the same length'):
            self.run_alias(namespace, name, frame, input=['raw', 'raw2'], output=['only'], **spec['options'])

    @pytest.mark.parametrize('outputs', [['first'], ['first', 'second', 'unused']])
    def test_round_retains_zip_behavior_for_mismatched_outputs(self, namespace, outputs):
        frame = pd.DataFrame({'raw': ['2.5'], 'raw2': ['3.5']}, index=[7])
        expected = frame.assign(first=[2.0])
        if len(outputs) > 1:
            expected['second'] = [4.0]
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'round', frame, input=['raw', 'raw2'], output=outputs), expected,
        )

    @pytest.mark.parametrize('case,expected', [
        ('lower', 'hello world. next! 13.5mm'),
        ('UPPER', 'HELLO WORLD. NEXT! 13.5MM'),
        ('title', 'Hello World. Next! 13.5Mm'),
        ('sentence', 'Hello world. Next! 13.5mm'),
    ])
    def test_case_modes(self, namespace, case, expected):
        frame = pd.DataFrame({'raw': ['hELLO WORLD. nEXT! 13.5mm']}, index=[7])
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'case', frame, input='raw', output='out', case=case), frame.assign(out=[expected]),
        )

    @pytest.mark.parametrize('case,text', [('upper', 'RED APPLE'), ('sentence', 'Red apple')])
    def test_case_preserves_non_strings_and_warns_once(self, namespace, case, text, caplog):
        frame = pd.DataFrame({'raw': ['Red APPLE', 42, None, ['x']]})
        with caplog.at_level(logging.WARNING):
            result = self.run_alias(namespace, 'case', frame, input='raw', output='out', case=case)
        pd.testing.assert_frame_equal(result, pd.DataFrame({'raw': ['Red APPLE', 42, '', ['x']], 'out': [text, 42, '', ['x']]}))
        assert sum('Non-string values will be skipped' in record.message for record in caplog.records) == 1

    def test_case_keeps_numeric_only_columns(self, namespace):
        frame = pd.DataFrame({'raw': [3, 4]})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'case', frame, input='raw', case='upper'), frame,
        )

    @pytest.mark.parametrize('name,values,options,converted', [
        ('case', ['Red APPLE'], {}, ['red apple']),
        ('data_type', [2, True], {}, ['2', 'True']),
        ('fraction_to_decimal', ['1/3'], {}, ['0.3333']),
        ('remove_words', ['Steel bottle'], {'to_remove': ['remove']}, ['bottle']),
        ('round', ['2.5', '3.5'], {}, [2.0, 4.0]),
    ])
    def test_default_options_and_in_place_output(self, namespace, name, values, options, converted):
        frame = pd.DataFrame({'raw': values})
        if name == 'remove_words':
            frame['remove'] = [['steel']]
        expected = frame.copy(deep=True)
        expected['raw'] = converted
        pd.testing.assert_frame_equal(self.run_alias(namespace, name, frame, input='raw', **options), expected)

    @pytest.mark.parametrize('dtype,values,options,converted', [
        ('int', ['2', 'bad', '3.5'], {}, [2, 'bad', '3.5']),
        ('int', ['2', 'bad', '3.5'], {'default': 0}, [2, 0, 0]),
        ('float', ['1.25', 'bad', ''], {}, [1.25, 'bad', '']),
        ('float', ['1.25', 'bad', ''], {'default': 0}, [1.25, 0.0, 0.0]),
        ('str', [2, None, False], {}, ['2', 'None', 'False']),
        ('bool', ['false', '', 0, None], {}, [True, False, False, False]),
    ])
    def test_data_type_conversions_defaults_and_invalid_values(self, namespace, dtype, values, options, converted):
        frame = pd.DataFrame({'raw': values})
        expected = pd.DataFrame({'raw': ['' if value is None else value for value in values], 'out': converted})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'data_type', frame, input='raw', output='out', data_type=dtype, **options), expected,
        )

    @pytest.mark.parametrize('with_default', [True, False])
    def test_datetime_conversion_keeps_recursion_defaults_and_index(self, namespace, with_default):
        frame = pd.DataFrame({'raw': ['31/12/2024', 'invalid'], 'Keep': [3, 1]}, index=pd.Index([7, 2], name='row'))
        options = {'data_type': 'datetime', 'format': '%d/%m/%Y'}
        if with_default:
            options['default'] = '2001-02-03'
        expected = frame.assign(out=[pd.Timestamp('2024-12-31'), pd.Timestamp('2001-02-03') if with_default else 'invalid'])
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'data_type', frame, input='raw', output='out', **options), expected,
        )

    @pytest.mark.parametrize('decimals,values', [
        (0, ['0.0', '1.0 in', '3.0', 'plain', '-0.0', 'None', '2']),
        (2, ['0.33', '1.25 in', '2.75', 'plain', '-0.5', 'None', '2']),
        (4, ['0.3333', '1.25 in', '2.75', 'plain', '-0.5', 'None', '2']),
    ])
    def test_fraction_parsing_precision_and_non_strings(self, namespace, decimals, values):
        frame = pd.DataFrame({'raw': ['1/3', '1-1/4 in', '2 3/4', 'plain', '-1/2', None, 2]})
        expected = pd.DataFrame({'raw': ['1/3', '1-1/4 in', '2 3/4', 'plain', '-1/2', '', 2], 'out': values})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'fraction_to_decimal', frame, input='raw', output='out', decimals=decimals), expected,
        )

    def test_fraction_uses_builtin_round_alongside_recipe_round(self, namespace, monkeypatch):
        canonical = importlib.import_module('wrangles.recipe_wrangles.standardize')
        def unexpected_recipe_round(*args, **kwargs):
            pytest.fail('Fraction parsing must call Python round, not the DataFrame wrapper')
        monkeypatch.setattr(canonical, 'round', unexpected_recipe_round)
        frame = pd.DataFrame({'raw': ['1/3']})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'fraction_to_decimal', frame, input='raw', output='out'), frame.assign(out=['0.3333']),
        )

    @pytest.mark.parametrize('tokenize,ignore,values', [
        (False, False, ['Red blue green', 'Red blue green']),
        (False, True, ['green', 'blue green']),
        (True, False, ['Red green', 'Red blue green']),
        (True, True, ['green', 'blue green']),
    ])
    def test_remove_words_tokenization_and_case_options(self, namespace, tokenize, ignore, values):
        frame = pd.DataFrame({'raw': ['Red blue green', ['Red', 'blue', 'green']], 'remove': [['red blue'], ['RED']]})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'remove_words', frame, input='raw', output='out', to_remove=['remove'], tokenize_to_remove=tokenize, ignore_case=ignore),
            frame.assign(out=values),
        )

    def test_remove_words_retains_missing_input_error_and_missing_removal_behavior(self, namespace):
        with pytest.raises(TypeError, match='expected string or bytes-like object'):
            self.run_alias(namespace, 'remove_words', pd.DataFrame({'raw': [None], 'remove': [['red']]}), input='raw', to_remove=['remove'])
        frame = pd.DataFrame({'raw': ['only'], 'remove': [None]})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'remove_words', frame, input='raw', output='out', to_remove=['remove']),
            pd.DataFrame({'raw': ['only'], 'remove': [''], 'out': ['only']}),
        )

    @pytest.mark.parametrize('columns', ['Materials', ['Materials', 'Colours']])
    def test_remove_words_accepts_single_and_multiple_removal_columns(self, namespace, columns):
        frame = pd.DataFrame({'raw': ['Steel Blue Bottle'], 'Materials': [['Steel']], 'Colours': [['Blue']]})
        expected = 'Blue Bottle' if isinstance(columns, str) else 'Bottle'
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'remove_words', frame, input='raw', output='out', to_remove=columns),
            frame.assign(out=[expected]),
        )

    @pytest.mark.parametrize('decimals,values', [(1, [25.2, 35.8, -25.2, '']), (-1, [30.0, 40.0, -30.0, ''])])
    def test_round_keeps_recipe_coercion_and_precision(self, namespace, decimals, values):
        frame = pd.DataFrame({'raw': ['25.25', '35.75', '-25.25', 'bad']})
        pd.testing.assert_frame_equal(
            self.run_alias(namespace, 'round', frame, input='raw', output='out', decimals=decimals), frame.assign(out=values),
        )

    @pytest.mark.parametrize('name,options,error,message', [
        ('case', {'case': 'not_a_case'}, AttributeError, 'not_a_case'),
        ('data_type', {'data_type': 'squirrel'}, TypeError, 'data_type squirrel is not supported'),
        ('fraction_to_decimal', {}, ZeroDivisionError, r'Fraction\(1, 0\)'),
        ('round', {'decimals': 1.5}, TypeError, 'cannot be interpreted as an integer'),
        ('remove_words', {'to_remove': ['Missing']}, KeyError, 'Missing'),
    ])
    def test_invalid_parameters_keep_error_types_and_messages(self, namespace, name, options, error, message):
        frame = pd.DataFrame({'raw': ['1/0']})
        with pytest.raises(error, match=message):
            self.run_alias(namespace, name, frame, input='raw', output='out', **options)

    def test_direct_modules_share_canonical_implementations(self, scalar_case):
        name, spec, frame = scalar_case
        canonical = importlib.import_module('wrangles.recipe_wrangles.standardize')
        module = 'convert' if name in ('case', 'data_type', 'fraction_to_decimal') else 'main' if name == 'remove_words' else 'pandas'
        legacy = importlib.import_module(f'wrangles.recipe_wrangles.{module}')
        implementation = getattr(canonical, name)
        assert implementation.__module__ == canonical.__name__
        assert getattr(legacy, name) is implementation
        assert getattr(wrangles.recipe._recipe_wrangles.standardize, name) is implementation
        if '.' not in spec['legacy']:
            assert getattr(wrangles.recipe._recipe_wrangles, name) is implementation
        for module in (canonical, legacy):
            pd.testing.assert_frame_equal(
                getattr(module, name)(frame.copy(deep=True), input='raw', output='out', **spec['options']), frame.assign(out=spec['values']),
            )

    def test_dataframe_accessors_preserve_original(self, namespace, scalar_case):
        name, spec, frame = scalar_case
        frame = wrangles.DataFrame(frame)
        original = frame.copy(deep=True)
        if name == 'round' and namespace == 'legacy':
            # The legacy root round recipe was never exposed by this accessor.
            assert not hasattr(frame.wrangles, 'round')
            return
        target = frame.wrangles.standardize if namespace == 'canonical' else frame.wrangles.convert if '.' in spec['legacy'] else frame.wrangles
        pd.testing.assert_frame_equal(
            getattr(target, name)(input='raw', output='out', **spec['options']), frame.assign(out=spec['values']),
        )
        pd.testing.assert_frame_equal(frame, original)

    def test_existing_callable_standardize_namespace_is_preserved(self):
        namespace = wrangles.recipe._recipe_wrangles
        main = importlib.import_module('wrangles.recipe_wrangles.main')
        canonical = importlib.import_module('wrangles.recipe_wrangles.standardize')
        core = importlib.import_module('wrangles.standardize')
        assert namespace.standardize is main.standardize
        assert callable(namespace.standardize)
        assert wrangles.standardize is core.standardize
        for name in ('clean', 'custom', 'replace'):
            assert getattr(namespace.standardize, name) is getattr(canonical, name)
        for name in ('clean', 'custom'):
            assert callable(getattr(wrangles.standardize, name))

    def test_generated_schema_preserves_legacy_contracts(self, tmp_path, monkeypatch):
        root = Path(__file__).resolve().parents[3]
        shutil.copyfile(root / 'schema/recipe_base_schema.json', tmp_path / 'recipe_base_schema.json')
        monkeypatch.chdir(tmp_path)
        runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
        schema = json.loads((tmp_path / 'schema.json').read_text(encoding='utf-8'))
        properties = schema['$defs']['wrangles']['items']['properties']
        for name, spec in self.CASES.items():
            assert properties[f'standardize.{name}'] == properties[spec['legacy']]
            for operation in (spec['legacy'], f'standardize.{name}'):
                jsonschema.validate({'wrangles': [{operation: {
                    'input': 'raw', 'output': 'out', **spec['options'],
                    'where': 'Keep = ?', 'where_params': [3], 'if': 'row_count > 0',
                }}]}, schema)


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
