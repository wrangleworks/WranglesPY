import wrangles
import pandas as pd
import pytest
import json as _json
import numpy as _np
import importlib
from copy import deepcopy
import json
from pathlib import Path
import runpy
import shutil

import jsonschema
import requests
import yaml


class TestStructureSerializationAliases:
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

    @pytest.fixture(params=['structure', 'convert'])
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
        canonical = importlib.import_module('wrangles.recipe_wrangles.structure')
        legacy = importlib.import_module('wrangles.recipe_wrangles.convert')
        implementation = getattr(canonical, name)
        assert implementation.__module__ == canonical.__name__
        assert getattr(legacy, name) is implementation
        assert getattr(wrangles.recipe._recipe_wrangles.structure, name) is implementation
        for module in (canonical, legacy):
            pd.testing.assert_frame_equal(getattr(module, name)(frame.copy(deep=True), input='raw', output='out'), frame.assign(out=spec['values']))

    @pytest.mark.parametrize('name', ['from_json', 'from_yaml'])
    def test_mutable_fallback_identity_is_preserved(self, name):
        canonical = importlib.import_module('wrangles.recipe_wrangles.structure')
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
        standardize = importlib.import_module('wrangles.recipe_wrangles.standardize')
        main = importlib.import_module('wrangles.recipe_wrangles.main')
        assert namespace.standardize is main.standardize
        assert callable(namespace.standardize)
        for name in ('clean', 'custom', 'replace'):
            assert getattr(namespace.standardize, name) is getattr(standardize, name)
        assert namespace.convert.parse.__module__ == 'wrangles.recipe_wrangles.convert'
        assert not hasattr(namespace.standardize, 'parse')
        assert not hasattr(namespace.structure, 'parse')

    @pytest.mark.parametrize('name', list(CASES))
    def test_serialization_is_registered_only_in_structure_and_convert(self, name):
        standardize = importlib.import_module('wrangles.recipe_wrangles.standardize')
        assert not hasattr(standardize, name)
        assert not hasattr(wrangles.recipe._recipe_wrangles.standardize, name)
        with pytest.raises(ValueError, match=f'Function standardize.{name} not recognized'):
            self.run_alias('standardize', name, pd.DataFrame({'raw': ['{}']}), input='raw')

    @pytest.mark.parametrize('legacy, canonical, value, params, values', [
        ('dictionary', 'split_dictionary', {'a': 1}, {'output': ['a']}, {'a': [1]}),
        ('list', 'split_list', [1, 2], {'output': ['a', 'b']}, {'a': [1], 'b': [2]}),
        ('text', 'split_text', 'a|b', {'char': '|', 'output': ['a', 'b']}, {'a': ['a'], 'b': ['b']}),
        ('tokenize', 'tokenize', 'a b', {'output': 'tokens'}, {'tokens': [['a', 'b']]}),
    ])
    def test_existing_structure_split_exports_and_accessor(self, legacy, canonical, value, params, values):
        namespace = wrangles.recipe._recipe_wrangles
        assert getattr(namespace.structure, canonical) is getattr(namespace.split, legacy)
        source = wrangles.DataFrame({'raw': [value]})
        original = source.copy(deep=True)
        result = getattr(source.wrangles.structure, canonical)(input='raw', **params)
        pd.testing.assert_frame_equal(result, source.assign(**values))
        pd.testing.assert_frame_equal(source, original)

    def test_generated_schema_preserves_legacy_contracts(self, tmp_path, monkeypatch):
        root = Path(__file__).resolve().parents[3]
        shutil.copyfile(root / 'schema/recipe_base_schema.json', tmp_path / 'recipe_base_schema.json')
        monkeypatch.chdir(tmp_path)
        runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
        schema = json.loads((tmp_path / 'schema.json').read_text(encoding='utf-8'))
        props = schema['$defs']['wrangles']['items']['properties']
        for name in self.CASES:
            assert props[f'structure.{name}'] == props[f'convert.{name}']
            assert f'standardize.{name}' not in props
            for namespace in ('structure', 'convert'):
                jsonschema.validate({'wrangles': [{f'{namespace}.{name}': {
                    'input': 'raw', 'output': 'out', 'where': 'Keep = ?', 'where_params': [3], 'if': 'row_count > 0',
                }}]}, schema)
        assert 'convert.parse' in props
        assert 'standardize.parse' not in props
        assert 'structure.parse' not in props


class TestSharedSerializationHelpers:
    @pytest.fixture(autouse=True)
    def block_http(self, monkeypatch):
        def unexpected(*args, **kwargs):
            pytest.fail('Serialization helpers must not call HTTP')
        monkeypatch.setattr('requests.sessions.Session.request', unexpected)

    @pytest.mark.parametrize('default,expected', [
        (None, [None, None]), ([], [[], []]), ([0], [0, 0]),
        ([1, 2], [1, 2]), ({'a': 1}, [{'a': 1}, {'a': 1}]),
    ])
    def test_default_normalizer_has_one_owner_and_keeps_broadcast_rules(self, default, expected):
        import importlib

        shared = importlib.import_module('wrangles.recipe_wrangles._serialization')
        canonical = importlib.import_module('wrangles.recipe_wrangles.structure')
        convert = wrangles.recipe._recipe_wrangles.convert
        assert shared._normalize_default_list.__module__ == shared.__name__
        assert canonical._normalize_default_list is convert._normalize_default_list is shared._normalize_default_list
        assert shared._normalize_default_list(default, ['a', 'b'], 'convert.parse') == expected
        with pytest.raises(ValueError, match='same length as input/output for convert.parse'):
            shared._normalize_default_list([1, 2, 3], ['a', 'b'], 'convert.parse')

    def test_safe_loaders_are_shared_without_changing_parse_resolution(self):
        from datetime import date
        import importlib
        import yaml

        shared = importlib.import_module('wrangles.recipe_wrangles._serialization')
        canonical = importlib.import_module('wrangles.recipe_wrangles.structure')
        convert = wrangles.recipe._recipe_wrangles.convert
        assert canonical._YAMLLoader is convert._YAMLLoader is shared._YAMLLoader
        assert canonical._YAMLDumper is convert._YAMLDumper is shared._YAMLDumper
        assert shared._YAMLLoader is getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
        frame = pd.DataFrame({'raw': ['yes', '00123', '2024-01-02']})
        decoded = wrangles.recipe.run({'wrangles': [{'structure.from_yaml': {'input': 'raw', 'output': 'out'}}]}, dataframe=frame.copy())
        pd.testing.assert_frame_equal(decoded, frame.assign(out=[True, 83, date(2024, 1, 2)]))
        parsed = wrangles.recipe.run({'wrangles': [{'convert.parse': {'input': 'raw', 'output': 'out'}}]}, dataframe=frame.copy())
        pd.testing.assert_frame_equal(parsed, frame.assign(out=frame['raw']))

    def test_pure_python_safe_loader_fallback(self, monkeypatch):
        import importlib
        from pathlib import Path
        import runpy
        import yaml

        shared = importlib.import_module('wrangles.recipe_wrangles._serialization')
        monkeypatch.delattr(yaml, 'CSafeLoader', raising=False)
        monkeypatch.delattr(yaml, 'CSafeDumper', raising=False)
        fallback = runpy.run_path(str(Path(shared.__file__)))
        assert fallback['_YAMLLoader'] is yaml.SafeLoader
        assert fallback['_YAMLDumper'] is yaml.SafeDumper
        assert yaml.load('yes', Loader=fallback['_YAMLLoader']) is True
        with pytest.raises(yaml.constructor.ConstructorError):
            yaml.load('!!python/tuple [1, 2]', Loader=fallback['_YAMLLoader'])
        text = yaml.dump({'word': 'café'}, Dumper=fallback['_YAMLDumper'], allow_unicode=True)
        assert text == 'word: café\n'


