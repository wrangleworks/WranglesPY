"""Offline catalog backfill checks against the supplied database mapping snapshot.

The fixture pins mapping fields from Wrangles-Docs registry/catalog/api-core.json
and includes the supplied lifecycle defaults. catalog_key is never used as a
fallback execution key; the lookup IDs are explicit user-provided corrections.
"""

from collections import defaultdict
import ast
import inspect
import json
from pathlib import Path
import re
import runpy
import shutil
import textwrap

import pytest
import pandas as pd
import requests
import yaml

import wrangles
from wrangles.recipe_wrangles import ai


ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / 'tests/fixtures/catalog/api-core.json').read_text())['catalog']

# Explicitly approved old/current identities, not catalog_key fallbacks.
ALIASES = {
    'standardize.replace': 'replace',
    'structure.split_dictionary': 'split.dictionary',
    'structure.split_list': 'split.list',
    'structure.split_text': 'split.text',
    'structure.tokenize': 'split.tokenize',
}
LOOKUP_IDS = {'lookup': '81', 'lookup.key': '101', 'lookup.semantic': '102'}
METADATA = {'catalog_id', 'status'}
FORBIDDEN = {'history', 'wranglesPY_key', 'catalog_key', 'catalog_kind'}
UNSTRUCTURED = {'maths', 'format.price_breaks'}


def public_callables(obj, path=''):
    """Include imported aliases and children of callable namespaces.

    main/pandas are implementation modules excluded by schema discovery;
    pandas.* also has its own generic dataframe dispatch in recipe.run.
    """
    if callable(obj):
        yield path, obj
    for name in dir(obj):
        if name.startswith('_') or name in ('main', 'pandas'):
            continue
        child = getattr(obj, name)
        if child is not obj:
            public_name = {v: k for k, v in wrangles.config.reserved_word_replacements.items()}.get(name, name)
            yield from public_callables(child, '.'.join(filter(None, (path, public_name))))


OPERATIONS = dict(public_callables(wrangles.recipe._recipe_wrangles))


def raw_schema(function):
    value = yaml.safe_load(function.__doc__)
    return value if isinstance(value, dict) else None


def expected_ids():
    by_key = defaultdict(list)
    for row in CATALOG:
        if row['catalog_kind'] == 'wrangle':
            by_key[row['wranglesPY_key']].append(row['catalog_id'])
    matched = {
        name: by_key[ALIASES.get(name, name)][0]
        for name in OPERATIONS
        if name not in UNSTRUCTURED and len(by_key[ALIASES.get(name, name)]) == 1
    }
    return {**matched, **LOOKUP_IDS}


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    work = tmp_path_factory.mktemp('catalog-schema')
    shutil.copyfile(ROOT / 'schema/recipe_base_schema.json', work / 'recipe_base_schema.json')
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(work)

        def no_network(*args, **kwargs):
            pytest.fail('Schema generation must not contact a live service')

        patch.setattr(requests.sessions.Session, 'request', no_network)
        runpy.run_path(str(ROOT / 'schema/generate_recipe_schema.py'))
    return json.loads((work / 'schema.json').read_text())


def test_namespace_and_unresolved_mappings(generated):
    schemas = generated['$defs']['wrangles']['items']['properties']
    assert set(OPERATIONS) - set(schemas) == UNSTRUCTURED
    assert set(schemas) == set(expected_ids())
    # lookup's three rows are ambiguous; dotted catalog keys are not runtime keys.
    assert [row['catalog_id'] for row in CATALOG
            if row['catalog_kind'] == 'wrangle' and row['wranglesPY_key'] == 'lookup'] == ['81', '101', '102']
    assert 'map' not in OPERATIONS
    assert expected_ids()['create.index'] == '17'
    for name, catalog_id in LOOKUP_IDS.items():
        row, = [row for row in CATALOG if row['catalog_id'] == catalog_id]
        assert row['catalog_kind'] == 'wrangle'
        assert row['catalog_key'] == name
        assert schemas[name]['catalog_id'] == catalog_id


@pytest.mark.parametrize('name,catalog_id', sorted(expected_ids().items()))
def test_catalog_ids_survive_generation_as_quoted_strings(generated, name, catalog_id):
    function = OPERATIONS[name]
    raw = raw_schema(function)
    emitted = generated['$defs']['wrangles']['items']['properties'][name]
    assert raw['catalog_id'] == emitted['catalog_id'] == catalog_id
    status = 'legacy' if name in ALIASES.values() else 'active'
    assert raw['status'] == emitted['status'] == status
    assert not FORBIDDEN.intersection(raw)
    assert not FORBIDDEN.intersection(emitted)
    assert isinstance(emitted['catalog_id'], str)
    assert re.fullmatch(r'[0-9]+', emitted['catalog_id'])
    yaml_nodes = dict((key.value, value) for key, value in yaml.compose(function.__doc__).value)
    assert yaml_nodes['catalog_id'].style in ('"', "'")
    assert not (METADATA | FORBIDDEN).intersection(inspect.signature(function).parameters)
    if not name.startswith('ai.'):
        # Static extraction must see the same literal metadata as runtime discovery.
        definition = ast.parse(textwrap.dedent(inspect.getsource(function))).body[0]
        assert yaml.safe_load(ast.get_docstring(definition)) == raw


def test_catalog_ids_are_never_nested_parameters(generated):
    def check_nested(node):
        if isinstance(node, dict):
            assert not (METADATA | FORBIDDEN).intersection(node)
            assert not (METADATA | FORBIDDEN).intersection(node.get('required', []))
            for child in node.values():
                check_nested(child)
        elif isinstance(node, list):
            for child in node:
                check_nested(child)

    for schema in generated['$defs']['wrangles']['items']['properties'].values():
        check_nested({key: value for key, value in schema.items() if key not in METADATA})


