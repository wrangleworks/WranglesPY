import wrangles
import pandas as pd
import pytest
from copy import deepcopy


class TestStructureMergeAliases:
    """Issue #1259: structural ownership with unchanged merge recipes."""

    names = {
        'coalesce': 'coalesce', 'concatenate': 'concatenate',
        'merge_dictionaries': 'dictionaries', 'key_value_pairs': 'key_value_pairs',
        'merge_lists': 'lists', 'to_list': 'to_list', 'to_dictionary': 'to_dict',
    }

    @pytest.fixture(autouse=True)
    def block_http(self, monkeypatch):
        def blocked(*args, **kwargs):
            pytest.fail('Merge alias tests must not contact live services')
        monkeypatch.setattr('requests.sessions.Session.request', blocked)

    @pytest.fixture(params=list(names))
    def merge_case(self, request):
        name = request.param
        data, options, values = {
            'coalesce': ({'A': ['', 'second', ''], 'B': ['first', 'fallback', 'third']},
                         {}, ['first', 'second', 'third']),
            'concatenate': ({'A': ['a', '', 'c'], 'B': ['x', 'y', '']},
                            {'char': '|'}, ['a|x', '|y', 'c|']),
            'merge_dictionaries': ({'A': [{'x': 1}, {}, {'x': 3}], 'B': [{'x': 2, 'y': 4}, {'z': 5}, {}]},
                                   {}, [{'x': 2, 'y': 4}, {'z': 5}, {'x': 3}]),
            'merge_lists': ({'A': [['a', 'A'], [], ['c']], 'B': [['a', 'b'], ['z'], []]},
                            {}, [['a', 'A', 'a', 'b'], ['z'], ['c']]),
            'key_value_pairs': ({'K1': ['color', 'size', 'empty'], 'V1': ['red', 'M', ''],
                                 'K2': ['size', 'size', 'tag'], 'V2': ['S', 'L', 'last']},
                                {'input': {'K1': 'V1', 'K2': 'V2'}},
                                [{'color': 'red', 'size': 'S'}, {'size': 'L'}, {'empty': '', 'tag': 'last'}]),
            'to_list': ({'A': ['a', '', 'c'], 'B': ['x', 'y', '']}, {}, [['a', 'x'], ['y'], ['c']]),
            'to_dictionary': ({'A': ['a', '', 'c'], 'B': ['x', 'y', '']},
                              {}, [{'A': 'a', 'B': 'x'}, {'B': 'y'}, {'A': 'c'}]),
        }[name]
        frame = pd.DataFrame({**data, 'Keep': [3, 1, 2]}, index=pd.Index([9, 2, 7], name='row'))
        params = {'input': ['A', 'B'], 'output': 'Out', **options}
        return name, frame, params, frame.assign(Out=values)

    def operations(self, name):
        return f'merge.{self.names[name]}', f'structure.{name}'

    def run_recipe(self, operation, frame, params, **kwargs):
        return wrangles.recipe.run({'wrangles': [{operation: deepcopy(params)}]},
                                   dataframe=deepcopy(frame), **kwargs)

    def assert_frame(self, result, expected):
        pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(expected))
        # DataFrame equality checks dictionary values but ignores key insertion order.
        for actual, wanted in zip(result.get('Out', []), expected.get('Out', [])):
            if isinstance(wanted, dict):
                assert list(actual) == list(wanted)

    @pytest.mark.parametrize('entrypoint', ['recipe', 'module'])
    def test_recipe_and_module_results_share_canonical_implementation(self, merge_case, entrypoint):
        from wrangles import recipe_wrangles

        name, frame, params, expected = merge_case
        canonical = getattr(recipe_wrangles.structure, name)
        assert canonical.__module__ == 'wrangles.recipe_wrangles.structure'
        assert getattr(recipe_wrangles.merge, self.names[name]) is canonical
        for operation in self.operations(name):
            if entrypoint == 'recipe':
                result = self.run_recipe(operation, frame, params)
            else:
                namespace, method = operation.split('.')
                result = getattr(getattr(recipe_wrangles, namespace), method)(deepcopy(frame), **deepcopy(params))
            self.assert_frame(result, expected)

    def test_existing_merge_accessor_preserves_source(self, merge_case):
        from wrangles.dataframe import DataFrame

        name, frame, params, expected = merge_case
        source = DataFrame(deepcopy(frame))
        result = getattr(source.wrangles.merge, self.names[name])(**deepcopy(params))
        self.assert_frame(result, expected)
        self.assert_frame(source, frame)

    @pytest.mark.parametrize('where, bindings', [
        ('Keep >= 2', {}), ('Keep >= ?', {'where_params': [2]}),
        ('Keep >= :minimum', {'where_params': {'minimum': 2}}),
    ])
    def test_where_and_bound_parameters_merge_back(self, merge_case, where, bindings):
        name, frame, params, expected = merge_case
        frame = frame.assign(Out='UNCHANGED')
        expected.at[2, 'Out'] = 'UNCHANGED'
        for operation in self.operations(name):
            self.assert_frame(self.run_recipe(operation, frame, {**params, 'where': where,
                              'if': 'row_count > 0', **bindings}), expected)

    def test_no_matching_where_retains_original_rows(self, merge_case):
        name, frame, params, _ = merge_case
        for operation in self.operations(name):
            self.assert_frame(self.run_recipe(operation, frame, {**params, 'where': 'Keep > 99'}),
                              frame.assign(Out=''))

    @pytest.mark.parametrize('enabled', [True, False])
    def test_conditional_execution(self, merge_case, enabled):
        name, frame, params, expected = merge_case
        for operation in self.operations(name):
            result = self.run_recipe(operation, frame, {**params, 'if': '${enabled}'}, variables={'enabled': enabled})
            self.assert_frame(result, expected if enabled else frame)

    def test_false_if_skips_invalid_input(self, merge_case):
        name, frame, _, _ = merge_case
        for operation in self.operations(name):
            self.assert_frame(self.run_recipe(operation, frame, {'input': 'Missing*', 'output': 'Out',
                              'if': 'row_count < 0'}), frame)

    def test_empty_frame_preserves_columns_and_dtypes(self, merge_case):
        name, frame, params, expected = merge_case
        expected = expected.iloc[:0].astype({'Out': 'object' if name == 'coalesce' else 'float64'})
        for operation in self.operations(name):
            self.assert_frame(self.run_recipe(operation, frame.iloc[:0], params), expected)

    def test_missing_input_preserves_meaningful_error(self, merge_case):
        name, frame, params, _ = merge_case
        params['input'] = {'Missing': 'V1'} if name == 'key_value_pairs' else 'Missing'
        for operation in self.operations(name):
            with pytest.raises(KeyError, match='Missing'):
                self.run_recipe(operation, frame, params)

    def test_coalesce_null_empty_zero_false_and_whitespace(self):
        frame = pd.DataFrame({'A': [None, '', 0, False, '   ', 'kept'],
                              'B': ['x', 'y', 'zero', 'bool', '  next  ', 'unused']})
        expected = frame.assign(A=['', '', 0, False, '   ', 'kept'], Out=['x', 'y', 0, False, 'next', 'kept'])
        for operation in self.operations('coalesce'):
            result = self.run_recipe(operation, frame, {'input': ['A', 'B'], 'output': 'Out'})
            self.assert_frame(result, expected)
            assert type(result.at[2, 'Out']) is int
            assert type(result.at[3, 'Out']) is bool

    @pytest.mark.parametrize('explicit_output', [False, True])
    def test_coalesce_single_list_and_default_output(self, explicit_output):
        frame = pd.DataFrame({'A': [[None, '', 'next'], [0, 'z'], [False, 'z'], ['  ', ' a '], [], ['']]})
        params = {'input': 'A', **({'output': 'Out'} if explicit_output else {})}
        expected = frame.assign(**{'Out' if explicit_output else 'A': ['next', 0, False, 'a', '', '']})
        for operation in self.operations('coalesce'):
            self.assert_frame(self.run_recipe(operation, frame, params), expected)

    def test_coalesce_multiple_columns_requires_output(self):
        for operation in self.operations('coalesce'):
            with pytest.raises(ValueError, match='An output column must be provided'):
                self.run_recipe(operation, pd.DataFrame({'A': ['a'], 'B': ['b']}), {'input': ['A', 'B']})

    @pytest.mark.parametrize('skip_empty, values', [(False, ['0|False||None|a', '|b', '']),
                                                   (True, ['a', 'b', ''])])
    def test_concatenate_list_values_and_skip_empty(self, skip_empty, values):
        frame = pd.DataFrame({'A': [[0, False, '', None, 'a'], ['', 'b'], []]})
        for operation in self.operations('concatenate'):
            result = self.run_recipe(operation, frame, {'input': 'A', 'output': 'Out', 'char': '|', 'skip_empty': skip_empty})
            self.assert_frame(result, frame.assign(Out=values))

    @pytest.mark.parametrize('skip_empty, values', [(False, ['None|x', '|y', ' |']),
                                                   (True, ['None|x', 'y', ' '])])
    def test_concatenate_column_stringification_and_skip_empty(self, skip_empty, values):
        frame = pd.DataFrame({'A': [None, '', ' '], 'B': ['x', 'y', '']})
        expected = frame.assign(A=['', '', ' '], Out=values)
        for operation in self.operations('concatenate'):
            result = self.run_recipe(operation, frame, {'input': ['A', 'B'], 'output': 'Out', 'char': '|', 'skip_empty': skip_empty})
            self.assert_frame(result, expected)

    @pytest.mark.parametrize('skip_empty, values', [
        (False, [{'x': '', 'a': 2}, {'zero': 0, 'false': False, 'none': None, 'blank': '  '}]),
        (True, [{'x': 1, 'a': 2}, {'zero': 0, 'false': False}]),
    ])
    def test_dictionary_conflicts_order_and_skip_empty(self, skip_empty, values):
        frame = pd.DataFrame({'A': [{'x': 1, 'a': 2}, {'zero': 0, 'false': False, 'none': None, 'blank': '  '}],
                              'B': [{'x': ''}, {}]})
        for operation in self.operations('merge_dictionaries'):
            result = self.run_recipe(operation, frame, {'input': ['A', 'B'], 'output': 'Out', 'skip_empty': skip_empty})
            self.assert_frame(result, frame.assign(Out=values))

    @pytest.mark.parametrize('options, values', [
        ({}, [['a', 'A', '', 'a', 'b'], ['0', 'False']]),
        ({'remove_duplicates': True}, [['a', 'A', '', 'b'], ['0', 'False']]),
        ({'remove_duplicates': True, 'ignore_case': True}, [['a', '', 'b'], ['0', 'False']]),
        ({'include_empty': False}, [['a', 'A', 'a', 'b'], ['0', 'False']]),
    ])
    def test_merge_lists_duplicates_case_scalars_and_empties(self, options, values):
        frame = pd.DataFrame({'A': [['a', 'A', ''], 0], 'B': [['a', 'b'], False]})
        for operation in self.operations('merge_lists'):
            result = self.run_recipe(operation, frame, {'input': ['A', 'B'], 'output': 'Out', **options})
            self.assert_frame(result, frame.assign(Out=values))

    @pytest.mark.parametrize('skip_empty', [False, True])
    def test_key_value_literal_column_mapping(self, skip_empty):
        frame = pd.DataFrame({'Key [1]': ['Color', ''], 'Value [1]': ['Red', ''], 'Keep': [3, 1]}, index=[7, 2])
        expected = frame.assign(Out=[{'Color': 'Red'}, {} if skip_empty else {'': ''}])
        for operation in self.operations('key_value_pairs'):
            result = self.run_recipe(operation, frame, {'input': {'Key [1]': 'Value [1]'}, 'output': 'Out', 'skip_empty': skip_empty})
            self.assert_frame(result, expected)

    @pytest.mark.parametrize('skip_empty, values', [
        (False, [{'x': 'last'}, {'': 'empty', 'y': ''}]),
        (True, [{'x': 'last'}, {}]),
    ])
    def test_key_value_wildcards_conflicts_and_skip_empty(self, skip_empty, values):
        frame = pd.DataFrame({'K1': ['x', ''], 'K2': ['x', 'y'],
                              'V1': ['first', 'empty'], 'V2': ['last', '']})
        for operation in self.operations('key_value_pairs'):
            result = self.run_recipe(operation, frame, {'input': {'K*': 'V*'}, 'output': 'Out', 'skip_empty': skip_empty})
            self.assert_frame(result, frame.assign(Out=values))
            empty = self.run_recipe(operation, frame, {'input': {'MissingK*': 'MissingV*'}, 'output': 'Out'})
            self.assert_frame(empty, frame.assign(Out=[{}, {}]))

    def test_key_value_boolean_conversion_preserves_source_mutation(self):
        frame = pd.DataFrame({'K': ['a', 'b', 'c'], 'V': [True, False, None]})
        expected = pd.DataFrame({'K': ['a', 'b', 'c'], 'V': ['True', 'False', 'None'],
                                 'Out': [{'a': True}, {'b': False}, {'c': 'None'}]})
        for operation in self.operations('key_value_pairs'):
            result = self.run_recipe(operation, frame, {'input': {'K': 'V'}, 'output': 'Out', 'skip_empty': True})
            self.assert_frame(result, expected)

    @pytest.mark.parametrize('include_empty', [False, True])
    def test_to_list_falsy_values_and_include_empty(self, include_empty):
        frame = pd.DataFrame({'A': pd.Series([0, False, None, ''], dtype=object), 'B': ['x', 'y', 'z', '']})
        values = [[0, 'x'], [False, 'y'], [None, 'z'], ['', '']] if include_empty else [['x'], ['y'], ['z'], []]
        expected = frame.assign(A=[0, False, '', ''], Out=values)
        for operation in self.operations('to_list'):
            self.assert_frame(self.run_recipe(operation, frame, {'input': ['A', 'B'], 'output': 'Out',
                              'include_empty': include_empty}), expected)

    @pytest.mark.parametrize('include_empty', [False, True])
    def test_to_dictionary_boolean_none_source_conversion(self, include_empty):
        frame = pd.DataFrame({'A': pd.Series([0, False, None, ''], dtype=object), 'B': ['x', 'y', 'z', '']})
        values = [{'A': '0', 'B': 'x'}, {'A': False, 'B': 'y'}, {'A': None, 'B': 'z'},
                  {'A': '', 'B': ''} if include_empty else {}]
        expected = frame.assign(A=['0', 'False', 'None', ''], Out=values)
        for operation in self.operations('to_dictionary'):
            result = self.run_recipe(operation, frame, {'input': ['A', 'B'], 'output': 'Out', 'include_empty': include_empty})
            self.assert_frame(result, expected)

    @pytest.mark.parametrize('pattern', [True, False])
    def test_wildcard_expansion_and_input_order(self, merge_case, pattern):
        name, frame, params, expected = merge_case
        if name == 'key_value_pairs':
            params['input'] = {'K*': 'V*'}
        elif pattern:
            params['input'] = 'regex:^(A|B)$'
        else:
            params['input'] = ['B', 'A']
            expected['Out'] = {
                'coalesce': ['first', 'fallback', 'third'],
                'concatenate': ['x|a', 'y|', '|c'],
                'merge_dictionaries': [{'x': 1, 'y': 4}, {'z': 5}, {'x': 3}],
                'merge_lists': [['a', 'b', 'a', 'A'], ['z'], ['c']],
                'to_list': [['x', 'a'], ['y'], ['c']],
                'to_dictionary': [{'B': 'x', 'A': 'a'}, {'B': 'y'}, {'A': 'c'}],
            }[name]
        for operation in self.operations(name):
            self.assert_frame(self.run_recipe(operation, frame, params), expected)

    @pytest.mark.parametrize('name, data, value', [
        ('coalesce', {'A': [''], 'B': ['first']}, 'first'),
        ('concatenate', {'A': ['a'], 'B': ['b']}, 'a,b'),
        ('merge_dictionaries', {'A': [{}], 'B': [{}]}, {}),
        ('merge_lists', {'A': [[]], 'B': [[]]}, []),
        ('key_value_pairs', {'A': ['a'], 'B': ['b']}, {}),
        ('to_list', {'A': [''], 'B': ['']}, []),
        ('to_dictionary', {'A': [''], 'B': ['']}, {}),
    ])
    def test_empty_input_keeps_existing_dispatch_semantics(self, name, data, value):
        frame = pd.DataFrame(data)
        params = {'input': {} if name == 'key_value_pairs' else [], 'output': 'Out'}
        for operation in self.operations(name):
            self.assert_frame(self.run_recipe(operation, frame, params), frame.assign(Out=[value]))

    @pytest.mark.parametrize('name, data, options, error, message', [
        ('merge_dictionaries', {'A': [None], 'B': [{}]}, {}, AttributeError, 'items'),
        ('merge_lists', {'A': [[1]], 'B': [[]]}, {'remove_duplicates': True, 'ignore_case': True}, AttributeError, 'lower'),
    ])
    def test_invalid_values_preserve_existing_errors(self, name, data, options, error, message):
        for operation in self.operations(name):
            with pytest.raises(error, match=message):
                self.run_recipe(operation, pd.DataFrame(data), {'input': ['A', 'B'], 'output': 'Out', **options})

    def test_generated_schema_preserves_all_alias_contracts(self, tmp_path, monkeypatch):
        import json
        import runpy
        from pathlib import Path
        import jsonschema

        root = Path(__file__).resolve().parents[3]
        (tmp_path / 'recipe_base_schema.json').write_bytes((root / 'schema/recipe_base_schema.json').read_bytes())
        monkeypatch.chdir(tmp_path)
        runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
        schema = json.loads((tmp_path / 'schema.json').read_text(encoding='utf-8'))
        props = schema['$defs']['wrangles']['items']['properties']
        for name in self.names:
            legacy, canonical = self.operations(name)
            assert props[canonical] == props[legacy]
            params = {'input': {'K*': 'V*'} if name == 'key_value_pairs' else ['A', 'B'], 'output': 'Out',
                      'where': 'Keep >= :minimum', 'where_params': {'minimum': 2}, 'if': 'row_count > 0'}
            if name == 'concatenate':
                params['char'] = '|'
            for operation in (legacy, canonical):
                jsonschema.validate({'wrangles': [{operation: params}]}, schema)
        for catalog_only_name in ('structure.dictionaries', 'structure.lists', 'structure.to_dict'):
            assert catalog_only_name not in props

    def test_existing_structure_split_exports_are_preserved(self):
        from wrangles.recipe_wrangles import split, structure

        for legacy, canonical in [('dictionary', 'split_dictionary'), ('list', 'split_list'),
                                   ('text', 'split_text'), ('tokenize', 'tokenize')]:
            assert getattr(structure, canonical) is getattr(split, legacy)


