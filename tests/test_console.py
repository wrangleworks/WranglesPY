"""Compatibility checks for both recipe command-line entry points."""
from importlib.metadata import version
import copy
import json
import subprocess
import sys
from unittest.mock import Mock

import pytest
from wrangles import console


@pytest.fixture(params=['legacy', 'unified'])
def invoke(request):
    if request.param == 'legacy':
        return console.recipe
    return lambda args: console.main(['recipe', 'run', *args])


@pytest.mark.parametrize('source', ['folder with spaces/recipe.yml', 'https://example.com/recipe.yml', 'abcdef12-3456-7890', 'read: []'])
def test_recipe_sources_and_defaults(invoke, monkeypatch, source):
    run = Mock(return_value=object())
    monkeypatch.setattr(console._recipe, 'run', run)
    assert invoke([source]) is None
    run.assert_called_once_with(source, functions=None, variables={}, timeout=None)


@pytest.mark.parametrize('short', [False, True])
@pytest.mark.parametrize('dictionary', [None, 'chosen'])
def test_recipe_options_and_executable_variables(invoke, monkeypatch, tmp_path, short, dictionary):
    variables = tmp_path / 'custom variables.py'
    variables.write_text("variables = {'count': 2 + 3}\nchosen = {'count': 4 * 3}\n", encoding='utf-8')
    run = Mock()
    monkeypatch.setattr(console._recipe, 'run', run)
    flags = ['-f', '-v', '-t'] if short else ['--functions', '--variables', '--timeout']
    args = ['input.yml', flags[0], 'custom functions.py', flags[1], str(variables), flags[2], '60.5']
    if dictionary:
        args += ['--varDict', dictionary]
    invoke(args)
    run.assert_called_once_with('input.yml', functions='custom functions.py',
                               variables={'count': 12 if dictionary else 5}, timeout=60.5)


@pytest.mark.parametrize('timeout', ['abc', '-1', 'nan', 'inf', '-inf'])
def test_invalid_timeout_fails_before_execution(invoke, monkeypatch, capsys, timeout):
    run = Mock()
    monkeypatch.setattr(console._recipe, 'run', run)
    with pytest.raises(SystemExit) as error:
        invoke(['input.yml', '--timeout=' + timeout])
    assert error.value.code == 2
    run.assert_not_called()
    result = capsys.readouterr()
    assert result.out == ''
    assert 'timeout' in result.err


def test_zero_timeout_is_forwarded(invoke, monkeypatch):
    run = Mock()
    monkeypatch.setattr(console._recipe, 'run', run)
    invoke(['input.yml', '-t', '0'])
    run.assert_called_once_with('input.yml', functions=None, variables={}, timeout=0.0)


