import importlib
import logging

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