class TestMergeCoalesce:
    """
    Test merge.coalesce
    """
    def test_columns(self):
        """
        Test coalescing multiple columns into one
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input: 
                  - Col1
                  - Col2
                  - Col3
                output: Output Col
            """,
            dataframe=pd.DataFrame({
                'Col1': ['A', '', ''],
                'Col2': ['', 'B', ''],
                'Col3': ['', '', 'C']
            })
        )
        assert df['Output Col'].values.tolist() == ['A', 'B', 'C']

    def test_where(self):
        """
        Test coalesce using where
        """
        data = pd.DataFrame({
            'Col1': ['A', '', ''],
            'Col2': ['', 'B', ''],
            'Col3': ['', '', 'C'],
            'numbers': [3, 4, 5]
        })
        recipe = """
        wrangles:
        - merge.coalesce:
            input: 
                - Col1
                - Col2
                - Col3
            output: Output Col
            where: numbers = 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Output Col'] == 'B' and df.iloc[0]['Output Col'] ==''

    def test_lists(self):
        """
        Test coalesce with a single column containing a list
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: ["","b","c"]
            wrangles:
            - merge.coalesce:
                input: header
            """
        )
        assert df["header"][0] == 'b'

    def test_lists_with_output(self):
        """
        Test coalesce with a single column containing
        a list that defines an output column
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header: ["","b","c"]
            wrangles:
            - merge.coalesce:
                input: header
                output: result
            """
        )
        assert df["result"][0] == 'b'

    def test_lists_mixed_list_scalar(self):
        """
        Test coalesce with a single column that
        contains a mix of lists and scalars
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input: header
            """,
            dataframe=pd.DataFrame({
                'header': [["","bb","cc"], '', 'dd', ["ee", ""]]
            })
        )
        assert df["header"].to_list() == ['bb', '', 'dd', 'ee']

    def test_output_error(self):
        """
        Test that a clear error is given if trying to coalesce
        multiple columns but not giving an output
        """
        with pytest.raises(ValueError, match="output column must be provided"):
            wrangles.recipe.run(
                """
                read:
                  - test:
                      rows: 1
                      values:
                        header1: value1
                        header2: value2
                wrangles:
                  - merge.coalesce:
                      input:
                        - header1
                        - header2
                """
            )

    def test_coalesce_empty_dataframe(self):
        """
        Test coalesce with empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
        - merge.coalesce:
            input:
                - Col1
                - Col2
                - Col3
            output: Output Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Output Col']

    def test_all_floats(self):
        """
        Test coalescing two columns of all floats preserves the values and dtype
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input:
                    - Col1
                    - Col2
                output: Output Col
            """,
            dataframe=pd.DataFrame({
                'Col1': [5.56, 3.14, 9.91],
                'Col2': [4.12, 2.35, 7.76]
            })
        )
        assert df['Output Col'].tolist() == [5.56, 3.14, 9.91]

    def test_float_zero_not_skipped(self):
        """
        Test that 0.0 in a column is returned instead of falling back to the next column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input:
                  - Col1
                  - Col2
                output: Result
            """,
            dataframe=pd.DataFrame({
                'Col1': [0.0,  1.5,  float('nan')],
                'Col2': [9.9,  9.9,  9.9         ],
            })
        )
        assert df['Result'].tolist() == [0.0, 1.5, 9.9]

    def test_integer_zero_not_skipped(self):
        """
        Test that integer 0 in a column is returned instead of falling back to the next column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input:
                  - Col1
                  - Col2
                output: Result
            """,
            dataframe=pd.DataFrame({
                'Col1': [0,  1,  None],
                'Col2': [99, 99, 99  ],
            })
        )
        assert df['Result'].tolist() == [0, 1, 99]

    def test_false_not_skipped(self):
        """
        Test that boolean False in a column is returned instead of falling back to the next column
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input:
                  - Col1
                  - Col2
                output: Result
            """,
            dataframe=pd.DataFrame({
                'Col1': [False,      True,       None      ],
                'Col2': ['fallback', 'fallback', 'fallback'],
            })
        )
        assert df['Result'].tolist() == [False, True, 'fallback']

    def test_lists_falsy_values_not_skipped(self):
        """
        Test that falsy values (0, 0.0, False) inside a per-cell list are returned
        as the first valid element rather than being skipped
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - merge.coalesce:
                input: Col
            """,
            dataframe=pd.DataFrame({
                'Col': [
                    [0,     1,    2  ],
                    [0.0,   1.5,  2.5],
                    [False, True      ],
                    ['',   'b',  'c' ],
                ]
            })
        )
        assert df['Col'].tolist() == [0, 0.0, False, 'b']