@pytest.mark.parametrize('args, expected', [(['--help'], 'recipe'), (['--version'], 'wrangles ' + version('wrangles')), (['recipe', '--help'], 'run'), (['recipe', 'run', '--help'], '--varDict')])
def test_help_and_version_offline_subprocess(args, expected):
    # Block connections before importing the package, not just after CLI import.
    script = "import socket\ndef blocked(*a, **k): raise AssertionError('Network forbidden')\nsocket.socket.connect = blocked\nsocket.create_connection = blocked\nfrom wrangles import config, auth\nconfig.api_user = config.api_password = None\nauth.get_access_token = blocked\nfrom wrangles.console import main\nmain()\n"
    result = subprocess.run([sys.executable, '-c', script, *args], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout
    assert result.stderr == ''


@pytest.mark.parametrize('prefix', [[ '-m', 'wrangles', 'recipe', 'run'], ['-c', 'from wrangles.console import recipe; recipe()']])
def test_real_recipe_writes_output_subprocess(tmp_path, prefix):
    output = tmp_path / 'result with spaces.csv'
    recipe = tmp_path / 'recipe with spaces.yml'
    recipe.write_text('read:\n  - test:\n      rows: 2\n      values:\n        item: synthetic\nwrite:\n  - file:\n      name: ' + output.as_posix() + '\n', encoding='utf-8')
    result = subprocess.run([sys.executable, *prefix, str(recipe), '--timeout', '30'], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding='utf-8-sig').splitlines() == ['item', 'synthetic', 'synthetic']

# Model validation uses the same authoring contract as the recipe connector.


@pytest.fixture
def definition_file(tmp_path):
    def write(content):
        path = tmp_path / 'definition with spaces.json'
        path.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
        return path
    return write


@pytest.mark.parametrize('columns,row', [
    (['Find'], ['Voltage']),
    (['Find', 'Description', 'Type', 'Default', 'Examples', 'Enum', 'Notes'],
     ['Voltage', 'Напруга', 'number', 0, [0, 12], [0, 12], None]),
    (['Notes', 'Find', 'Nullable', 'Default', 'Type'], ['', 'Enabled', False, False, 'boolean']),
    (list(console._saved.KNOWN_HEADINGS),
     ['Voltage', '', 'object', None, None, None, '', {'value': {'type': 'number'}}, None,
      ['value'], False, False, '12 volts', {'value': 12}]),
    (['Find', 'Description', 'Type', 'Default', 'Examples', 'Enum', 'Notes', 'Properties', 'Items', 'Required', 'Example - Input', 'Example - Output'],
     ['Voltage', '', 'number', 0, None, None, '', None, None, None, '12 volts', 12]),
    (['Find', 'Extra'], ['Voltage', {'native': [False, 0, None, 'é']}]),
])
def test_validate_shared_contract_preserves_content(definition_file, monkeypatch, capsys, columns, row):
    content = {'Columns': columns, 'Data': [row], 'Settings': {'GeneralInstructions': 'Read carefully'}}
    original = copy.deepcopy(content)
    path = definition_file(content)
    original_bytes = path.read_bytes()
    prepare = Mock(wraps=console._saved.prepare_content)
    monkeypatch.setattr(console._saved, 'prepare_content', prepare)
    console.main(['model', 'validate', str(path), '--json'])
    result = capsys.readouterr()
    envelope = json.loads(result.out)
    assert envelope['schema_version'] == 1
    assert envelope['command'] == 'model.validate'
    assert envelope['outcome'] == 'valid'
    assert envelope['error'] is None
    assert envelope['readiness'] == envelope['verification'] == 'not_checked'
    assert envelope['model_id'] is None
    assert envelope['validation']['rows'] == 1
    assert envelope['validation']['columns'] == len(columns)
    prepare.assert_called_once_with(original)
    assert prepare.call_args.args[0] == original
    assert path.read_bytes() == original_bytes
    assert 'does not guarantee' in result.err


def test_validate_runtime_incompatibility_is_only_warning(definition_file, capsys):
    path = definition_file({'Columns': ['Find', 'Unknown'], 'Data': [['Voltage', 'populated']]})
    console.main(['model', 'validate', str(path), '--json'])
    result = capsys.readouterr()
    envelope = json.loads(result.out)
    assert envelope['outcome'] == 'valid'
    assert envelope['validation']['runtime'] == 'incompatible'
    assert envelope['validation']['warnings'][0]['code'] == 'runtime_incompatible'
    assert 'runtime compiler rejected' in result.err


def test_validate_authoring_error_has_location_without_values(definition_file, capsys):
    path = definition_file({'Columns': ['Find', 'Type'], 'Data': [['Voltage', 'SECRET-INVALID-TYPE']]})
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'validate', str(path), '--json'])
    assert error.value.code == 2
    result = capsys.readouterr()
    envelope = json.loads(result.out)
    assert envelope['outcome'] == 'invalid'
    assert envelope['error'] == {'code': 'authoring_validation',
        'message': 'Type must be string, number, integer, boolean, array, or object.',
        'path': '$.Data[0][1]', 'row': 2, 'column': 2, 'heading': 'Type'}
    assert 'SECRET' not in result.out + result.err


@pytest.mark.parametrize('document', ['{"Columns":', '{"Columns":[],"Columns":[]}', '{"Columns":["Find"],"Data":[[NaN]]}', 'not: json'])
def test_validate_invalid_json_is_structured(tmp_path, capsys, document):
    path = tmp_path / 'invalid.json'
    path.write_text(document, encoding='utf-8')
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'validate', str(path), '--json'])
    assert error.value.code == 2
    result = json.loads(capsys.readouterr().out)
    assert result['error']['code'] == 'invalid_json'
    if document == '{"Columns":':
        assert result['error']['line'] == 1
        assert result['error']['column'] == 12