class TestConvertCase:
    """
    Test convert.case wrangles
    """
    def test_default(self):
        """
        Default value -> no case specified
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'a string'

    def test_list(self):
        """
        Input is a list
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input:
                - Data1
                - Data2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'a string' and df.iloc[0]['Data2'] == 'another string'

    def test_output(self):
        """
        Specifying output column
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            output: Column
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Column'] == 'a string'

    def test_list_to_list(self):
        """
        Output and input are a multi columns
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input:
                - Data1
                - Data2
            output:
                - Column1
                - Column2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Column1'] == 'a string' and df.iloc[0]['Column2'] == 'another string'

    def test_multi_input_single_output(self):
        """
        Input is a list of columns and output is a single column
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input:
                - Data1
                - Data2
            output: Column1
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_single_input_multi_output(self):
        """
        Input is a list of columns and output is a single column
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            output:
                - Column1
                - Column2
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_lower(self):
        """
        Test converting to lower case
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            case: lower
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'a string'

    def test_upper(self):
        """
        Test converting to upper case
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            case: upper
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'A STRING'

    def test_upper_list(self):
        """
        Test the output when trying to convert a list to upper case
        """
        data = pd.DataFrame({'Data': [['A StRiNg', 'Another String']]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: output data
            case: upper
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output data'] == ['A StRiNg', 'Another String']
        
    def test_title(self):
        """
        Test converting to title case
        """
        data = pd.DataFrame([['A StRiNg', 'Another String']], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.case:
            input: Data1
            case: title
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data1'] == 'A String'

    def test_sentence(self):
        """
        Test converting to sentence case
        """
        data = pd.DataFrame({
            'Data': ["will this be capitalized correctly? i'm not so sure! probably not... but maybe", 'i LOST! mY 13.5mm WRENCH.']
        })
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: output data
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output data'] == "Will this be capitalized correctly? I'm not so sure! Probably not... But maybe" and df.iloc[1]['output data'] == 'I lost! My 13.5mm wrench.'

    def test_list_sentence(self):
        """
        Test converting case with a list of strings
        """
        data = pd.DataFrame({'Data': [['a StRiNg.', ' YET another StRiNg.', '   a THIRD STring.']]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: output data
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output data'] == ['a StRiNg.', ' YET another StRiNg.', '   a THIRD STring.']

    def test_where(self):
        """
        Test converting to title case using where
        """
        data = pd.DataFrame({
        'Col1': ['ball bearing', 'roller bearing', 'needle bearing'],
        'number': [25, 31, 22]
        })
        recipe = """
        wrangles:
        - convert.case:
            input: Col1
            case: title
            where: number > 22
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Col1'] == 'Ball Bearing' and df.iloc[2]['Col1'] == "needle bearing"

    def test_where_empty(self):
        """
        Test converting to title case using where
        """
        data = pd.DataFrame({
        'Col1': ['ball bearing', 'roller bearing', 'needle bearing'],
        'number': [25, 31, 22]
        })
        recipe = """
        wrangles:
        - convert.case:
            input: Col1
            case: title
            where: number > 35
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Col1'] == 'ball bearing' and df.iloc[2]['Col1'] == "needle bearing" 

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.case:
                input: column
                output: upper column
                case: upper
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'upper column']

    def test_sentence_tabs_after_punctuation(self):
        """
        Sentence case with tab characters as whitespace between sentences.
        The regex handles [ \t]* between punctuation and next word.
        """
        data = pd.DataFrame({'Data': ["hello.\tthere! one more sentence."]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: out
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == "Hello.\tThere! One more sentence."

    def test_sentence_leading_whitespace(self):
        """
        Sentence case where the string starts with leading spaces/tabs.
        The first non-whitespace character should be capitalised.
        """
        data = pd.DataFrame({'Data': ["   hello world. next sentence", "\t\thello again"]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: out
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == "   Hello world. Next sentence"
        assert df.iloc[1]['out'] == "\t\tHello again"

    def test_sentence_unicode_accented_chars(self):
        """
        Sentence case preserves/capitalises Unicode accented characters.
        """
        data = pd.DataFrame({'Data': ["héllo wörld. ñoño is here! über cool."]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: out
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == "Héllo wörld. Ñoño is here! Über cool."

    def test_sentence_starts_with_number(self):
        """
        Sentence case when the sentence starts with a digit.
        The digit 'consumes' the capitalise flag; subsequent lowercase letters stay lower.
        """
        data = pd.DataFrame({'Data': ["13 items found. that's all."]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: out
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == "13 items found. That's all."

    def test_lower_non_string_preserved(self):
        """
        Non-string values (int, list, None) in a lower-case column are returned unchanged.
        The vectorised path must restore originals for non-string rows.
        """
        data = pd.DataFrame({'Data': ["HELLO", 99, ["A", "B"], None]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: out
            case: lower
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == "hello"
        assert df.iloc[1]['out'] == 99
        assert df.iloc[2]['out'] == ["A", "B"]

    def test_title_non_string_preserved(self):
        """
        Non-string values in a title-case column are returned unchanged.
        """
        data = pd.DataFrame({'Data': ["hello world", {"key": "val"}]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: out
            case: title
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == "Hello World"
        assert df.iloc[1]['out'] == {"key": "val"}

    def test_purely_numeric_column_preserved(self):
        """
        A column with an all-integer int64 dtype must not raise AttributeError
        from the .str accessor and must return all values unchanged with a warning.
        """
        data = pd.DataFrame({'Data': [1, 2, 3]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            output: out
            case: lower
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == 1
        assert df.iloc[1]['out'] == 2
        assert df.iloc[2]['out'] == 3

    def test_lower_large_dataframe(self):
        """
        Vectorised lower case on a large dataframe produces correct output.
        """
        n = 100_000
        data = pd.DataFrame({'Data': ['Hello World MIXED Case'] * n})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            case: lower
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data'] == 'hello world mixed case'
        assert df.iloc[-1]['Data'] == 'hello world mixed case'

    def test_upper_large_dataframe(self):
        """
        Vectorised upper case on a large dataframe produces correct output.
        """
        n = 100_000
        data = pd.DataFrame({'Data': ['hello world mixed case'] * n})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            case: upper
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data'] == 'HELLO WORLD MIXED CASE'

    def test_title_large_dataframe(self):
        """
        Vectorised title case on a large dataframe produces correct output.
        """
        n = 100_000
        data = pd.DataFrame({'Data': ['hello world mixed case'] * n})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            case: title
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data'] == 'Hello World Mixed Case'

    def test_sentence_large_dataframe(self):
        """
        Regex-based sentence case on a large dataframe produces correct output.
        """
        n = 50_000
        data = pd.DataFrame({'Data': ['first sentence. second one! third? yes.'] * n})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            case: sentence
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Data'] == 'First sentence. Second one! Third? Yes.'

    def test_lower_multiple_columns(self):
        """
        Vectorised lower case across multiple input/output column pairs.
        """
        n = 50_000
        data = pd.DataFrame({
            'Col1': ['Hello World'] * n,
            'Col2': ['ANOTHER STRING'] * n,
            'Col3': ['YET ANOTHER'] * n,
        })
        recipe = """
        wrangles:
        - convert.case:
            input:
              - Col1
              - Col2
              - Col3
            output:
              - Out1
              - Out2
              - Out3
            case: lower
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Out1'] == 'hello world'
        assert df.iloc[0]['Out2'] == 'another string'
        assert df.iloc[0]['Out3'] == 'yet another'

    def test_mixed_types_warning_logged_once(self, caplog):
        """
        When a column contains non-string values, the invalid_data warning fires
        exactly once regardless of how many non-string rows there are.
        """
        import logging
        data = pd.DataFrame({'Data': ["hello", 1, 2, 3, "world"]})
        recipe = """
        wrangles:
        - convert.case:
            input: Data
            case: upper
        """
        with caplog.at_level(logging.WARNING):
            df = wrangles.recipe.run(recipe, dataframe=data)
        warning_messages = [r.message for r in caplog.records if 'invalid' in r.message.lower() or 'non-string' in r.message.lower() or 'not a string' in r.message.lower()]
        # Warning should fire at most once
        assert len(warning_messages) <= 1
        # Strings are correctly transformed
        assert df.iloc[0]['Data'] == 'HELLO'
        assert df.iloc[4]['Data'] == 'WORLD'
        # Non-strings are preserved
        assert df.iloc[1]['Data'] == 1


class TestConvertDataType:
    """
    Test convert.data_type wrangles
    """
    def test_str(self):
        """
        Test converting to string data type
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: Data1
            data_type: str
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['Data1'], str)

    def test_list_to_list(self):
        """
        Test using a list of outputs and a list of inputs
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: 
              - Data1
              - Data2
            output:
              - out1
              - out2
            data_type: str
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['out1'], str) and isinstance(df.iloc[0]['out2'], str) 

    def test_error_multi_input_single_output(self):
        """
        Test error when list of inputs given with a single output
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: 
              - Data1
              - Data2
            output: out1
            data_type: str
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_error_single_input_multi_output(self):
        """
        Test error when single input given with list of outputs
        """
        data = pd.DataFrame([[1, "2"]], columns=['Data1', 'Data2'])
        recipe = """
        wrangles:
        - convert.data_type:
            input: Data1
            output: 
              - out1
              - out2
            data_type: str
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_where(self):
        """
        Test convert.data_type using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: number
                data_type: str
                where: number > 25
            """,
            dataframe=pd.DataFrame({
                'number': [25, 31, 22]
            })
        )
        assert df['number'].values.tolist() == [25, '31', 22]

    def test_convert_to_datetime(self):
        data = pd.DataFrame({
            'date': ['12/25/2050'],
        })
        recipe = """
        wrangles:
        - convert.data_type:
            input: date
            output: date_type
            data_type: datetime
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['date_type'].week == 51
        
    def test_convert_to_datetime_where(self):
        """
        Test using convert to datetime using where
        """
        data = pd.DataFrame({
            'date': ['12/25/2050', '11/10/1987'],
            'numbers': [4, 2]
        })
        recipe = """
        wrangles:
        - convert.data_type:
            input: date
            output: date_type
            data_type: datetime
            where: numbers > 3
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['date_type'] == '0' and df.iloc[0]['date_type'].week == 51

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: column
                output: output column
                data_type: str
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']

    def test_convert_datatype_invalid_int(self):
        """
        Test converting a column of strings and integers to integers
        where some values cannot be converted
        """
        df = pd.DataFrame({
            'col': ['1', '2', 3, '4', 5, '', 'this is text']
        })
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: col
                output: output
                data_type: int
            """,
            dataframe=df
            )
        assert df['output'][0] == 1 and df['output'][6] == 'this is text'

    def test_convert_datatype_invalid_default_int(self):
        """
        Test converting a column of strings and integers to integers
        where some values cannot be converted and a default is provided
        """
        df = pd.DataFrame({
            'col': ['1', '2', 3, '4', 5, '', 'this is text']
        })
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: col
                output: output
                data_type: int
                default: 0
            """,
            dataframe=df
            )
        assert df['output'][0] == _np.int64(1) and df['output'][6] == _np.int64(0)

    def test_convert_datatype_invalid_float(self):
        """
        Test converting a column of strings and floats to floats
        where some values cannot be converted
        """
        df = pd.DataFrame({
            'col': ['1.24', '2.123', 3.99, '4.1', 5.04, '', 'this is text']
        })
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: col
                output: output
                data_type: float
            """,
            dataframe=df
            )
        assert df['output'][0] == 1.24 and df['output'][6] == 'this is text'

    def test_convert_datatype_invalid_default_float(self):
        """
        Test converting a column of strings and floats to floats
        where some values cannot be converted and a default is provided
        """
        df = pd.DataFrame({
            'col': ['1.24', '2.123', 3.99, '4.1', 5.04, '', 'this is text']
        })
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: col
                output: output
                data_type: float
                default: 0.00
            """,
            dataframe=df
            )
        assert df['output'][0] == 1.24 and df['output'][6] == 0.00

    def test_convert_datatype_invalid_date(self):
        """
        Test converting a column of strings to dates
        where some values cannot be converted
        """
        df = pd.DataFrame({
            'col': ['4/9/2222', 'Look, a string!']
        })
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: col
                output: output
                data_type: datetime
            """,
            dataframe=df
            )
        assert df['output'][0] == pd.Timestamp('2222-04-09 00:00:00') and df['output'][1] == 'Look, a string!'

    def test_convert_datatype_invalid_date_default(self):
        """
        Test converting a column of strings to dates where
        some values cannot be converted, with a default
        """
        df = pd.DataFrame({
            'col': ['4/9/2222', 'Look, a string!']
        })
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.data_type:
                input: col
                output: output
                data_type: datetime
                default: 1999-08-29
            """,
            dataframe=df
            )
        assert df['output'][0] == pd.Timestamp('2222-04-09 00:00:00') and df['output'][1] == pd.Timestamp('1999-08-29 00:00:00')

    def test_convert_datatype_error_invalid_data_type(self):
        """
        Test the error when passing an invalid datatype to the data_type param
        """
        df = pd.DataFrame({
            'col': ['4/9/2222', 'Look, a string!']
        })
        recipe = """
        wrangles:
        - convert.data_type:
            input: col
            output: output
            data_type: squirrel
            default: rodent
        """
        with pytest.raises(TypeError) as info:
            wrangles.recipe.run(recipe, dataframe=df)
        assert (
            info.typename == 'TypeError' and
            'convert.data_type (line 3) - data_type squirrel is not supported.' in info.value.args[0]
        )


class TestConvertFractionToDecimal:
    """
    Test convert.fraction_to_decimal wrangle
    """
    def test_default(self):
        """
        Test basic example
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: col1
            output: out1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high"

    def test_list_to_list(self):
        """
        Test using a list of outputs and inputs
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: 
                - col1
                - col2
            output: 
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high" and df.iloc[0]['out2'] == "The length is 0.75 wide 0.125 high"

    def test_list_to_single_output(self):
        """
        Test using a list of inputs and a single output
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: 
                - col1
                - col2
            output: out1
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_single_input_multi_output(self):
        """
        Test using a single input and a list of outputs
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'col2': ['The length is 3/4 wide 1/8 high', 'the panel is 1/3 inches', 'the diameter is 3/16 meters']
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: col1
            output: 
                - out1
                - out2
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )
        
    def test_different_separators(self):
        """
        Testing different separators for mixed fractions
        """
        data = pd.DataFrame({
            'input': [
                '1-1/3',
                '1-1/2 cups',
                '1 1/2 cups',
                '1 1/3',
                'not range 1-1/4',
                'e.g 1-3/4 - 2-1/2',
                'fraction ranges 1/4 - 1/2'
            ]
        })
        
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - convert.fraction_to_decimal:
                input: input
                output: out
                decimals: 2
            """,
            dataframe=data
        )
        assert df['out'].tolist() == ['1.33', '1.5 cups', '1.5 cups', '1.33', 'not range 1.25', 'e.g 1.75 - 2.5', 'fraction ranges 0.25 - 0.5']

    def test_where(self):
        """
        Test using fraction to decimal using where
        """
        data = pd.DataFrame({
        'col1': ['The length is 1/2 wide 1/3 high', 'the panel is 3/4 inches', 'the diameter is 1/3 meters'],
        'numbers': [13, 12, 11]
        })
        recipe = """
        wrangles:
        - convert.fraction_to_decimal:
            input: col1
            output: out1
            where: numbers > 11
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[2]['out1'] == "" and df.iloc[0]['out1'] == "The length is 0.5 wide 0.3333 high"

    def test_convert_fraction_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.fraction_to_decimal:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']


class TestConvertParse:
    """
    Test convert.parse wrangle
    """
    @staticmethod
    def _excessively_nested_value(representation):
        import sys

        depth = sys.getrecursionlimit() + 100
        if representation == "json":
            return "[" * depth + "0" + "]" * depth
        if representation == "yaml":
            return "{key: " * depth + "0" + "}" * depth
        value = 0
        for _ in range(depth):
            value = [value]
        return value

    def test_proper_json(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [
                    '{"key": "value", "enabled": false}',
                    '["one", 2, true]',
                ]
            })
        )

        assert df["column"].tolist() == [
            {"key": "value", "enabled": False},
            ["one", 2, True],
        ]

    @pytest.mark.parametrize("other, expected_other", [("1.5", 1.5), ("", None)])
    def test_large_integer_precision_with_mixed_scalars(self, other, expected_other):
        original = wrangles.DataFrame(
            {"column": ["9007199254740993", other]},
            index=pd.Index([23, 5], name="source_row"),
        )
        df = original.wrangles.convert.parse(input="column", output="parsed")

        assert df.index.equals(original.index)
        assert df["parsed"].dtype == object
        assert type(df.at[23, "parsed"]) is int
        assert df.at[23, "parsed"] == 9007199254740993
        assert df.at[5, "parsed"] == expected_other

    @pytest.mark.parametrize("other", ["1.5", ""])
    def test_large_integer_precision_survives_recipe_rendering(self, other):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                output: parsed
            - create.jinja:
                output: rendered
                template:
                  string: 'value={{ parsed }}'
            """,
            dataframe=pd.DataFrame({"column": ["9007199254740993", other]}),
        )

        assert type(df.at[0, "parsed"]) is int
        assert df.at[0, "parsed"] == 9007199254740993
        assert df["rendered"].tolist() == ["value=9007199254740993", f"value={other}"]

    def test_human_readable_json_and_yaml(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                expected: dictionary
            """,
            dataframe=pd.DataFrame({
                "column": [
                    "{key: value, items: [one, two]}",
                    "key: value\nitems:\n- one\n- two",
                ]
            })
        )

        assert df["column"].tolist() == [
            {"key": "value", "items": ["one", "two"]},
            {"key": "value", "items": ["one", "two"]},
        ]

    def test_python_representation(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                expected: dictionary
            """,
            dataframe=pd.DataFrame({
                "column": [
                    "{'active': True, 'missing': None, 'items': ['one']}"
                ]
            })
        )

        assert df["column"][0] == {
            "active": True,
            "missing": None,
            "items": ["one"],
        }

    def test_accidentally_quoted_structures(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [
                    """'{"key": "value"}'""",
                    '"[1, 2, 3]"',
                    '''"{'key': None}"''',
                    "'key: value'",
                ]
            })
        )

        assert df["column"].tolist() == [
            {"key": "value"},
            [1, 2, 3],
            {"key": None},
            {"key": "value"},
        ]

    def test_missing_values_use_independent_defaults(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                default: {}
                expected: dictionary
            """,
            dataframe=pd.DataFrame({
                "column": ["", "   ", None, _np.nan]
            })
        )

        assert df["column"].tolist() == [{}, {}, {}, {}]
        assert len({id(value) for value in df["column"]}) == 4

    def test_missing_values_without_default_remain_empty(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": ["", "   ", None, _np.nan]
            })
        )

        # The recipe runner normalizes None results to its standard empty cell.
        assert df["column"].tolist() == ["", "", "", ""]

    def test_valid_falsy_values_are_preserved(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                default: fallback
            """,
            dataframe=pd.DataFrame({
                "column": ["[]", "{}", '""', "false", "0"]
            })
        )

        assert df["column"].tolist() == [[], {}, "", False, 0]

    def test_yaml_scalar_resolution_stays_json_like(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                expected: dictionary
            """,
            dataframe=pd.DataFrame({
                "column": [
                    "{answer: yes, state: on, date: 2026-07-25, enabled: true}"
                ]
            })
        )

        assert df["column"][0] == {
            "answer": "yes",
            "state": "on",
            "date": "2026-07-25",
            "enabled": True,
        }

    def test_yaml_numeric_resolution_preserves_identifiers(self):
        df = wrangles.DataFrame({
            "column": [
                "{part: 00123, code: 12:34, time: 12:34.5, hex: 0xFF, "
                "binary: 0b10, decimal: 01.5, quantity: 12, zero: 0, "
                "negative: -12, fraction: 1.25, exponent: 1e3, "
                "small: -1.5e-2}"
            ]
        }).wrangles.convert.parse(input="column", expected="dictionary")

        assert df["column"][0] == {
            "part": "00123",
            "code": "12:34",
            "time": "12:34.5",
            "hex": "0xFF",
            "binary": "0b10",
            "decimal": "01.5",
            "quantity": 12,
            "zero": 0,
            "negative": -12,
            "fraction": 1.25,
            "exponent": 1000.0,
            "small": -0.015,
        }

    @pytest.mark.parametrize("loader_name", ["SafeLoader", "CSafeLoader"])
    @pytest.mark.parametrize("quoted", [False, True])
    def test_yaml_aliases_are_rejected(self, monkeypatch, loader_name, quoted):
        import yaml
        from wrangles.recipe_wrangles import convert

        if not hasattr(yaml, loader_name):
            pytest.skip(f"PyYAML {loader_name} is unavailable")
        loader = type("ObjectLoader", (getattr(yaml, loader_name),), {
            "yaml_implicit_resolvers": convert._ObjectYAMLLoader.yaml_implicit_resolvers,
        })
        monkeypatch.setattr(convert, "_ObjectYAMLLoader", loader)
        value = (
            "a: &a [one, two]\n"
            "b: &b [*a, *a, *a]\n"
            "c: [*b, *b, *b]"
        )
        if quoted:
            value = _json.dumps(value)
        df = wrangles.DataFrame({"column": [value]})

        with pytest.raises(ValueError, match="Unable to convert value"):
            df.wrangles.convert.parse(input="column")

        result = df.wrangles.convert.parse(input="column", default={})
        assert result["column"][0] == {}

    @pytest.mark.parametrize("value", [
        "&a [one, two]",
        "&a [*a]",
        "{part: !!int 00123}",
        "{time: !!float '12:34.5'}",
    ])
    def test_yaml_anchors_and_tags_are_rejected(self, value):
        with pytest.raises(ValueError, match="Unable to convert value"):
            wrangles.DataFrame({"column": [value]}).wrangles.convert.parse(input="column")

    def test_quoted_yaml_markers_remain_literal_text(self):
        df = wrangles.DataFrame({
            "column": ["{alias: '*part', anchor: '&part', tag: '!!int 00123'}"]
        }).wrangles.convert.parse(input="column")

        assert df["column"][0] == {
            "alias": "*part", "anchor": "&part", "tag": "!!int 00123",
        }

    def test_existing_yaml_converter_keeps_yaml_resolution(self):
        df = wrangles.DataFrame({
            "column": ["{part: 00123, code: 12:34, enabled: yes}"]
        }).wrangles.convert.from_yaml(input="column")

        assert df["column"][0] == {"part": 83, "code": 754, "enabled": True}

    def test_existing_objects_are_normalized(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [
                    {"number": _np.int64(2), "values": _np.array([1, 2])}
                ]
            })
        )

        assert df["column"][0] == {
            "number": 2,
            "values": [1, 2],
        }

    def test_numpy_defaults_are_normalized_and_independent(self):
        default = {"number": _np.int64(2), "values": _np.array([1, 2])}
        values = ["", "{bad", "[1, 2]"]
        df = wrangles.DataFrame({"first": values, "second": values})
        result = df.wrangles.convert.parse(
            input=["first", "second"], expected="dictionary", default=default,
        )

        records = result.to_dict("records")
        expected = {"number": 2, "values": [1, 2]}
        assert records == [{"first": expected, "second": expected}] * 3
        assert _json.loads(_json.dumps(records, allow_nan=False)) == records
        result["first"][0]["values"].append(3)
        assert result["first"][1]["values"] == [1, 2]
        assert result["second"][0]["values"] == [1, 2]
        assert default["values"].tolist() == [1, 2]

    @pytest.mark.parametrize("value", ["", "{bad", "{}"])
    @pytest.mark.parametrize("default", [
        {"value": _np.float64("nan")},
        {"value": {1, 2}},
        {"value": b"bytes"},
        {1: "non-string key"},
    ])
    def test_non_json_defaults_are_rejected(self, value, default):
        with pytest.raises(ValueError, match="Invalid default.*column"):
            wrangles.DataFrame({"column": [value]}).wrangles.convert.parse(
                input="column", default=default,
            )

    def test_recursive_default_is_rejected(self):
        default = {}
        default["self"] = default

        with pytest.raises(ValueError, match="Invalid default.*column"):
            wrangles.DataFrame({"column": [""]}).wrangles.convert.parse(
                input="column", default=default,
            )

    def test_excessively_nested_default_is_rejected(self):
        default = {"value": self._excessively_nested_value("object")}

        with pytest.raises(ValueError, match="Invalid default.*column"):
            wrangles.DataFrame({"column": [""]}).wrangles.convert.parse(
                input="column", default=default,
            )

    def test_expected_types_and_per_column_defaults(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input:
                  - dictionary
                  - array
                output:
                  - dictionary result
                  - array result
                expected:
                  - dictionary
                  - list
                default:
                  - {}
                  - []
            """,
            dataframe=pd.DataFrame({
                "dictionary": ["[1, 2]", "{bad"],
                "array": ['{"key": "value"}', "[1, 2]"],
            })
        )

        assert df["dictionary result"].tolist() == [{}, {}]
        assert df["array result"].tolist() == [[], [1, 2]]

    @pytest.mark.parametrize("expected", [
        "any", "dictionary", "list", "scalar",
        ["any"], ["dictionary", "list", "scalar"],
    ])
    def test_expected_schema_accepts_supported_categories(self, expected):
        import jsonschema
        import yaml

        schema = yaml.safe_load(wrangles.recipe._recipe_wrangles.convert.parse.__doc__)
        jsonschema.Draft7Validator.check_schema(schema)
        jsonschema.Draft7Validator(schema).validate({"input": "column", "expected": expected})

    @pytest.mark.parametrize("expected", [
        "banana", ["banana"], ["dictionary", "banana"], 1, None,
    ])
    def test_expected_schema_rejects_unsupported_categories(self, expected):
        import jsonschema
        import yaml

        schema = yaml.safe_load(wrangles.recipe._recipe_wrangles.convert.parse.__doc__)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft7Validator(schema).validate({"input": "column", "expected": expected})
        with pytest.raises(ValueError):
            wrangles.DataFrame({"column": ["{}"]}).wrangles.convert.parse(
                input="column", expected=expected,
            )

    def test_explicit_null_default(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                expected: dictionary
                default: null
            """,
            dataframe=pd.DataFrame({
                "column": ["not a dictionary"]
            })
        )

        # The recipe runner normalizes a null result to its standard empty cell.
        assert df["column"][0] == ""

    def test_invalid_nonempty_value_without_default_errors(self):
        with pytest.raises(ValueError, match="Unable to convert value"):
            wrangles.recipe.run(
                """
                wrangles:
                - convert.parse:
                    input: column
                    expected: dictionary
                """,
                dataframe=pd.DataFrame({
                    "column": ["{not closed"]
                })
            )

    @pytest.mark.parametrize("representation", ["json", "yaml", "object"])
    @pytest.mark.parametrize("via_recipe", [False, True])
    def test_excessive_nesting_uses_default(self, representation, via_recipe):
        value = self._excessively_nested_value(representation)
        original = wrangles.DataFrame({"column": [value, '{"ok": true}', value]})
        default = {}
        parameters = {"input": "column", "output": "parsed", "default": default}

        if via_recipe:
            df = wrangles.recipe.run(
                {"wrangles": [{"convert.parse": parameters}]}, dataframe=original,
            )
        else:
            df = original.wrangles.convert.parse(**parameters)

        assert df["parsed"].tolist() == [{}, {"ok": True}, {}]
        df.at[0, "parsed"]["changed"] = True
        assert df.at[2, "parsed"] == {}
        assert default == {}

    @pytest.mark.parametrize("representation", ["json", "yaml", "object"])
    @pytest.mark.parametrize("via_recipe", [False, True])
    def test_excessive_nesting_without_default_has_context(self, representation, via_recipe):
        value = self._excessively_nested_value(representation)
        original = wrangles.DataFrame({"column": [value]})

        with pytest.raises(ValueError, match="Unable to convert value in column 'column'") as error:
            if via_recipe:
                wrangles.recipe.run(
                    {"wrangles": [{"convert.parse": {"input": "column"}}]},
                    dataframe=original,
                )
            else:
                original.wrangles.convert.parse(input="column")

        assert "to a any object" in str(error.value)
        assert "Set a default" in str(error.value)

    def test_non_json_yaml_types_are_rejected(self):
        with pytest.raises(ValueError, match="Unable to convert value"):
            wrangles.recipe.run(
                """
                wrangles:
                - convert.parse:
                    input: column
                """,
                dataframe=pd.DataFrame({
                    "column": ["!!set {one: null, two: null}"]
                })
            )

    def test_multiple_inputs_require_matching_outputs(self):
        with pytest.raises(ValueError, match="same length"):
            wrangles.recipe.run(
                """
                wrangles:
                - convert.parse:
                    input:
                      - column 1
                      - column 2
                    output: result
                """,
                dataframe=pd.DataFrame({
                    "column 1": ["{}"],
                    "column 2": ["[]"],
                })
            )

    def test_empty_dataframe(self):
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.parse:
                input: column
                output: result
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )

        assert df.empty and df.columns.to_list() == ["column", "result"]


class TestConvertFromJSON:
    """
    Test convert.from_json wrangles
    """
    def test_array(self):
        """
        Test converting to a JSON array to a list
        """
        data = pd.DataFrame([['["val1", "val2"]']], columns=['header1'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: header1
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['header1'], list)

    def test_array_list_to_list(self):
        """
        Test converting to a JSON array to a list using a list of inputs and outputs
        """
        data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: 
                - header1
                - header2
                output:
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert isinstance(df.iloc[0]['out1'], list) and isinstance(df.iloc[0]['out2'], list)

    def test_array_list_to_single_output(self):
        """
        Test error with a list of inputs and a single output
        """
        data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: 
                - header1
                - header2
                output: out1
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_array_single_input_to_multi_output(self):
        """
        Test error with a single input and a list of outputs
        """
        data = pd.DataFrame([['["val1", "val2"]', '["val3", "val4"]']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.from_json:
                input: header1
                output: 
                - out1
                - out2
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_array_where(self):
        """
        Test converting to a JSON array to a list using where
        """
        data = pd.DataFrame({
            'header1': ['["val1", "val2"]', '["val3", "val4"]'],
            'numbers': [5, 7]
        })
        recipe = """
        wrangles:
            - convert.from_json:
                input: header1
                where: numbers > 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['header1'] == '["val1", "val2"]' and isinstance(df.iloc[1]['header1'], list)

    def test_error(self):
        """
        Test that bad values return an appropriate error
        """
        with pytest.raises(ValueError) as error:
            wrangles.recipe.run(
                """
                wrangles:
                - convert.from_json:
                    input: header1
                """,
                dataframe=pd.DataFrame({
                    "header1": ["", '[1,2,3]']
                })
            )
        assert "Unable to load all rows as JSON" in error.value.args[0]

    def test_default_array(self):
        """
        Test that a default applies correctly for error values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                default: []
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '[1,2,3]']
            })
        )
        assert (
            df["header1"][0] == [] and
            df["header1"][1] == [1,2,3]
        )

    def test_default_dict_empty(self):
        """
        Test that a default applies correctly for empty values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                default: {}
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '[1,2,3]']
            })
        )
        assert (
            df["header1"][0] == {} and
            df["header1"][1] == [1,2,3]
        )

    def test_default_dict_error(self):
        """
        Test that a default applies correctly for error values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                default: {}
            """,
            dataframe=pd.DataFrame({
                "header1": ['{"a":"b":"c"}', '[1,2,3]']
            })
        )
        assert (
            df["header1"][0] == {} and
            df["header1"][1] == [1,2,3]
        )

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input: header1
                output: output column
            """,
            dataframe=pd.DataFrame({
                "header1": []
            })
        )
        assert df.empty and df.columns.to_list() == ['header1', 'output column']

    def test_default_list_single_column(self):
        """
        Test that a list of one default applies correctly when input is a list of one column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input:
                  - header1
                default:
                  - {}
                output:
                  - out1
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '[1,2,3]']
            })
        )
        assert df["out1"][0] == {} and df["out1"][1] == [1, 2, 3]

    def test_default_list_multiple_columns(self):
        """
        Test that a list of defaults applies one default per column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input:
                  - header1
                  - header2
                default:
                  - {}
                  - []
                output:
                  - out1
                  - out2
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '{"a": 1}'],
                "header2": ["", '[4,5,6]']
            })
        )
        assert (
            df["out1"][0] == {} and
            df["out1"][1] == {"a": 1} and
            df["out2"][0] == [] and
            df["out2"][1] == [4, 5, 6]
        )

    def test_default_list_one_applied_to_all_columns(self):
        """
        Test that a list of one default is unwrapped and applied to all columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input:
                  - header1
                  - header2
                default:
                  - {}
                output:
                  - out1
                  - out2
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '{"a": 1}'],
                "header2": ["", '{"b": 2}']
            })
        )
        assert (
            df["out1"][0] == {} and
            df["out1"][1] == {"a": 1} and
            df["out2"][0] == {} and
            df["out2"][1] == {"b": 2}
        )

    def test_default_list_length_mismatch_raises(self):
        """
        Test that a default list whose length doesn't match input raises an error
        """
        with pytest.raises(ValueError, match="same length"):
            wrangles.recipe.run(
                """
                wrangles:
                - convert.from_json:
                    input:
                      - header1
                      - header2
                    default:
                      - {}
                      - []
                      - null
                    output:
                      - out1
                      - out2
                """,
                dataframe=pd.DataFrame({
                    "header1": [""],
                    "header2": [""]
                })
            )

    def test_default_list_complex_values_no_output(self):
        """
        Test a list of complex defaults (dict and list) with no output specified,
        overwriting the input columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_json:
                input:
                  - header1
                  - header2
                default:
                  - my_output:
                      key1: Val1
                      key2: Val2
                  - [this, is, a, list]
            """,
            dataframe=pd.DataFrame({
                "header1": ["", '{"a": 1}'],
                "header2": ["", '[1,2,3]']
            })
        )
        assert (
            df["header1"][0] == {"my_output": {"key1": "Val1", "key2": "Val2"}} and
            df["header1"][1] == {"a": 1} and
            df["header2"][0] == ["this", "is", "a", "list"] and
            df["header2"][1] == [1, 2, 3]
        )


