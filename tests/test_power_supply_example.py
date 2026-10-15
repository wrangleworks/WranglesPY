"""Offline checks for the published Power Supply example and live evidence flow."""
import json
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest
import requests
import wrangles
from wrangles import ai_definition, ai_saved_model, auth, console
from tests import test_cli_live

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'power-supply'


def test_power_supply_definition_has_compilable_nested_schema_and_paired_example(monkeypatch):
    network = Mock(side_effect=AssertionError('Unexpected service call'))
    monkeypatch.setattr(requests.Session, 'request', network)
    content = json.loads((EXAMPLE / 'definition.json').read_text(encoding='utf-8'))
    prepared = ai_saved_model.prepare_content(content)
    compiled = ai_definition.compile_definition({}, model='validation-only', saved_model_content=prepared)
    assert len(compiled.output) == 23
    assert set(compiled.output['OutputVoltage']['properties']) == {'value', 'unit', 'adjustable'}
    assert set(compiled.output['PlugType']['enum']) - {None} == {'EU', 'UK', 'US', 'IEC-C14', 'Bare-wire', 'USB-C'}
    assert compiled.field_examples[0].output == {'value': 12, 'unit': 'VDC', 'adjustable': False}
    assert compiled.messages == [content['Settings']['GeneralInstructions']]
    network.assert_not_called()


def test_power_supply_recipe_reads_fixture_and_writes_nested_results(monkeypatch, tmp_path):
    network = Mock(side_effect=AssertionError('Unexpected service call'))
    monkeypatch.setattr(requests.Session, 'request', network)
    monkeypatch.setattr(auth, 'get_applied_permission_group', lambda: None)
    output = tmp_path / 'power supply results.json'
    monkeypatch.setenv('POWER_SUPPLY_INPUT', str(EXAMPLE / 'input.json'))
    monkeypatch.setenv('POWER_SUPPLY_OUTPUT', str(output))
    monkeypatch.setenv('POWER_SUPPLY_MODEL_ID', '12345678-abcd-1234')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-key')
    inputs = json.loads((EXAMPLE / 'input.json').read_text(encoding='utf-8'))
    values = [{'OutputVoltage': {'value': value, 'unit': 'VDC', 'adjustable': index == 1}, 'PlugType': plug}
              for index, (value, plug) in enumerate([(12, 'EU'), (24, 'Bare-wire'), (5, 'Bare-wire')])]
    extract = Mock(return_value=values)
    monkeypatch.setattr(wrangles.extract, 'ai', extract)
    console.main(['recipe', 'run', str(EXAMPLE / 'recipe.wrgl.yml')])
    result = json.loads(output.read_text(encoding='utf-8'))
    assert [row['record_id'] for row in result] == ['PS-001', 'PS-002', 'PS-003']
    assert [row['attributes'] for row in result] == values
    assert extract.call_args.args[0] == [{'description': row['description']} for row in inputs]
    assert extract.call_args.kwargs['model_id'] == '12345678-abcd-1234'
    assert extract.call_args.kwargs['api_key'] == 'synthetic-test-key'
    assert extract.call_args.kwargs['cache'] is False
    extract.assert_called_once()
    network.assert_not_called()


def test_live_harness_keeps_id_on_creation_verification_failure(tmp_path):
    calls = []
    def runner(args, **kwargs):
        calls.append(args)
        if args[0] == 'git':
            return subprocess.CompletedProcess(args, 0, 'synthetic-commit\n', '')
        envelope = {'outcome': 'error', 'model_id': '12345678-abcd-1234', 'target': 'https://example.test',
                    'error': {'code': 'deadline'}}
        return subprocess.CompletedProcess(args, 5, json.dumps(envelope), 'SECRET-RAW-DIAGNOSTIC')
    with pytest.raises(AssertionError, match='create failed'):
        test_cli_live._run_roundtrip(tmp_path, runner=runner)
    evidence = json.loads(next(tmp_path.glob('*/evidence.json')).read_text(encoding='utf-8'))
    assert evidence['model_id'] == '12345678-abcd-1234'
    assert evidence['target'] == 'https://example.test'
    assert evidence['steps'][0]['exit_code'] == 5
    assert sum(args[0] != 'git' for args in calls) == 1
    assert 'SECRET' not in json.dumps(evidence)


def test_live_harness_roundtrip_updates_same_id_and_preserves_settings(tmp_path):
    calls = []
    definition = json.loads((EXAMPLE / 'definition.json').read_text(encoding='utf-8'))
    def runner(args, **kwargs):
        if args[0] == 'git':
            return subprocess.CompletedProcess(args, 0, 'synthetic-commit\n', '')
        action = args[4]
        calls.append(args)
        if action == 'export':
            Path(args[args.index('--output') + 1]).write_text(json.dumps(definition), encoding='utf-8')
        if action == 'update':
            content = json.loads(Path(args[args.index('--file') + 1]).read_text(encoding='utf-8'))
            assert 'Settings' not in content
            assert content['Data'][0][1] != definition['Data'][0][1]
        if action == 'verify':
            content = json.loads(Path(args[args.index('--file') + 1]).read_text(encoding='utf-8'))
            assert content['Settings'] == {**definition['Settings'], 'model_id': '12345678-abcd-1234'}
            assert content['Data'][0][1] != definition['Data'][0][1]
        return subprocess.CompletedProcess(args, 0, json.dumps({'outcome': 'verified', 'verification': 'passed',
            'model_id': '12345678-abcd-1234', 'target': 'https://example.test'}), '')
    path = test_cli_live._run_roundtrip(tmp_path, runner=runner)
    evidence = json.loads(path.read_text(encoding='utf-8'))
    assert [args[4] for args in calls] == ['create', 'export', 'update', 'verify']
    assert all(args[5] == '12345678-abcd-1234' for args in calls[1:])
    assert evidence['outcome'] == 'passed'
    assert evidence['commit'] == 'synthetic-commit'
    assert evidence['live_extraction'] == evidence['excel_ui'] == 'not_run'

@pytest.mark.parametrize('failure', ['timeout', 'malformed'])
def test_live_harness_unknown_result_stops_without_second_creation(tmp_path, failure):
    writes = []
    def runner(args, **kwargs):
        if args[0] == 'git':
            return subprocess.CompletedProcess(args, 0, 'synthetic-commit\n', '')
        writes.append(args)
        if failure == 'timeout':
            raise subprocess.TimeoutExpired(args, 420, output='SECRET')
        return subprocess.CompletedProcess(args, 0, 'SECRET-NOT-JSON', 'SECRET')
    with pytest.raises(AssertionError):
        test_cli_live._run_roundtrip(tmp_path, runner=runner)
    evidence = json.loads(next(tmp_path.glob('*/evidence.json')).read_text(encoding='utf-8'))
    assert evidence['outcome'] == 'unknown'
    assert evidence['model_id'] is None
    assert evidence['steps'][0]['outcome'] == 'unknown'
    assert len(writes) == 1
    assert 'SECRET' not in json.dumps(evidence)