class TestMergeConcatenate:
    """
    All concatenate tests
    """
    def test_concatenate_1(self):
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'C']]
        })
        recipe = """
        wrangles:
        - merge.concatenate:
            input: Col1
            output: Join List
            char: ' '
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Join List'] == 'A B C'
        
    # Multi column concat
    def test_concatenate_2(self):
        data = pd.DataFrame({
            'Col1': ['A'],
            'Col2': ['B'],
            'Col3': ['C']
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Join Col
                char: ', '
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Join Col'] == 'A, B, C'

    def test_concatenate_where(self):
        """
        Test concatenate using where
        """
        data = pd.DataFrame({
            'Col1': ['A', 'E', 'H'],
            'Col2': ['B', 'F', 'I'],
            'Col3': ['C', 'G', 'J'],
            'numbers': [23, 44, 13]
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Join Col
                char: ', '
                where: numbers !=13
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Join Col'] == 'A, B, C' and df.iloc[2]['Join Col'] == ''

    def test_where_single_column(self):
        """
        Test concatenate using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - merge.concatenate:
                    input: Col1
                    output: Col1
                    char: ', '
                    where: Col1 LIKE '%A%'
            """,
            dataframe=pd.DataFrame({
                'Col1': [['A', 'B', 'C'], [1,2,3], ['X', 'Y', 'Z']],
            })
        )
        assert df['Col1'].to_list() == ['A, B, C', [1,2,3], ['X','Y','Z']]

    def test_concatenate_integer(self):
        """
        Test that a non-string doesn't
        break the concatenation
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: ["a", 1]
            wrangles:
            - merge.concatenate:
                input: header1
                output: result
                char: ''
            """
        )
        assert df["result"][0] == 'a1'

    def test_concatenate_skip_empty_true(self):
        """
        Test skipping empty values as true
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: a
                    header2: ""
                    header3: b
            wrangles:
            - merge.concatenate:
                input:
                    - header1
                    - header2
                    - header3
                output: result
                char: '-'
                skip_empty: true
            """
        )
        assert df["result"][0] == 'a-b'

    def test_concatenate_skip_empty_false(self):
        """
        Test skipping empty values set as false
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: a
                    header2: ""
                    header3: b
            wrangles:
            - merge.concatenate:
                input:
                    - header1
                    - header2
                    - header3
                output: result
                char: '-'
                skip_empty: false
            """
        )
        assert df["result"][0] == 'a--b'

    def test_concatenate_skip_empty_default(self):
        """
        Test skipping empty values not provided
        """
        df = wrangles.recipe.run(
            """
            read:
            - test:
                rows: 1
                values:
                    header1: a
                    header2: ""
                    header3: b
            wrangles:
            - merge.concatenate:
                input:
                    - header1
                    - header2
                    - header3
                output: result
                char: '-'
            """
        )
        assert df["result"][0] == 'a--b'

    def test_concatenate_strings(self):
        """
        Test concatenate with a single column of strings (a bug)
        """
        data = pd.DataFrame({
            'Col1': ['AAAAAA', 'EEEEEE', 'HHHHHH'],
            'Col2': ['BBBBBB', 'FFFFFF', 'IIIIII'],
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: Col1
                output: Output Col
                char: ' '
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Output Col'] == 'AAAAAA' and df.iloc[2]['Output Col'] == 'HHHHHH'

    def test_concatenate_strings_skip_empty(self):
        """
        Test concatenate with a single column of strings (a bug) with skip empty
        """
        data = pd.DataFrame({
            'Col1': ['AAAAAA', 'EEEEEE', 'HHHHHH'],
            'Col2': ['BBBBBB', 'FFFFFF', 'IIIIII'],
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: Col1
                output: Output Col
                char: ' '
                skip_empty: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Output Col'] == 'AAAAAA' and df.iloc[2]['Output Col'] == 'HHHHHH'

    def test_concatenate_empty_dataframe(self):
        """
        Test concatenate with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.concatenate:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Output Col
                char: ', '
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Output Col']


