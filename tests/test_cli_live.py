"""Explicitly opted-in live CLI smoke test; creates one disposable model.

Default pytest runs skip this test. See examples/power-supply/README.md.
"""
import copy
from datetime import datetime, timezone
import json
import os
from importlib.metadata import version
from pathlib import Path
import platform
import subprocess
import sys
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples' / 'power-supply'


def _run_roundtrip(output_root, runner=subprocess.run):
    """Persist each result before asserting, especially the newly created ID."""
    run_id = uuid.uuid4().hex
    directory = Path(output_root) / run_id
    directory.mkdir(parents=True, exist_ok=False)
    evidence_path = directory / 'evidence.json'
    commit = runner(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=15)
    dirty = runner(['git', 'diff', '--quiet', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=15)
    evidence = {'run_id': run_id, 'started_at': datetime.now(timezone.utc).isoformat(), 'outcome': 'running', 'package_version': version('wrangles'),
                'commit': commit.stdout.strip() if commit.returncode == 0 else 'unavailable',
                'uncommitted_tracked_changes': dirty.returncode != 0,
                'python': platform.python_version(), 'platform': platform.system(),
                'name': 'CLI synthetic Power Supply ' + run_id,
                'model_id': None, 'target': None, 'steps': [],
                'live_extraction': 'not_run', 'excel_ui': 'not_run', 'ci': 'not_run',
                'cleanup': 'Manual cleanup required for this disposable model; use the recorded ID. No automatic deletion.'}

    def save():
        temporary = evidence_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(evidence_path)

    def invoke(action, *arguments):
        step = {'command': 'model.' + action, 'outcome': 'started'}
        evidence['steps'].append(step)
        save()
        try:
            result = runner([sys.executable, '-m', 'wrangles', 'model', action, *arguments,
                             '--json', '--request-timeout', '30'], cwd=ROOT,
                            capture_output=True, text=True, timeout=420)
        except subprocess.TimeoutExpired:
            step['outcome'] = 'unknown'
            evidence['outcome'] = 'unknown'
            save()
            raise AssertionError('CLI process timed out; reconcile the model before rerunning. See evidence.json.') from None
        step['exit_code'] = result.returncode
        try:
            envelope = json.loads(result.stdout)
            assert isinstance(envelope, dict)
        except (ValueError, AssertionError):
            step['outcome'] = 'unknown'
            evidence['outcome'] = 'unknown'
            save()
            raise AssertionError('CLI did not return one JSON object; see evidence.json. Do not repeat creation blindly.') from None
        step['result'] = envelope
        step['outcome'] = envelope.get('outcome', 'unknown')
        if action == 'create' and envelope.get('model_id'):
            evidence['model_id'] = envelope['model_id']
        if envelope.get('target'):
            evidence['target'] = envelope['target']
        if result.returncode != 0:
            evidence['outcome'] = 'failed'
        save()
        assert result.returncode == 0, f'{action} failed; see {evidence_path}'
        return envelope

    save()
    created = invoke('create', '--type', 'extract-ai', '--file', str(EXAMPLE / 'definition.json'),
                     '--name', evidence['name'], '--verify', '--wait-timeout', '300')
    model_id = evidence['model_id']
    assert model_id and created['verification'] == 'passed'
    saved_path = directory / 'saved.json'
    invoke('export', model_id, '--output', str(saved_path))
    saved = json.loads(saved_path.read_text(encoding='utf-8'))
    revised = copy.deepcopy(saved)
    description = revised['Columns'].index('Description')
    revised['Data'][0][description] += ' Use the explicitly printed manufacturer name only.'
    # The service persists the update target in saved Settings.
    revised.setdefault('Settings', {}).setdefault('model_id', model_id)
    expected_path = directory / 'expected-after-update.json'
    expected_path.write_text(json.dumps(revised, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Omit settings from the update to verify that saved settings survive.
    revised.pop('Settings', None)
    revised_path = directory / 'update.json'
    revised_path.write_text(json.dumps(revised, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    updated = invoke('update', model_id, '--file', str(revised_path), '--verify', '--wait-timeout', '300')
    assert updated['model_id'] == model_id and updated['verification'] == 'passed'
    verified = invoke('verify', model_id, '--file', str(expected_path))
    assert verified['model_id'] == model_id and verified['verification'] == 'passed'
    evidence['outcome'] = 'passed'
    save()
    return evidence_path


@pytest.mark.skipif(os.environ.get('WRANGLES_RUN_LIVE_CLI') != '1', reason='Live model creation requires explicit WRANGLES_RUN_LIVE_CLI=1')
def test_live_saved_model_cli_roundtrip():
    output_root = os.environ.get('WRANGLES_CLI_LIVE_OUTPUT')
    assert output_root, 'Set WRANGLES_CLI_LIVE_OUTPUT to a persistent directory before running.'
    _run_roundtrip(output_root)