@pytest.mark.parametrize('kind', ['missing', 'directory', 'encoding'])
def test_validate_unreadable_file_is_input_error(tmp_path, capsys, kind):
    path = tmp_path / 'input.json'
    if kind == 'directory':
        path.mkdir()
    elif kind == 'encoding':
        path.write_bytes(b'\xff\xfe')
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'validate', str(path), '--json'])
    assert error.value.code == 2
    result = json.loads(capsys.readouterr().out)
    assert result['error']['code'] == 'input_file'


@pytest.mark.parametrize('args', [['model', 'validate', '--json'], ['model', 'validate', 'file.json', '--wrong', '--json']])
def test_model_usage_errors_have_one_json_result(args, capsys):
    with pytest.raises(SystemExit) as error:
        console.main(args)
    assert error.value.code == 2
    output = capsys.readouterr()
    assert len(output.out.splitlines()) == 1
    assert json.loads(output.out)['error']['code'] == 'usage'
    assert '--help' in output.err


@pytest.mark.parametrize('exception,code,name', [(RuntimeError('SECRET'), 1, 'unexpected'), (KeyboardInterrupt(), 130, 'interrupted')])
def test_validate_failure_exit_codes(definition_file, monkeypatch, capsys, exception, code, name):
    path = definition_file({'Columns': ['Find'], 'Data': [['Voltage']]})
    monkeypatch.setattr(console._saved, 'prepare_content', Mock(side_effect=exception))
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'validate', str(path), '--json'])
    assert error.value.code == code
    output = capsys.readouterr()
    assert json.loads(output.out)['error']['code'] == name
    assert 'SECRET' not in output.out + output.err


def test_validate_human_output(definition_file, capsys):
    console.main(['model', 'validate', str(definition_file({'Columns': ['Find'], 'Data': [['Voltage']]}))])
    output = capsys.readouterr()
    assert output.out == 'Valid saved-model definition.\n'
    assert 'Authoring validation' in output.err


@pytest.mark.parametrize('invalid', [False, True])
def test_validate_offline_subprocess(definition_file, invalid):
    path = definition_file({'Columns': ['Find'], 'Data': [['Напруга']]})
    if invalid:
        path.write_text('{', encoding='utf-8')
    script = "import socket\ndef blocked(*a, **k): raise AssertionError('Network forbidden')\nsocket.socket.connect = blocked\nsocket.create_connection = blocked\nfrom wrangles import config, auth\nconfig.api_user = config.api_password = None\nauth.get_access_token = blocked\nfrom wrangles.console import main\nmain()\n"
    result = subprocess.run([sys.executable, '-c', script, 'model', 'validate', str(path), '--json'], capture_output=True, text=True, timeout=60)
    assert result.returncode == (2 if invalid else 0), result.stderr
    envelope = json.loads(result.stdout)
    assert envelope['outcome'] == ('invalid' if invalid else 'valid')
    assert len(result.stdout.splitlines()) == 1
    if not invalid:
        assert envelope['validation']['runtime'] == 'compatible'

@pytest.mark.parametrize('content,path', [
    ([], '$'),
    ({'Columns': ['Find']}, '$'),
    ({'Columns': ['Type'], 'Data': []}, '$.Columns'),
    ({'Columns': ['Find'], 'Data': [['A', 'extra']]}, '$.Data[0]'),
    ({'Columns': ['Find'], 'Data': [['A']], 'Settings': False}, '$.Settings'),
])
def test_validate_invalid_shape_and_settings(definition_file, capsys, content, path):
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'validate', str(definition_file(content)), '--json'])
    assert error.value.code == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope['error']['code'] == 'authoring_validation'
    assert envelope['error']['path'] == path


def test_validate_runtime_diagnostics_do_not_leak_or_change_logging(definition_file, monkeypatch, capsys):
    import logging
    logger = logging.getLogger(console._definition.__name__)
    before = list(logger.filters)
    def compile_with_sensitive_diagnostic(*args, **kwargs):
        logger.warning('SECRET-IN-SCHEMA')
        raise ValueError('Invalid extract.ai definition at model_id.data[1]: SECRET-IN-SCHEMA')
    monkeypatch.setattr(console._definition, 'compile_definition', compile_with_sensitive_diagnostic)
    console.main(['model', 'validate', str(definition_file({'Columns': ['Find'], 'Data': [['A']]})), '--json'])
    output = capsys.readouterr()
    assert 'SECRET' not in output.out + output.err
    envelope = json.loads(output.out)
    assert envelope['validation']['warnings'][0]['path'] == '$.Data[0]'
    assert logger.filters == before
