import importlib
from copy import deepcopy
import logging
import json
from pathlib import Path
import runpy
import shutil
import warnings
from types import SimpleNamespace

import jsonschema
import requests

import pandas as pd
import pytest
import yaml

import wrangles


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


class TestStandardizeFormatAliases:
    """Compatibility for the seven recipe aliases requested in #1248."""

    CASES = {
        'dates': (
            ['2024-01-02', '2024-12-31', ''],
            {'format': '%d/%m/%Y'},
            ['02/01/2024', '31/12/2024', ''],
        ),
        'pad': (
            ['12', '', '  '],
            {'pad_length': 4, 'side': 'left', 'char': '0'},
            ['0012', '0000', '00  '],
        ),
        'prefix': (['123', '', 'abc'], {'value': 'ID-'}, ['ID-123', 'ID-', 'ID-abc']),
        'remove_duplicates': (
            [['A', 'a', 'A'], 'b b B', ''], {}, [['A', 'a'], 'b B', ''],
        ),
        'significant_figures': (
            [1234.56, 0.012345, 0.0], {}, [1230.0, 0.0123, 0.0],
        ),
        'suffix': (['123', '', 'abc'], {'value': '-X'}, ['123-X', '-X', 'abc-X']),
        'trim': (['  red  ', '\tblue\n', ''], {}, ['red', 'blue', '']),
    }

    @pytest.fixture(autouse=True)
    def block_live_http(self, monkeypatch):
        def blocked(*args, **kwargs):
            pytest.fail('Standardize alias tests must not contact live services')

        monkeypatch.setattr(requests.sessions.Session, 'request', blocked)

    @pytest.fixture(params=list(CASES))
    def format_case(self, request):
        name = request.param
        values, options, expected = deepcopy(self.CASES[name])
        frame = pd.DataFrame({'row_id': [3, 1, 2], 'raw': values})
        return name, frame, options, expected

    def _run(self, operation, frame, options, **kwargs):
        return wrangles.recipe.run(
            {'wrangles': [{operation: {'input': 'raw', **deepcopy(options)}}]},
            dataframe=frame.copy(deep=True), **kwargs,
        )

    @pytest.mark.parametrize('explicit_output', [False, True], ids=['overwrite', 'new-column'])
    def test_alias_matches_legacy_output(self, format_case, explicit_output, caplog):
        name, frame, options, values = format_case
        target = 'result' if explicit_output else 'raw'
        if explicit_output:
            options['output'] = target
        expected = frame.copy()
        expected[target] = values

        with warnings.catch_warnings(record=True) as caught, caplog.at_level(logging.WARNING):
            warnings.simplefilter('always', DeprecationWarning)
            for operation in (f'format.{name}', f'standardize.{name}'):
                pd.testing.assert_frame_equal(self._run(operation, frame, options), expected)
        assert not any(issubclass(w.category, DeprecationWarning) for w in caught)
        assert not any('deprecat' in record.getMessage().lower() for record in caplog.records)

    @pytest.mark.parametrize('explicit_output', [False, True], ids=['overwrite', 'new-column'])
    def test_alias_preserves_where_and_parameters(self, format_case, explicit_output):
        name, frame, options, values = format_case
        target = 'result' if explicit_output else 'raw'
        if explicit_output:
            options['output'] = target
            frame[target] = 'untouched'
        expected = frame.copy()
        expected.at[1, target] = values[1]
        options.update(where='row_id = :selected_id', where_params={'selected_id': 1})
        for operation in (f'format.{name}', f'standardize.{name}'):
            pd.testing.assert_frame_equal(self._run(operation, frame, options), expected)

    @pytest.mark.parametrize('enabled', [True, False])
    def test_alias_preserves_if(self, format_case, enabled):
        name, frame, options, values = format_case
        options.update(output='result', **{'if': '${enabled}'})
        expected = frame.assign(result=values) if enabled else frame
        for operation in (f'format.{name}', f'standardize.{name}'):
            result = self._run(operation, frame, options, variables={'enabled': enabled})
            pd.testing.assert_frame_equal(result, expected)

    def test_alias_preserves_empty_where(self, format_case):
        name, frame, options, _ = format_case
        options.update(output='result', where='row_id > 10')
        expected = frame.assign(result='')
        for operation in (f'format.{name}', f'standardize.{name}'):
            pd.testing.assert_frame_equal(self._run(operation, frame, options), expected)

    def test_alias_preserves_multiple_inputs_and_wildcards(self, format_case):
        name, frame, options, values = format_case
        frame['raw_extra'] = frame['raw'].copy()
        options.update(input='raw*', output=['first', 'second'])
        expected = frame.assign(first=values, second=values)
        for operation in (f'format.{name}', f'standardize.{name}'):
            pd.testing.assert_frame_equal(self._run(operation, frame, options), expected)

    def test_alias_preserves_mismatched_output_error(self, format_case):
        name, frame, options, _ = format_case
        frame['raw_extra'] = frame['raw'].copy()
        options.update(input=['raw', 'raw_extra'], output=['only'])
        for operation in (f'format.{name}', f'standardize.{name}'):
            with pytest.raises(ValueError, match='The lists for input and output must be the same length'):
                self._run(operation, frame, options)

    @pytest.mark.parametrize('name, override, expected', [
        ('pad', {'skip_empty': True}, ['0012', '', '  ']),
        ('prefix', {'skip_empty': True}, ['ID-123', '', 'ID-abc']),
        ('suffix', {'skip_empty': True}, ['123-X', '', 'abc-X']),
        ('remove_duplicates', {'ignore_case': True}, [['A'], 'b', '']),
        ('significant_figures', {'significant_figures': 2}, [1200.0, 0.012, 0.0]),
    ])
    def test_alias_preserves_option_overrides(self, name, override, expected):
        values, options, _ = deepcopy(self.CASES[name])
        frame = pd.DataFrame({'row_id': [3, 1, 2], 'raw': values})
        options.update(output='result', **override)
        for operation in (f'format.{name}', f'standardize.{name}'):
            pd.testing.assert_frame_equal(
                self._run(operation, frame, options), frame.assign(result=expected),
            )

    def test_aliases_share_implementations_and_preserve_legacy_namespace(self):
        namespace = wrangles.recipe._recipe_wrangles
        main = importlib.import_module('wrangles.recipe_wrangles.main')
        canonical = importlib.import_module('wrangles.recipe_wrangles.standardize')
        assert namespace.standardize is main.standardize
        assert callable(namespace.standardize)
        for name in self.CASES:
            implementation = getattr(canonical, name)
            assert implementation.__module__ == canonical.__name__
            assert getattr(namespace.standardize, name) is implementation
            assert getattr(namespace.format, name) is implementation
        for name in ('clean', 'custom', 'replace'):
            assert callable(getattr(namespace.standardize, name))

    @pytest.mark.parametrize('module_name', ['standardize', 'format'])
    def test_module_exports_preserve_transformations(self, format_case, module_name):
        name, frame, options, values = format_case
        module = importlib.import_module(f'wrangles.recipe_wrangles.{module_name}')
        expected = frame.assign(result=values)
        if name == 'dates':
            # The direct wrapper preserves missing dates; recipe.run fills them.
            expected.at[2, 'result'] = float('nan')
        result = getattr(module, name)(
            frame.copy(deep=True), input='raw', output='result', **options,
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_dataframe_accessor_preserves_both_names(self, format_case):
        name, frame, options, values = format_case
        source = wrangles.DataFrame(frame.copy(deep=True))
        expected = frame.assign(result=values)
        if name == 'dates':
            expected.at[2, 'result'] = float('nan')
        for namespace in (source.wrangles.standardize, source.wrangles.format):
            result = getattr(namespace, name)(input='raw', output='result', **options)
            pd.testing.assert_frame_equal(result, expected)
        pd.testing.assert_frame_equal(pd.DataFrame(source), frame)

    def test_generated_schema_preserves_both_names_and_controls(self, tmp_path, monkeypatch):
        root = Path(__file__).resolve().parents[3]
        shutil.copyfile(root / 'schema/recipe_base_schema.json', tmp_path / 'recipe_base_schema.json')
        monkeypatch.chdir(tmp_path)
        runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
        schema = json.loads((tmp_path / 'schema.json').read_text(encoding='utf-8'))
        contracts = schema['$defs']['wrangles']['items']['properties']
        assert {'standardize', 'standardize.clean', 'standardize.custom', 'standardize.replace'} <= contracts.keys()
        for name, (_, options, _) in self.CASES.items():
            old, new = f'format.{name}', f'standardize.{name}'
            assert contracts[new] == contracts[old]
            assert {'if', 'where', 'where_params'} <= contracts[new]['properties'].keys()
            for operation in (old, new):
                jsonschema.validate({'wrangles': [{operation: {
                    'input': 'raw', 'output': 'result', 'where': 'row_id = :selected_id',
                    'where_params': {'selected_id': 1}, 'if': 'row_count > 0', **options,
                }}]}, schema)
