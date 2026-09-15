"""Compatibility checks for both recipe command-line entry points."""
from importlib.metadata import version
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