class TestMergeLists:
    """
    Test merge.lists
    """
    def test_lists_1(self):
        """
        Joining lists together
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B']],
            'Col2': [['D', 'E']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'D', 'E']

    def test_lists_where(self):
        """
        Test merge.lists using where
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B'], ['C', 'D']],
            'Col2': [['D', 'E'], ['F', 'G']],
            'numbers': [0, 5]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                where: numbers > 0
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == '' and df.iloc[1]['Combined Col'] == ['C', 'D', 'F', 'G']

    def test_lists_remove_duplicates(self):
        """
        Test merge.lists using remove_duplicates
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'C'], ['F', 'G', 'H']],
            'Col2': [['D', 'E', 'C'], ['F', 'G', 'I']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                remove_duplicates: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'C', 'D', 'E'] and df.iloc[1]['Combined Col'] == ['F', 'G', 'H', 'I']

    def test_lists_remove_duplicates_ignore_case_true(self):
        """
        Test merge.lists using remove_duplicates with ignore_case set to true
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'c'], ['f', 'G', 'H']],
            'Col2': [['D', 'E', 'C'], ['F', 'g', 'I']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                remove_duplicates: true
                ignore_case: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'c', 'D', 'E'] and df.iloc[1]['Combined Col'] == ['f', 'G', 'H', 'I']

    def test_lists_remove_duplicates_ignore_case_false(self):
        """
        Test merge.lists using remove_duplicates with ignore_case set to false
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B', 'c'], ['f', 'G', 'H']],
            'Col2': [['D', 'E', 'C'], ['F', 'g', 'I']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                remove_duplicates: true
                ignore_case: false
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'c', 'D', 'E', 'C'] and df.iloc[1]['Combined Col'] == ['f', 'G', 'H', 'F', 'g', 'I']

    def test_lists_ignore_case_false(self):
        """
        Test merge.lists using with ignore_case without remove_duplicates
        """
        data = pd.DataFrame({
            'Col1': [['A', 'B'], ['f', 'G']],
            'Col2': [['D', 'B'], ['F', 'g']]
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                ignore_case: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'D', 'B'] and df.iloc[1]['Combined Col'] == ['f', 'G', 'F', 'g']

    def test_lists_empty_dataframe(self):
        """
        Test merge.lists with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Combined Col']

    def test_lists_include_empty_true(self):
        """
        Test merge.lists with include_empty=True (should include empty strings)
        """
        data = pd.DataFrame({
            'Col1': ['', 'A', 'B'],  # String column with empty value
            'Col2': [['C', 'D'], ['E'], ['F', 'G']]  # List column
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                include_empty: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['', 'C', 'D']
        assert df.iloc[1]['Combined Col'] == ['A', 'E']
        assert df.iloc[2]['Combined Col'] == ['B', 'F', 'G']

    def test_lists_include_empty_false(self):
        """
        Test merge.lists with include_empty=False (should filter out empty strings)
        """
        data = pd.DataFrame({
            'Col1': ['', 'A', 'B'],  # String column with empty value
            'Col2': [['C', 'D'], ['E'], ['F', 'G']]  # List column
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                include_empty: false
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['C', 'D']  # Empty string filtered out
        assert df.iloc[1]['Combined Col'] == ['A', 'E']
        assert df.iloc[2]['Combined Col'] == ['B', 'F', 'G']

    def test_lists_include_empty_default(self):
        """
        Test merge.lists with default include_empty (should be True for backward compatibility)
        """
        data = pd.DataFrame({
            'Col1': ['', 'A'],  # String column with empty value
            'Col2': [['C', 'D'], ['E']]  # List column
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        # Default should include empty strings for backward compatibility
        assert df.iloc[0]['Combined Col'] == ['', 'C', 'D']
        assert df.iloc[1]['Combined Col'] == ['A', 'E']

    def test_lists_include_empty_mixed_input(self):
        """
        Test merge.lists with include_empty=False and mixed list/string inputs including empty values in lists
        """
        data = pd.DataFrame({
            'Col1': ['', 'A'],  # String column with empty value
            'Col2': [['', 'B', ''], ['C', '']]  # List column with empty values
        })
        recipe = """
        wrangles:
            - merge.lists:
                input: 
                    - Col1
                    - Col2
                output: Combined Col
                include_empty: false
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        # Should filter out all empty strings
        assert df.iloc[0]['Combined Col'] == ['B']
        assert df.iloc[1]['Combined Col'] == ['A', 'C']


class TestMergeToList:
    """
    Test merge.to_list
    """
    def test_to_lists_1(self):
        data = pd.DataFrame({
            'Col1': ['A'],
            'Col2': ['B'],
            'Col3': ['C']
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == ['A', 'B', 'C']
        
    def test_to_lists_where(self):
        """
        Test merge.to_list using where
        """
        data = pd.DataFrame({
            'Col1': ['A', 'D', 'G'],
            'Col2': ['B', 'E', 'H'],
            'Col3': ['C', 'F', 'I'],
            'numbers': [3, 6, 9]
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
                where: numbers = 6
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Combined Col'] == '' and df.iloc[1]['Combined Col'] == ['D', 'E', 'F']

    def test_to_lists_empty_dataframe(self):
        """
        Test merge.to_list with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.to_list:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Combined Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Combined Col']


class TestMergeToDict:
    """
    Test merge.to_dict
    """
    def test_to_dict_1(self):
        data = pd.DataFrame({
        'Col1':[{'A'}],
        'Col2':[{'B'}]
    })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: 
                    - Col1
                    - Col2
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': {'A'}, 'Col2': {'B'}}

    def test_to_dict_2(self):
        """
        Input is a wildcard
        """
        data = pd.DataFrame({
        'Col1':[{'A'}],
        'Col2':[{'B'}]
    })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: Col*
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': {'A'}, 'Col2': {'B'}}

    def test_to_dict_3(self):
        """
        If the row instance is a boolean type
        """
        data = pd.DataFrame({
            'Col1':[True],
            'Col2':[False],
            'Col3': [None],
        })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: Col*
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': True, 'Col2': False, 'Col3': None}

    def test_to_dict_where(self):
        """
        Test merge.to_dict using where
        """
        data = pd.DataFrame({
            'Col1':['A', 'C', 'E'],
            'Col2':['B', 'D', 'F'],
            'numbers': [43, 22, 65]
        })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: 
                    - Col1
                    - Col2
                output: Dict Col
                where: numbers < 60
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Dict Col'] == {'Col1': 'A', 'Col2': 'B'} and df.iloc[2]['Dict Col'] == ''

    def test_to_dict_empty_dataframe(self):
        """
        Test merge.to_dict with an empty dataframe
        """
        data = pd.DataFrame({
            'Col1': [],
            'Col2': [],
            'Col3': []
        })
        recipe = """
        wrangles:
            - merge.to_dict:
                input: 
                    - Col1
                    - Col2
                    - Col3
                output: Dict Col
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['Col1', 'Col2', 'Col3', 'Dict Col']


class TestMergeKeyValuePairs:
    """
    Test merge.key_value_pairs
    """
    def test_key_value_pairs_1(self):
        data = pd.DataFrame({
        'Letter': ['A', 'B', 'C'],
        'Number': [1, 2, 3],
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  Letter: Number
                output: Pairs
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[2]['Pairs'] == {'C': 3}

    def test_key_value_pairs_where(self):
        """
        Test merge.key_value_pairs using where
        """
        data = pd.DataFrame({
        'Letter': ['A', 'B', 'C'],
        'Number': [1, 2, 3],
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  Letter: Number
                output: Pairs
                where: Number = 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['Pairs'] == {'B': 2} and df.iloc[0]['Pairs'] == ''

    def test_key_value_pairs_2(self):
        """
        Using a Wildcard
        """
        data = pd.DataFrame({
        'key 1': ['A', 'B', 'C'],
        'key 2': ['One', 'Two', 'three'],
        'value 1': ['a', 'b', 'c'],
        'value 2': ['First', 'Second', 'Third']
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  key*: value*
                output: Object
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[2]['Object'] == {'C': 'c', 'three': 'Third'}

    def test_wildcard_where(self):
        """
        Using a Wildcard and where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
                - merge.key_value_pairs:
                    input:
                        key*: value*
                    output: Object
                    where: '"key 1" = "C"'
            """,
            dataframe=pd.DataFrame({
                'key 1': ['A', 'B', 'C'],
                'key 2': ['One', 'Two', 'three'],
                'value 1': ['a', 'b', 'c'],
                'value 2': ['First', 'Second', 'Third']
            })
        )
        assert (
            df['Object'][0] == '' and 
            df['Object'][2] == {'C': 'c', 'three': 'Third'}
        )

    def test_key_value_pairs_3(self):
        """
        True or False in row Values
        """
        data = pd.DataFrame({
        'key 1': ['A'],
        'key 2': [True],
        'value 1': ['a'],
        'value 2': [False]
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  key*: value*
                output: Object
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Object'] == {'A': 'a', True: False}

    def test_key_value_pairs_empty_dataframe(self):
        """
        Test merge.key_value_pairs with an empty dataframe
        """
        data = pd.DataFrame({
            'key1': [],
            'key2': [],
            'value1': [],
            'value2': []
        })
        recipe = """
        wrangles:
            - merge.key_value_pairs:
                input:
                  key*: value*
                output: Object
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['key1', 'key2', 'value1', 'value2', 'Object']
    
    def test_key_value_pairs_skip_empty_true(self):  
        """  
        Test merge.key_value_pairs with skip_empty=True - should skip empty keys and values  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '', 'C'],  # Empty key in second row  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # Empty dict because key is empty  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_false(self):  
        """  
        Test merge.key_value_pairs with skip_empty=False - should include empty keys/values  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '', 'C'],  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: false  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {'': 2}  # Empty key included  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_values(self):  
        """  
        Test that skip_empty also skips empty values, not just keys  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', 'B', 'C'],  
            'Number': [1, '', 3],  # Empty value in second row  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # Empty dict because value is empty  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_whitespace(self):  
        """  
        Test that skip_empty treats whitespace-only strings as empty  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '  ', 'C'],  # Whitespace key in second row  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # Whitespace key skipped  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_none_values(self):  
        """  
        Test that skip_empty handles None values correctly  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', 'B', 'C'],  
            'Number': [1, None, 3],  # None value in second row  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {'A': 1}  
        assert df.iloc[1]['Pairs'] == {}  # None value skipped  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_multiple_pairs(self):  
        """  
        Test skip_empty with multiple key-value pairs using wildcards  
        """  
        data = pd.DataFrame({  
            'key 1': ['A', '', 'C'],  
            'key 2': ['One', 'Two', ''],  
            'value 1': ['a', 'b', 'c'],  
            'value 2': ['First', '', 'Third']  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    key*: value*  
                output: Object  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Object'] == {'A': 'a', 'One': 'First'}  
        assert df.iloc[1]['Object'] == {}  # Empty key and value skipped  
        assert df.iloc[2]['Object'] == {'C': 'c'}  # Empty key and value skipped  
    
    def test_key_value_pairs_skip_empty_all_empty(self):  
        """  
        Test skip_empty when all keys/values in a row are empty  
        """  
        data = pd.DataFrame({  
            'Letter': ['', '', ''],  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == {}  
        assert df.iloc[1]['Pairs'] == {}  
        assert df.iloc[2]['Pairs'] == {}  
    
    def test_key_value_pairs_skip_empty_with_where(self):  
        """  
        Test skip_empty works correctly with where clause  
        """  
        data = pd.DataFrame({  
            'Letter': ['A', '', 'C'],  
            'Number': [1, 2, 3],  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    Letter: Number  
                output: Pairs  
                skip_empty: true  
                where: Number > 1  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Pairs'] == ''  # Not processed due to where clause  
        assert df.iloc[1]['Pairs'] == {}  # Processed but empty key skipped  
        assert df.iloc[2]['Pairs'] == {'C': 3}  
    
    def test_key_value_pairs_skip_empty_boolean_values(self):  
        """  
        Test that skip_empty correctly handles boolean values  
        """  
        data = pd.DataFrame({  
            'key 1': ['A'],  
            'key 2': [True],  
            'value 1': ['a'],  
            'value 2': [False]  
        })  
        recipe = """  
        wrangles:  
            - merge.key_value_pairs:  
                input:  
                    key*: value*  
                output: Object  
                skip_empty: false  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[0]['Object'] == {'A': 'a', True: False}

class TestMergeDictionaries:
    """
    Test merge.dictionaries
    """
    def test_merge_dicts_1(self):
        data = pd.DataFrame({
            'd1': [{'Hello': 'Fey'}],
            'd2': [{'Hello2': 'Lucy'}],
        })
        recipe = """
        wrangles:
        - merge.dictionaries:
            input:
                - d1
                - d2
            output: out
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}

    def test_merge_dicts_where(self):
        """
        Tests merge.dictionaries using where
        """
        data = pd.DataFrame({
            'd1': [{'Hello': 'Fey'}, {'Hello': 'Moto'}, {'Hello': 'World'}],
            'd2': [{'Hola': 'Lucy'}, {'Hola': 'Hello'}, {'Hola': 'Nice to meet you'}],
            'numbers': [2, 55, 71]
        })
        recipe = """
        wrangles:
        - merge.dictionaries:
            input:
                - d1
                - d2
            output: out
            where: numbers > 2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[1]['out'] == {'Hello': 'Moto', 'Hola': 'Hello'} and df.iloc[0]['out'] == ''

    def test_merge_dicts_empty_dataframe(self):
        """
        Test merge.dictionaries with an empty dataframe
        """
        data = pd.DataFrame({
            'd1': [],
            'd2': [],
            'd3': []
        })
        recipe = """
        wrangles:
        - merge.dictionaries:
            input:
                - d1
                - d2
                - d3
            output: out
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.empty and df.columns.to_list() == ['d1', 'd2', 'd3', 'out']
        
    def test_merge_dicts_skip_empty_true(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should skip empty dictionary values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}],  
            'd2': [{'Hello2': 'Lucy', 'Blank': ''}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should only include non-empty values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_false(self):  
        """  
        Test merge.dictionaries with skip_empty=False - should include empty values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}],  
            'd2': [{'Hello2': 'Lucy', 'Blank': ''}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: false  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should include empty values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Empty': '', 'Hello2': 'Lucy', 'Blank': ''}  
    
    def test_merge_dicts_skip_empty_default(self):  
        """  
        Test merge.dictionaries with default skip_empty (should be False for backward compatibility)  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}],  
            'd2': [{'Hello2': 'Lucy'}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Default should include empty values for backward compatibility  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Empty': '', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_whitespace(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should skip whitespace-only values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Spaces': '   '}],  
            'd2': [{'Hello2': 'Lucy', 'Tab': '\t'}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should skip whitespace-only values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_none_values(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should skip None values  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'NoneVal': None}],  
            'd2': [{'Hello2': 'Lucy', 'AlsoNone': None}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should skip None values  
        assert df.iloc[0]['out'] == {'Hello': 'Fey', 'Hello2': 'Lucy'}  
    
    def test_merge_dicts_skip_empty_mixed_types(self):  
        """  
        Test merge.dictionaries with skip_empty=True - should handle mixed types correctly  
        """  
        data = pd.DataFrame({  
            'd1': [{'String': 'Value', 'Number': 0, 'Empty': ''}],  
            'd2': [{'Bool': False, 'None': None, 'Valid': 'Data'}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should skip empty string and None, but keep 0 and False (they're valid values)  
        assert df.iloc[0]['out'] == {'String': 'Value', 'Number': 0, 'Bool': False, 'Valid': 'Data'}  
    
    def test_merge_dicts_skip_empty_all_empty(self):  
        """  
        Test merge.dictionaries with skip_empty=True when all values are empty  
        """  
        data = pd.DataFrame({  
            'd1': [{'Empty1': '', 'Empty2': ''}],  
            'd2': [{'Empty3': None, 'Empty4': '   '}],  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        # Should result in empty dictionary  
        assert df.iloc[0]['out'] == {}  
    
    def test_merge_dicts_skip_empty_where(self):  
        """  
        Test merge.dictionaries with skip_empty=True and where clause  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey', 'Empty': ''}, {'Hello': 'Moto', 'Empty': ''}],  
            'd2': [{'Hola': 'Lucy', 'Blank': ''}, {'Hola': 'Hello', 'Blank': ''}],  
            'numbers': [2, 55]  
        })  
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            output: out  
            skip_empty: true  
            where: numbers > 2  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        assert df.iloc[1]['out'] == {'Hello': 'Moto', 'Hola': 'Hello'} and df.iloc[0]['out'] == ''

    def test_merge_dicts_with_empty_dict(self):  
        """  
        Test merge.dictionaries with one empty dictionary  
        """  
        data = pd.DataFrame({  
            'd1': [{'Hello': 'Fey'}, {}, {'Hello': 'World'}],  
            'd2': [{'Hola': 'Lucy'}, {'Hola': 'Moto'}, {'Hola': 'Nice'}],  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
            skip_empty: true
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        expected = [  
            {'Hello': 'Fey', 'Hola': 'Lucy'},  
            {'Hola': 'Moto'},  
            {'Hello': 'World', 'Hola': 'Nice'}  
        ]  
        assert df['out'].tolist() == expected
    
    def test_merge_dicts_few_empty_dict(self):  
        """  
        Test merge.dictionaries with a few empty dictionaries  
        """  
        data = pd.DataFrame({  
            'd1': [{}, {'Hello': 'Fey'}, {}],  
            'd2': [{'Hola': 'Lucy'}, {}, {'Hola': 'Moto'}],  
            'd3': [{'key': 'value'}, {'key': 'test'}, {}]  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
                - d3 
            skip_empty: true 
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        expected = [  
            {'Hola': 'Lucy', 'key': 'value'},  
            {'Hello': 'Fey', 'key': 'test'},  
            {'Hola': 'Moto'}  
        ]  
        assert df['out'].tolist() == expected

    def test_merge_dicts_all_empty_skip_empty_true(self):  
        """  
        Test merge.dictionaries where all dictionaries are empty  
        """  
        data = pd.DataFrame({  
            'd1': [{}, {}, {}],  
            'd2': [{}, {}, {}],  
            'd3': [{}, {}, {}]  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
                - d3  
            skip_empty: true 
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        # All rows should result in empty dictionaries  
        expected = [{}, {}, {}]  
        assert df['out'].tolist() == expected

    def test_merge_dicts_all_empty_skip_empty_false(self):  
        """  
        Test merge.dictionaries where all dictionaries are empty with skip_empty=False 
        """  
        data = pd.DataFrame({  
            'd1': [{}, {}, {}],  
            'd2': [{}, {}, {}],  
            'd3': [{}, {}, {}]  
        })  
        
        recipe = """  
        wrangles:  
        - merge.dictionaries:  
            input:  
                - d1  
                - d2  
                - d3  
            skip_empty: false 
            output: out  
        """  
        df = wrangles.recipe.run(recipe, dataframe=data)  
        
        expected = [{}, {}, {}]  
        assert df['out'].tolist() == expected