class TestConvertFromYAML:
    """
    Test convert.from_yaml wrangle
    """
    def test_default(self):
        """
        Test converting YAML to an object
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": ["key: val\nkey2:\n- list1\n- list2\n"]
            })
        )
        assert (
            _json.dumps(df['column'][0]) == 
            _json.dumps({"key": "val", "key2": ["list1", "list2"]})
        )

    def test_empty_default_list(self):
        """
        Test converting a YAML to an object
        with a default for empty values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                default: []
            """,
            dataframe=pd.DataFrame({
                "column": ["", "key: val\nkey2:\n- list1\n- list2\n"]
            })
        )
        assert (
            df["column"][0] == [] and
            df["column"][1]["key"] == "val"
        )

    def test_empty_default_dict(self):
        """
        Test converting a YAML to an object
        with a default for empty values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                default: {}
            """,
            dataframe=pd.DataFrame({
                "column": ["", "key: val\nkey2:\n- list1\n- list2\n"]
            })
        )
        assert (
            df["column"][0] == {} and
            df["column"][1]["key"] == "val"
        )

    def test_error_default_dict(self):
        """
        Test converting YAML to an object
        with a default for error values
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                default: {}
            """,
            dataframe=pd.DataFrame({
                "column": [
                    " key: val\nkey2:\n- list1\n- list2\n",
                    "key: val\nkey2:\n- list1\n- list2\n"
                ]
            })
        )
        assert (
            df["column"][0] == {} and
            df["column"][1]["key"] == "val"
        )

    def test_where(self):
        """
        Test converting YAML to an object with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                output: output col
                where: numbers > 6
            """,
            dataframe=pd.DataFrame({
                "column": [
                    "key: val\nkey2:\n- list1\n- list2\n",
                    "key3: val\nkey4:\n- list1\n- list2\n",
                    "key5: val\nkey6:\n- list1\n- list2\n",
                    ],
                "numbers": [5, 7, 8]
            })
        )
        assert (
            df['output col'][0]== '' and
            df['output col'][1]["key3"] == "val"
        )

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']

    def test_default_list_single_column(self):
        """
        Test that a list of one default applies correctly when input is a list of one column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input:
                  - column
                default:
                  - {}
                output:
                  - out1
            """,
            dataframe=pd.DataFrame({
                "column": ["", "key: val\n"]
            })
        )
        assert df["out1"][0] == {} and df["out1"][1] == {"key": "val"}

    def test_default_list_multiple_columns(self):
        """
        Test that a list of defaults applies one default per column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input:
                  - col1
                  - col2
                default:
                  - {}
                  - []
                output:
                  - out1
                  - out2
            """,
            dataframe=pd.DataFrame({
                "col1": ["", "key: val\n"],
                "col2": ["", "- item1\n"]
            })
        )
        assert (
            df["out1"][0] == {} and
            df["out1"][1] == {"key": "val"} and
            df["out2"][0] == [] and
            df["out2"][1] == ["item1"]
        )

    def test_default_list_one_applied_to_all_columns(self):
        """
        Test that a list of one default is unwrapped and applied to all columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input:
                  - col1
                  - col2
                default:
                  - {}
                output:
                  - out1
                  - out2
            """,
            dataframe=pd.DataFrame({
                "col1": ["", "key: val\n"],
                "col2": ["", "key2: val2\n"]
            })
        )
        assert (
            df["out1"][0] == {} and
            df["out1"][1] == {"key": "val"} and
            df["out2"][0] == {} and
            df["out2"][1] == {"key2": "val2"}
        )

    def test_default_list_length_mismatch_raises(self):
        """
        Test that a default list whose length doesn't match input raises an error
        """
        with pytest.raises(ValueError, match="same length"):
            wrangles.recipe.run(
                """
                wrangles:
                - convert.from_yaml:
                    input:
                      - col1
                      - col2
                    default:
                      - {}
                      - []
                      - null
                    output:
                      - out1
                      - out2
                """,
                dataframe=pd.DataFrame({
                    "col1": [""],
                    "col2": [""]
                })
            )

    def test_default_list_complex_values_no_output(self):
        """
        Test a list of complex defaults (dict and list) with no output specified,
        overwriting the input columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.from_yaml:
                input:
                  - col1
                  - col2
                default:
                  - my_output:
                      key1: Val1
                      key2: Val2
                  - [this, is, a, list]
            """,
            dataframe=pd.DataFrame({
                "col1": ["", "a: 1\n"],
                "col2": ["", "- 1\n- 2\n- 3\n"]
            })
        )
        assert (
            df["col1"][0] == {"my_output": {"key1": "Val1", "key2": "Val2"}} and
            df["col1"][1] == {"a": 1} and
            df["col2"][0] == ["this", "is", "a", "list"] and
            df["col2"][1] == [1, 2, 3]
        )

    def test_from_yaml_to_yaml_roundtrip_reported_data(self):
        """
        Regression test for a reported round-trip bug (PR #987 review):
        convert.from_yaml -> convert.to_yaml on multiple wildcard-matched
        columns with per-column defaults should be idempotent - running
        from_yaml again on the round-tripped output must reproduce the
        same parsed values, for every row, including a row with a
        malformed/empty cell that must fall back to its column's default.
        """
        df = pd.DataFrame({
            "Top 1": [
                "Score: 0.295\nValue: Blade Runner",
                "Score: 0.234\nValue: Interstellar",
                "Score: 0.291\nValue: Interstellar",
            ],
            "Top 2": [
                "[]",
                "Score: 0.22\nValue: Westworld",
                "Score: 0.248\nValue: Blade Runner",
            ],
            "Top 3": [
                "Score: 0.174\nValue: Westworld",
                "'",
                "Score: 0.195\nValue: Westworld",
            ],
        })
        recipe = """
        wrangles:
          - convert.from_yaml:
              input:
                - Top *
              default:
                - {}
                - []
                - ''
        """
        parsed = wrangles.recipe.run(recipe, dataframe=df.copy())

        assert parsed.to_dict(orient="records") == [
            {
                "Top 1": {"Score": 0.295, "Value": "Blade Runner"},
                "Top 2": [],
                "Top 3": {"Score": 0.174, "Value": "Westworld"},
            },
            {
                "Top 1": {"Score": 0.234, "Value": "Interstellar"},
                "Top 2": {"Score": 0.22, "Value": "Westworld"},
                # Malformed cell ("'") fails to parse and falls back to the default
                "Top 3": "",
            },
            {
                "Top 1": {"Score": 0.291, "Value": "Interstellar"},
                "Top 2": {"Score": 0.248, "Value": "Blade Runner"},
                "Top 3": {"Score": 0.195, "Value": "Westworld"},
            },
        ]

        roundtripped = wrangles.recipe.run(
            """
            wrangles:
              - convert.from_yaml:
                  input:
                    - Top *
                  default:
                    - {}
                    - []
                    - ''
              - convert.to_yaml:
                  input:
                    - Top *
              - convert.from_yaml:
                  input:
                    - Top *
                  default:
                    - {}
                    - []
                    - ''
            """,
            dataframe=df.copy()
        )

        assert parsed.to_dict(orient="records") == roundtripped.to_dict(orient="records")


class TestConvertToJSON:
    """
    Test convert.to_json wrangles
    """
    def test_array(self):
        """
        Test converting to a list to a JSON array
        """
        data = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - merge.to_list:
                input:
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == '["val1", "val2"]'

    def test_array_list_to_list(self):
        """
        Test converting to a list to a JSON array with a list of input and output columns
        """
        data = pd.DataFrame([[["val1", "val2"], ["val3", "val4"]]], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.to_json:
                input: 
                - header1
                - header2
                output: 
                - out1
                - out2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out1'] == '["val1", "val2"]' and df.iloc[0]['out2'] == '["val3", "val4"]'

    def test_array_single_input_to_multi_output(self):
        """
        Test converting to a list to a JSON array with a single input and a list of output columns
        """
        data = pd.DataFrame([[["val1", "val2"], ["val3", "val4"]]], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - convert.to_json:
                input: header1
                output: 
                - out1
                - out2
        """
        with pytest.raises(ValueError) as info:
            wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_array_where(self):
        """
        Test converting to a list to a JSON array using where
        """
        data = pd.DataFrame({
            'header1': ['val1', 'val2', 'val3'],
            'header2': ['val4', 'val5', 'val6'],
            'numbers': [2, 7, 4]
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input:
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
                where: numbers > 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == "" and df.iloc[1]['headers_json'] == '["val2", "val5"]'

    def test_array_indent(self):
        """
        Test converting to a list to a JSON array using indent
        """
        data = pd.DataFrame([['val1', 'val2']], columns=['header1', 'header2'])
        recipe = """
        wrangles:
            - merge.to_list:
                input:
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
                indent: 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == '[\n    "val1",\n    "val2"\n]'

    def test_array_sort_keys(self):
        """
        Test converting to a list to a JSON array using sort_keys
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        wrangles:
            - merge.to_dict:
                input:
                - header3
                - header1
                - header2
                output: headers
            - convert.to_json:
                input: headers
                output: headers_json
                sort_keys: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['headers_json'] == '{"header1": "val1", "header2": "val2", "header3": "val3"}'

    def test_ensure_ascii_true(self):
        """
        Test uncommon characters that require UTF encoding.
        With ascii as True these should show the encoded version.
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        read:
            - test:
                rows: 5
                values: 
                    column: this is a ° symbol
        wrangles:
            - merge.to_dict:
                input:
                - column
                output: column dict

            - convert.to_json:
                input: column dict
                output: column dict
                ensure_ascii: True
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column dict'] == '{"column": "this is a \\u00b0 symbol"}'

    def test_ensure_ascii_false(self):
        """
        Test uncommon characters that require UTF encoding.
        With ascii as false, these should not be encoded.
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        read:
            - test:
                rows: 5
                values: 
                    column: this is a ° symbol
        wrangles:
            - merge.to_dict:
                input:
                - column
                output: column dict

            - convert.to_json:
                input: column dict
                output: column dict
                ensure_ascii: False
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column dict'] == '{"column": "this is a ° symbol"}'

    def test_ensure_ascii_default(self):
        """
        Test uncommon characters that require UTF encoding.
        With default settings, these should not be encoded.
        """
        data = pd.DataFrame([['val3', 'val1', 'val2']], columns=['header3', 'header1', 'header2'])
        recipe = """
        read:
            - test:
                rows: 5
                values: 
                    column: this is a ° symbol
        wrangles:
            - merge.to_dict:
                input:
                - column
                output: column dict

            - convert.to_json:
                input: column dict
                output: column dict
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['column dict'] == '{"column": "this is a ° symbol"}'

    def test_numpy_array(self):
        """
        Test converting a numpy array to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [_np.array([1, "a"], dtype=object)]
            })
        )
        assert df['column'][0] == '[1, "a"]'

    def test_datetime(self):
        """
        Test converting a datetime to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [pd.Timestamp('2020-01-01')]
            })
        )
        assert df['column'][0][:22] == '["2020-01-01T00:00:00.'

    def test_numpy_float(self):
        """
        Test converting a numpy float to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [[_np.float32(1)]]
            }, dtype=object)
        )
        assert df['column'][0] == '[1.0]'

    def test_numpy_int(self):
        """
        Test converting a numpy float to json
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [[_np.int32(1)]]
            }, dtype=object)
        )
        assert df['column'][0] == '[1]'

    def test_multiple_input_single_output(self):
        """
        Test providing multiple inputs but only one output
        Should merge to a dictionary before converting to JSON
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  column1: a
                  column2:
                    b: 1
            wrangles:
            - convert.to_json:
                input:
                  - column1
                  - column2
                output: result
            """
        )
        assert df['result'][0] == r'{"column1": "a", "column2": {"b": 1}}'

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_json:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']

    def test_scalar_string_to_json_array(self):
        """
        Test converting a scalar string to a JSON array
        """
        data = pd.DataFrame({'Test': ['abcd']})
        recipe = """
        wrangles:
            - convert.to_json:
                input: Test
                output: Test_json
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Test_json'] == '["abcd"]'
    
    def test_multiple_scalar_columns_to_json_array(self):
        """
        Test converting multiple scalar columns to JSON arrays
        """
        data = pd.DataFrame({
            'col1': ['a'],
            'col2': ['b']
        })
        recipe = """
        wrangles:
            - convert.to_json:
                input:
                - col1
                - col2
                output:
                - col1_json
                - col2_json
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['col1_json'] == '["a"]' and df.iloc[0]['col2_json'] == '["b"]'

    def test_mixed_scalar_and_list_columns_to_json_array(self):
        """
        Test converting a scalar and a list column to JSON arrays
        """
        data = pd.DataFrame({
            'col1': ['a'],
            'col2': [['b', 'c']]
        })
        recipe = """
        wrangles:
            - convert.to_json:
                input:
                - col1
                - col2
                output:
                - col1_json
                - col2_json
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['col1_json'] == '["a"]' and df.iloc[0]['col2_json'] == '["b", "c"]'

    def test_numeric_scalar_column_to_json_array(self):
        """
        Test converting a numeric scalar column to a JSON array
        """
        data = pd.DataFrame({'num': [123]})
        recipe = """
        wrangles:
            - convert.to_json:
                input: num
                output: num_json
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['num_json'] == '[123]'
        

class TestConvertToYAML:
    """
    Test convert.to_yaml wrangle
    """
    def test_default(self):
        """
        Test converting an object to YAML
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [{"key": "val", "key2": ["list1", "list2"]}]
            })
        )
        assert df['column'][0] == "key: val\nkey2:\n- list1\n- list2\n"

    def test_sort_order_default(self):
        """
        Test that an object converted to YAML
        maintains its order using the default settings
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [{"key2": "val", "key1": ["list1", "list2"]}]
            })
        )
        assert df['column'][0] == "key2: val\nkey1:\n- list1\n- list2\n"

    def test_sort_keys_true(self):
        """
        Test specifying sort_keys: true
        for convert.to_yaml
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
                sort_keys: true
            """,
            dataframe=pd.DataFrame({
                "column": [{"key2": "val", "key1": ["list1", "list2"]}]
            })
        )
        assert df['column'][0] == "key1:\n- list1\n- list2\nkey2: val\n"

    def test_multi_input_single_output(self):
        """
        Test providing multiple inputs but only one output
        Should merge to a dictionary before converting to YAML
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                  column1: a
                  column2:
                    b: 1
            wrangles:
            - convert.to_yaml:
                input:
                  - column1
                  - column2
                output: result
            """
        )
        assert df['result'][0] == 'column1: a\ncolumn2:\n  b: 1\n'

    def test_unicode_characters(self):
        """
        Test that unicode characters are encoded correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
            """,
            dataframe=pd.DataFrame({
                "column": [{"key": "this is a ° symbol"}]
            })
        )
        assert df['column'][0] == 'key: this is a ° symbol\n'

    def test_where(self):
        """
        Test converting an object to YAML with where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
                output: output col
                where: numbers > 6
            """,
            dataframe=pd.DataFrame({
                "column": [
                        {"key": "val", "key2": ["list1", "list2"]},
                        {"key3": "val", "key4": ["list1", "list2"]},
                        {"key5": "val", "key6": ["list1", "list2"]},
                ],
                "numbers": [5, 7, 8]
            })
        )
        assert (
            df['output col'][0] == "" and
            df['output col'][1] == "key3: val\nkey4:\n- list1\n- list2\n"
        )

    def test_empty(self):
        """
        Test that empty values are handled correctly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - convert.to_yaml:
                input: column
                output: output column
            """,
            dataframe=pd.DataFrame({
                "column": []
            })
        )
        assert df.empty and df.columns.to_list() == ['column', 'output column']