def test_duplicate_ids_only_identify_approved_compatibility_pairs(generated):
    schemas = generated['$defs']['wrangles']['items']['properties']
    groups = defaultdict(set)
    for name, schema in schemas.items():
        if 'catalog_id' in schema:
            groups[schema['catalog_id']].add(name)
    duplicates = {frozenset(names) for names in groups.values() if len(names) > 1}
    assert duplicates == {frozenset((alias, canonical)) for alias, canonical in ALIASES.items()}
    for current, old in ALIASES.items():
        assert OPERATIONS[current] is not OPERATIONS[old]
        assert OPERATIONS[current].__doc__ != OPERATIONS[old].__doc__
        assert schemas[current]['status'] == 'active'
        assert schemas[old]['status'] == 'legacy'
        assert {k: v for k, v in schemas[current].items() if k != 'status'} == {
            k: v for k, v in schemas[old].items() if k != 'status'
        }


@pytest.mark.parametrize('kind,catalog_id', [(None, '149'), ('choose', '150'), ('score', '151'), ('true_false', '152')])
def test_ai_schema_builder_retains_catalog_identity(kind, catalog_id):
    schema = ai._schema(kind)
    assert schema['catalog_id'] == catalog_id
    assert schema['status'] == 'active'
    assert not FORBIDDEN.intersection(schema)


def test_snapshot_does_not_store_derived_lifecycle_fields():
    assert all('history' not in row for row in CATALOG)


def test_connector_coverage_remains_separate(generated):
    connectors = set()
    for operation in ('read', 'write', 'run'):
        schemas = generated['$defs'][operation]['items']['properties']
        connectors.update(schemas)
        assert all(not METADATA.intersection(schema) for schema in schemas.values())
    snapshot_keys = {row['wranglesPY_key'] for row in CATALOG if row['catalog_kind'] == 'connector'}
    assert len(snapshot_keys) == 46
    assert connectors - snapshot_keys == {'excel.table'}
    assert snapshot_keys - connectors == set()


def test_generated_contract_is_identical_without_metadata(generated, tmp_path, monkeypatch):
    """Metadata must not affect parameter schemas, defaults or validation rules."""
    shutil.copyfile(ROOT / 'schema/recipe_base_schema.json', tmp_path / 'recipe_base_schema.json')
    monkeypatch.chdir(tmp_path)
    for function in set(OPERATIONS.values()):
        schema = raw_schema(function)
        if schema is not None:
            monkeypatch.setattr(function, '__doc__', yaml.safe_dump(
                {key: value for key, value in schema.items() if key not in METADATA}
            ))
    runpy.run_path(str(ROOT / 'schema/generate_recipe_schema.py'))
    baseline = json.loads((tmp_path / 'schema.json').read_text())
    without_metadata = json.loads(json.dumps(generated))
    for schema in without_metadata['$defs']['wrangles']['items']['properties'].values():
        for key in METADATA:
            schema.pop(key)
    assert without_metadata == baseline


@pytest.mark.parametrize('current,old,values,params,column,expected', [
    ('standardize.replace', 'replace', ['red'], {'find': 'red', 'replace': 'blue'}, 'Value', 'blue'),
    ('structure.split_dictionary', 'split.dictionary', [{'a': 1}], {}, 'a', 1),
    ('structure.split_list', 'split.list', [[1, 2]], {'output': ['First', 'Second']}, 'First', 1),
    ('structure.split_text', 'split.text', ['red,blue'], {'output': 'Result'}, 'Result', ['red', 'blue']),
    ('structure.tokenize', 'split.tokenize', ['red blue'], {'output': 'Result'}, 'Result', ['red', 'blue']),
])
def test_lifecycle_metadata_preserves_alias_recipe_execution(current, old, values, params, column, expected):
    source = pd.DataFrame({'Value': values})
    results = [wrangles.recipe.run(
        {'wrangles': [{name: {'input': 'Value', **params}}]}, dataframe=source.copy(deep=True)
    ) for name in (current, old)]
    pd.testing.assert_frame_equal(*results)
    assert results[0][column].iloc[0] == expected
    direct_results = [OPERATIONS[name](source.copy(deep=True), input='Value', **params)
                      for name in (current, old)]
    pd.testing.assert_frame_equal(*direct_results)
    pd.testing.assert_frame_equal(direct_results[0], results[0])


@pytest.mark.parametrize('current,old', ALIASES.items())
def test_compatibility_signatures_and_original_defaults(current, old):
    required = inspect.Parameter.empty
    expected = {
        'replace': [('df', required), ('input', required), ('find', required),
                    ('replace', required), ('output', None)],
        'split.dictionary': [('df', required), ('input', required), ('output', None),
                             ('default', None), ('output_format', 'columns')],
        'split.list': [('df', required), ('input', required), ('output', required)],
        'split.text': [('df', required), ('input', required), ('output', None),
                       ('char', ','), ('pad', None), ('element', None),
                       ('inclusive', False), ('skip_empty', False)],
        'split.tokenize': [('df', required), ('input', required), ('output', None),
                           ('method', 'space'), ('functions', None)],
    }
    old_signature = inspect.signature(OPERATIONS[old])
    assert inspect.signature(OPERATIONS[current]) == old_signature
    assert [(p.name, p.default) for p in old_signature.parameters.values()] == expected[old]
    assert all(p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
               for p in old_signature.parameters.values())
