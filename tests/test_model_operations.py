"""Synthetic service contracts for model operations and bounded SDK requests."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
import requests

from wrangles import model_operations as operations, utils, auth, config, console

MODEL_ID = '12345678-abcd-1234'
CONTENT = {'Columns': ['Find', 'Default', 'Extra'],
           'Data': [['Enabled', False, {'values': [0, None, 'Напруга']}]],
           'Settings': {'GeneralInstructions': 'Synthetic', 'flag': False}}


def response(body=None, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode()
    return result


@pytest.fixture
def service(monkeypatch):
    state = {'calls': [], 'metadata': {'id': MODEL_ID, 'purpose': 'extract', 'variant': 'extract-ai',
              'name': 'Synthetic', 'status': 'Ready', 'settings': {'password': 'SECRET'}, 'token': 'SECRET'},
             'content': copy.deepcopy(CONTENT), 'write': response({'model_id': MODEL_ID}, 202)}
    monkeypatch.setattr(auth, 'get_access_token', lambda: 'synthetic-token')
    def request(session, method, url, **kwargs):
        state['calls'].append((method, url, copy.deepcopy(kwargs)))
        assert session.get_adapter(url).max_retries.total == 0
        assert kwargs['timeout'] == 7
        assert kwargs['allow_redirects'] is False
        assert kwargs['headers'] == {'Authorization': 'Bearer synthetic-token'}
        if method in ('POST', 'PUT'):
            if isinstance(state['write'], BaseException):
                raise state['write']
            return state['write']
        if url.endswith('/model/metadata'):
            return response(state['metadata'])
        assert url.endswith('/model/content')
        return response(state['content'])
    monkeypatch.setattr(requests.Session, 'request', request)
    return state


def test_create_submits_full_content_once(service):
    original = copy.deepcopy(CONTENT)
    result = operations.SavedModelClient(7).create(CONTENT, name='Synthetic')
    assert result['model_id'] == MODEL_ID
    assert result['outcome'] == 'accepted'
    assert len(service['calls']) == 1
    method, url, kwargs = service['calls'][0]
    assert method == 'POST'
    assert url == config.api_host + '/model/content'
    assert kwargs['params'] == {'type': 'extract', 'variant': 'extract-ai', 'name': 'Synthetic'}
    assert kwargs['json']['Columns'] == CONTENT['Columns']
    assert kwargs['json']['Data'] == CONTENT['Data']
    assert kwargs['json']['Settings']['flag'] is False
    assert kwargs['json']['Settings']['AdditionalMessages'] == 'Synthetic'
    assert result['submitted_content'] == kwargs['json']
    assert CONTENT == original


@pytest.mark.parametrize('kwargs', [{'model_type': 'lookup'}, {'name': ''}, {'content': {'Columns': [], 'Data': []}}])
def test_create_invalid_inputs_never_contact_service(service, kwargs):
    arguments = {'content': CONTENT, 'name': 'Synthetic', **kwargs}
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create(**arguments)
    assert error.value.exit_code == 2
    assert service['calls'] == []


@pytest.mark.parametrize('override', [None, {}, {'flag': False, 'count': 0, 'nullable': None, 'GeneralInstructions': ''}])
def test_update_replaces_table_and_merges_content_settings(service, override):
    service['content']['Settings'] = {'flag': True, 'count': 9, 'nullable': 'present', 'keep': 'retained', 'GeneralInstructions': 'old'}
    submitted = {'Columns': ['Find'], 'Data': [['New']]}
    if override is not None:
        submitted['Settings'] = override
    original = copy.deepcopy(submitted)
    result = operations.SavedModelClient(7).update(MODEL_ID, submitted)
    assert [call[0] for call in service['calls']] == ['GET', 'GET', 'PUT']
    assert service['calls'][0][2]['params'] == {'id': MODEL_ID}
    assert service['calls'][1][2]['params'] == {'model_id': MODEL_ID}
    write = service['calls'][2][2]
    assert write['params'] == {'type': 'extract', 'model_id': MODEL_ID}
    assert write['json']['Columns'] == ['Find']
    assert write['json']['Data'] == [['New']]
    settings = write['json']['Settings']
    assert settings['keep'] == 'retained'
    assert settings['flag'] is (False if override else True)
    assert settings['count'] == (0 if override else 9)
    assert settings['nullable'] == (None if override else 'present')
    assert settings['GeneralInstructions'] == ('' if override else 'old')
    assert 'password' not in settings
    assert result['submitted_content'] == write['json']
    assert result['outcome'] == 'accepted'  # pre-update Ready is not update completion
    assert submitted == original


@pytest.mark.parametrize('settings', [None, {}])
def test_update_null_or_empty_settings_do_not_clear_existing(service, settings):
    result = operations.SavedModelClient(7).update(MODEL_ID, {'Columns': ['Find'], 'Data': [['New']], 'Settings': settings})
    assert result['submitted_content']['Settings']['GeneralInstructions'] == 'Synthetic'
    assert result['submitted_content']['Settings']['flag'] is False


@pytest.mark.parametrize('metadata', [{'purpose': 'lookup', 'variant': 'extract-ai'}, {'purpose': 'extract', 'variant': 'pattern'}, {}, {'purpose': 'extract'}])
def test_update_rejects_incompatible_metadata_before_content_or_write(service, metadata):
    service['metadata'] = metadata
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).update(MODEL_ID, CONTENT)
    assert error.value.code == 'unsupported_type'
    assert error.value.model_id == MODEL_ID
    assert len(service['calls']) == 1


def test_update_invalid_content_fails_before_network(service):
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).update(MODEL_ID, {'Columns': [], 'Data': []})
    assert error.value.model_id == MODEL_ID
    assert service['calls'] == []


def test_inspect_separates_metadata_from_content_and_secrets(service):
    result = operations.SavedModelClient(7).inspect(MODEL_ID)
    assert result == {'outcome': 'success', 'model_id': MODEL_ID, 'metadata': {
        'id': MODEL_ID, 'purpose': 'extract', 'variant': 'extract-ai', 'name': 'Synthetic', 'status': 'Ready'}}
    assert len(service['calls']) == 1
    assert 'SECRET' not in json.dumps(result)


def test_export_round_trip_can_be_submitted_to_same_id(service):
    client = operations.SavedModelClient(7)
    exported = client.export_definition(MODEL_ID)
    assert exported == CONTENT
    result = client.update(MODEL_ID, exported)
    assert result['submitted_content']['Columns'] == CONTENT['Columns']
    assert result['submitted_content']['Data'] == CONTENT['Data']
    assert [method for method, _, _ in service['calls']] == ['GET', 'GET', 'GET', 'GET', 'PUT']
    assert all('/model/' in url for _, url, _ in service['calls'])


@pytest.mark.parametrize('method', ['create', 'update'])
@pytest.mark.parametrize('failure', [requests.Timeout('SECRET'), requests.ConnectionError('SECRET'), response({}, 503)])
def test_uncertain_write_is_not_retried_and_retains_known_id(service, method, failure):
    service['write'] = failure
    client = operations.SavedModelClient(7)
    with pytest.raises(operations.ModelOperationError) as error:
        client.create(CONTENT, name='Synthetic') if method == 'create' else client.update(MODEL_ID, CONTENT)
    assert error.value.outcome == 'unknown'
    assert error.value.code == 'submission_unknown'
    assert error.value.model_id == (MODEL_ID if method == 'update' else None)
    assert error.value.exit_code == 4
    assert sum(call[0] in ('POST', 'PUT') for call in service['calls']) == 1
    assert 'SECRET' not in str(error.value)


@pytest.mark.parametrize('status,exit_code', [(401, 3), (403, 3), (400, 4), (302, 4)])
def test_service_errors_are_safe_and_classified(service, status, exit_code):
    service['write'] = response({'password': 'SECRET'}, status)
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create(CONTENT, name='Synthetic')
    assert error.value.exit_code == exit_code
    assert len(service['calls']) == 1
    assert 'SECRET' not in str(error.value)


@pytest.mark.parametrize('body', [{}, [], {'model_id': 'bad'}, {'id': MODEL_ID, 'model_id': '87654321-abcd-1234'}])
def test_accepted_create_missing_or_ambiguous_id_does_not_repeat(service, body):
    service['write'] = response(body, 202)
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create(CONTENT, name='Synthetic')
    assert error.value.code == 'missing_model_id'
    assert error.value.outcome == 'accepted'
    assert len(service['calls']) == 1


@pytest.mark.parametrize('timeout', [0, -1, float('inf'), float('nan'), True, '30'])
def test_invalid_request_timeout_rejected(timeout):
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(timeout)
    assert error.value.exit_code == 2


def test_service_target_uses_sdk_configuration_without_credential_diagnostics(monkeypatch):
    monkeypatch.setattr(config, 'api_host', 'https://user:SECRET@example.test:8443/api?token=SECRET#SECRET')
    assert operations.SavedModelClient().target == 'https://example.test:8443/api'


def test_bounded_requests_restore_nested_policy_and_isolate_threads(monkeypatch):
    calls = []
    def request(session, method, url, **kwargs):
        calls.append(kwargs)
        return response({})
    monkeypatch.setattr(requests.Session, 'request', request)
    with utils.bounded_requests(7):
        with utils.bounded_requests(2):
            utils.request_retries('POST', 'https://example.test')
        utils.request_retries('GET', 'https://example.test')
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(utils.request_retries, 'GET', 'https://example.test').result()
    utils.request_retries('GET', 'https://example.test')
    assert calls == [{'timeout': 2, 'allow_redirects': False}, {'timeout': 7, 'allow_redirects': False}, {}, {}]


def test_bounded_requests_restore_after_exception():
    with pytest.raises(RuntimeError):
        with utils.bounded_requests(7):
            raise RuntimeError()
    assert utils._REQUEST_TIMEOUT.get() is None


def test_authentication_requests_are_also_bounded(monkeypatch):
    calls = []
    monkeypatch.setattr(auth, '_access_token', None)
    monkeypatch.setattr(auth, 'refresh_token', None)
    monkeypatch.setattr(config, 'api_user', 'synthetic')
    monkeypatch.setattr(config, 'api_password', 'synthetic')
    def request(session, method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith('/token'):
            return response({'access_token': 'synthetic-token', 'expires_in': 300})
        return response({'id': MODEL_ID, 'status': 'Ready'})
    monkeypatch.setattr(requests.Session, 'request', request)
    operations.SavedModelClient(4).inspect(MODEL_ID)
    assert len(calls) == 2
    assert all(item[2]['timeout'] == 4 and item[2]['allow_redirects'] is False for item in calls)
    assert calls[1][2]['headers'] == {'Authorization': 'Bearer synthetic-token'}


def test_auth_failure_never_submits(service, monkeypatch):
    monkeypatch.setattr(auth, 'get_access_token', Mock(side_effect=RuntimeError('SECRET')))
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create(CONTENT, name='Synthetic')
    assert error.value.exit_code == 3
    assert service['calls'] == []
    assert 'SECRET' not in str(error.value)



@pytest.mark.parametrize('action', ['create', 'update', 'inspect', 'export'])
def test_cli_service_commands_json_and_arguments(service, tmp_path, capsys, action):
    definition = tmp_path / 'input with spaces.json'
    definition.write_text(json.dumps(CONTENT, ensure_ascii=False), encoding='utf-8')
    output = tmp_path / 'saved with spaces.json'
    args = ['model', action]
    if action == 'create':
        args += ['--type', 'extract-ai', '--name', 'Synthetic', '--file', str(definition)]
    else:
        args += [MODEL_ID]
        if action == 'update':
            args += ['--file', str(definition)]
        if action == 'export':
            args += ['--output', str(output)]
    console.main([*args, '--json', '--request-timeout', '7'])
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(captured.out.splitlines()) == 1
    assert result['command'] == 'model.' + action
    assert result['model_id'] == MODEL_ID
    assert result['outcome'] == ('accepted' if action in ('create', 'update') else 'success')
    assert result['readiness'] == result['verification'] == 'not_checked'
    assert result['target'] == config.api_host
    assert 'submitted_content' not in result
    assert 'SECRET' not in captured.out + captured.err
    if action == 'export':
        assert json.loads(output.read_text(encoding='utf-8')) == CONTENT
        assert result['output'] == str(output)
        assert not list(tmp_path.glob('.wrangles-*'))
    if action in ('create', 'update'):
        assert 'Submission accepted' in captured.err


def test_cli_export_failure_preserves_existing_destination(service, tmp_path, monkeypatch, capsys):
    output = tmp_path / 'existing.json'
    output.write_text('original', encoding='utf-8')
    monkeypatch.setattr(console._os, 'replace', Mock(side_effect=OSError('SECRET')))
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'export', MODEL_ID, '--output', str(output), '--json', '--request-timeout', '7'])
    assert error.value.code == 2
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result['error']['code'] == 'output_file'
    assert result['model_id'] == MODEL_ID
    assert output.read_text(encoding='utf-8') == 'original'
    assert not list(tmp_path.glob('.wrangles-*'))
    assert 'SECRET' not in captured.out + captured.err


def test_cli_invalid_definition_preserves_id_and_never_contacts_service(service, tmp_path, capsys):
    definition = tmp_path / 'invalid.json'
    definition.write_text('{', encoding='utf-8')
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'update', MODEL_ID, '--file', str(definition), '--json'])
    assert error.value.code == 2
    result = json.loads(capsys.readouterr().out)
    assert result['model_id'] == MODEL_ID
    assert result['error']['code'] == 'invalid_json'
    assert service['calls'] == []


def test_cli_unknown_submission_keeps_id_in_failure_envelope(service, tmp_path, capsys):
    definition = tmp_path / 'valid.json'
    definition.write_text(json.dumps(CONTENT), encoding='utf-8')
    service['write'] = requests.Timeout('SECRET')
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'update', MODEL_ID, '--file', str(definition), '--json', '--request-timeout', '7'])
    assert error.value.code == 4
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result['model_id'] == MODEL_ID
    assert result['outcome'] == 'unknown'
    assert result['error']['code'] == 'submission_unknown'
    assert 'SECRET' not in captured.out + captured.err


@pytest.mark.parametrize('args', [
    ['create', '--type', 'lookup', '--name', 'X', '--file', 'x.json'],
    ['update', MODEL_ID, '--file', 'x.json', '--name', 'rename'],
    ['export', MODEL_ID],
    ['inspect', MODEL_ID, '--request-timeout', '0'],
])
def test_cli_invalid_service_arguments_fail_before_network(service, capsys, args):
    with pytest.raises(SystemExit) as error:
        console.main(['model', *args, '--json'])
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'usage'
    assert service['calls'] == []


@pytest.mark.parametrize('content', [None, [], {'Columns': [], 'Data': []}, {'Columns': ['Find'], 'Data': [['A']], 'Settings': False}])
def test_bad_saved_content_does_not_trigger_update(service, content):
    service['content'] = content
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).update(MODEL_ID, CONTENT)
    assert error.value.exit_code == 4
    assert error.value.model_id == MODEL_ID
    assert all(call[0] == 'GET' for call in service['calls'])


def test_metadata_id_mismatch_blocks_update(service):
    service['metadata']['id'] = '87654321-abcd-1234'
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).update(MODEL_ID, CONTENT)
    assert error.value.code == 'malformed_response'
    assert error.value.model_id == MODEL_ID
    assert len(service['calls']) == 1


def test_successful_update_accepts_empty_response(service):
    service['write'] = response(None, 204)
    assert operations.SavedModelClient(7).update(MODEL_ID, CONTENT)['outcome'] == 'accepted'
    assert len(service['calls']) == 3


def test_invalid_json_creation_response_is_not_retried(service):
    bad = response({}, 202)
    bad._content = b'not-json SECRET'
    service['write'] = bad
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create(CONTENT, name='Synthetic')
    assert error.value.outcome == 'accepted'
    assert len(service['calls']) == 1
    assert 'SECRET' not in str(error.value)


def test_refresh_token_network_failure_does_not_submit(monkeypatch):
    monkeypatch.setattr(auth, '_access_token', None)
    monkeypatch.setattr(auth, 'refresh_token', 'synthetic')
    monkeypatch.setattr(auth._jwt, 'decode', lambda *args, **kwargs: {'azp': 'services'})
    request = Mock(side_effect=requests.Timeout('SECRET'))
    monkeypatch.setattr(requests.Session, 'request', request)
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create(CONTENT, name='Synthetic')
    assert error.value.code == 'authentication_transport'
    assert error.value.exit_code == 4
    request.assert_called_once()
    assert request.call_args.args[1].endswith('/token')
    assert request.call_args.kwargs['timeout'] == 7
    assert utils._REQUEST_TIMEOUT.get() is None


def test_legacy_retry_policy_is_unchanged_outside_bounded_context(monkeypatch):
    session = Mock()
    session.request.return_value = response({})
    monkeypatch.setattr(requests, 'Session', Mock(return_value=session))
    utils.request_retries('GET', 'https://example.test')
    adapter = session.mount.call_args.args[1]
    assert adapter.max_retries.total == 3
    assert 'POST' in adapter.max_retries.allowed_methods
    session.request.assert_called_once_with('GET', 'https://example.test')
    session.close.assert_called_once()

@pytest.mark.parametrize('key', ['id', 'modelId', 'model'])
def test_creation_accepts_existing_sdk_id_aliases(service, key):
    service['write'] = response({key: MODEL_ID}, 202)
    assert operations.SavedModelClient(7).create(CONTENT, name='Synthetic')['model_id'] == MODEL_ID
    assert len(service['calls']) == 1


@pytest.mark.parametrize('failure', [requests.Timeout('SECRET'), requests.ConnectionError('SECRET')])
def test_read_network_failure_preserves_id(monkeypatch, failure):
    monkeypatch.setattr(auth, 'get_access_token', lambda: 'synthetic')
    request = Mock(side_effect=failure)
    monkeypatch.setattr(requests.Session, 'request', request)
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).inspect(MODEL_ID)
    assert error.value.code == 'network'
    assert error.value.model_id == MODEL_ID
    assert error.value.outcome == 'error'
    request.assert_called_once()


def test_export_rejects_wrong_model_family_before_reading_content(service):
    service['metadata']['purpose'] = 'lookup'
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).export_definition(MODEL_ID)
    assert error.value.code == 'unsupported_type'
    assert len(service['calls']) == 1


def test_non_json_content_fails_before_request(service):
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create({**CONTENT, 'extra': float('nan')}, name='Synthetic')
    assert error.value.exit_code == 2
    assert service['calls'] == []


def test_cli_export_subprocess_writes_document_separately(tmp_path):
    import subprocess
    import sys
    output = tmp_path / 'definition space.json'
    script = '''import json, socket
import requests
def blocked(*a, **k): raise AssertionError('Unexpected network')
socket.socket.connect = blocked
from wrangles import auth, console
auth.get_access_token = lambda: 'synthetic'
def request(session, method, url, **kwargs):
    assert method == 'GET'
    body = {'purpose': 'extract', 'variant': 'extract-ai'} if url.endswith('/metadata') else {'Columns': ['Find'], 'Data': [['Напруга']], 'Settings': {}}
    result = requests.Response()
    result.status_code = 200
    result._content = json.dumps(body).encode()
    return result
requests.Session.request = request
console.main()
'''
    result = subprocess.run([sys.executable, '-c', script, 'model', 'export', MODEL_ID, '--output', str(output), '--json'], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['outcome'] == 'success'
    assert len(result.stdout.splitlines()) == 1
    assert json.loads(output.read_text(encoding='utf-8')) == {'Columns': ['Find'], 'Data': [['Напруга']], 'Settings': {}}
    assert 'Service target:' in result.stderr

@pytest.mark.parametrize('value', ['', 'wrong', '12345678-abcd-1234:version'])
def test_invalid_model_id_does_not_contact_service(service, value):
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).inspect(value)
    assert error.value.exit_code == 2
    assert service['calls'] == []


@pytest.mark.parametrize('failure,code,error_code', [(KeyboardInterrupt(), 130, 'interrupted'), (RuntimeError('SECRET'), 1, 'unexpected')])
def test_cli_interruption_or_unexpected_failure_keeps_update_id(service, tmp_path, capsys, failure, code, error_code):
    definition = tmp_path / 'valid.json'
    definition.write_text(json.dumps(CONTENT), encoding='utf-8')
    service['write'] = failure
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'update', MODEL_ID, '--file', str(definition), '--json', '--request-timeout', '7'])
    assert error.value.code == code
    captured = capsys.readouterr()
    envelope = json.loads(captured.out)
    assert envelope['model_id'] == MODEL_ID
    assert envelope['error']['code'] == error_code
    assert 'SECRET' not in captured.out + captured.err
    assert len(service['calls']) == 3

class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    timer = FakeClock()
    monkeypatch.setattr(operations, 'time', timer)
    monkeypatch.setattr(utils, '_time', timer)
    return timer


def submission():
    return {'outcome': 'accepted', 'model_id': MODEL_ID,
            'submitted_content': {'Columns': ['Find'], 'Data': [['New']], 'Settings': {}}}


@pytest.mark.parametrize('expected,actual,kind', [
    ({'a': None}, {}, 'missing'), ({}, {'a': None}, 'unexpected'),
    (False, 0, 'type'), (False, '', 'type'), (0, None, 'type'), (1, 1.0, 'type'),
    ([1, 2], [2, 1], 'value'), ({'x': {'y': 'SECRET-ONE'}}, {'x': {'y': 'SECRET-TWO'}}, 'value'),
    (['Find', 'Type'], ['Type', 'Find'], 'value'),
])
def test_content_comparison_preserves_meaningful_differences(expected, actual, kind):
    result = operations.compare_content(expected, actual)
    assert result['matches'] is False
    assert result['differences'][0]['kind'] == kind
    assert 'SECRET' not in json.dumps(result)


def test_content_comparison_ignores_only_object_key_order():
    result = operations.compare_content({'a': False, 'b': [0, None, 'Напруга']}, {'b': [0, None, 'Напруга'], 'a': False})
    assert result == {'matches': True, 'differences': [], 'differences_truncated': False}


def test_content_comparison_limits_diagnostics():
    result = operations.compare_content(list(range(30)), list(range(1, 31)), max_differences=3)
    assert result['matches'] is False
    assert result['differences'] == [{'path': '$[0]', 'kind': 'value'}, {'path': '$[1]', 'kind': 'value'}, {'path': '$[2]', 'kind': 'value'}]
    assert result['differences_truncated'] is True


@pytest.mark.parametrize('status', ['Processing', 'Accepted', 'Queued'])
def test_create_waits_until_ready_without_readback_when_not_verifying(monkeypatch, clock, status):
    client = operations.SavedModelClient()
    request = Mock(return_value=response({'model_id': MODEL_ID}, 202))
    monkeypatch.setattr(client, '_request', request)
    metadata = Mock(side_effect=[{'status': status}, {'status': 'Ready'}])
    monkeypatch.setattr(client, '_metadata', metadata)
    read = Mock()
    monkeypatch.setattr(client, 'read_content', read)
    result = client.create(submission()['submitted_content'], name='Synthetic', wait=True, wait_timeout=10)
    assert result['outcome'] == 'ready'
    assert result['readiness'] == 'ready'
    assert result['verification'] == 'not_checked'
    assert clock.sleeps == [2]
    assert metadata.call_count == 2
    request.assert_called_once()
    assert request.call_args.args[0] == 'POST'
    read.assert_not_called()
    assert operations._DEADLINE.get() is None


def test_create_verify_implies_wait_and_compares_effective_content(monkeypatch, clock):
    client = operations.SavedModelClient()
    monkeypatch.setattr(client, '_request', Mock(return_value=response({'id': MODEL_ID}, 202)))
    monkeypatch.setattr(client, '_metadata', Mock(side_effect=[{'status': 'Processing'}, {'status': 'Ready'}]))
    effective = operations.ai_saved_model.prepare_content(CONTENT)
    read = Mock(return_value=effective)
    monkeypatch.setattr(client, 'read_content', read)
    result = client.create(CONTENT, name='Synthetic', verify=True)
    assert result['outcome'] == 'verified'
    assert result['verification'] == 'passed'
    assert result['readiness'] == 'ready'
    assert result['submitted_content'] == effective
    read.assert_called_once_with(MODEL_ID)
    assert clock.sleeps == [2]


def test_standalone_verify_is_read_only_and_keeps_readiness_unchecked(service):
    service['content'] = operations.ai_saved_model.prepare_content(CONTENT)
    result = operations.SavedModelClient(7).verify(MODEL_ID, CONTENT)
    assert result['outcome'] == 'verified'
    assert result['verification'] == 'passed'
    assert result['readiness'] == 'not_checked'
    assert [call[0] for call in service['calls']] == ['GET', 'GET']


def test_standalone_verify_reports_safe_field_differences(service):
    service['content'] = operations.ai_saved_model.prepare_content(CONTENT)
    service['content']['Data'][0][1] = 'SECRET'
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).verify(MODEL_ID, CONTENT)
    assert error.value.exit_code == 6
    assert error.value.model_id == MODEL_ID
    assert error.value.verification == 'failed'
    assert error.value.differences['differences'] == [{'path': '$["Data"][0][1]', 'kind': 'type'}]
    assert 'SECRET' not in str(error.value) + json.dumps(error.value.differences)
    assert [call[0] for call in service['calls']] == ['GET', 'GET']


def test_update_skips_stale_ready_and_verifies_effective_settings(monkeypatch, clock):
    client = operations.SavedModelClient()
    metadata = {'purpose': 'extract', 'variant': 'extract-ai', 'status': 'Ready'}
    monkeypatch.setattr(client, '_metadata', Mock(side_effect=[metadata, metadata, {'status': 'Processing'}, metadata]))
    old = {'Columns': ['Find'], 'Data': [['Old']], 'Settings': {'keep': False}}
    effective = {'Columns': ['Find'], 'Data': [['New']], 'Settings': {'keep': False}}
    read = Mock(side_effect=[old, old, effective])
    monkeypatch.setattr(client, 'read_content', read)
    request = Mock(return_value=response(None, 204))
    monkeypatch.setattr(client, '_request', request)
    result = client.update(MODEL_ID, {'Columns': ['Find'], 'Data': [['New']]}, verify=True, wait_timeout=10)
    assert result['outcome'] == 'verified'
    assert result['verification'] == 'passed'
    assert result['readiness'] == 'unconfirmed'
    assert result['freshness']['readback_matches'] is True
    assert result['freshness']['status_transition_observed'] is True
    assert 'version' in result['freshness']['limitation']
    assert request.call_args.kwargs['json'] == effective
    request.assert_called_once()
    assert clock.sleeps == [2, 2]


def test_identical_update_never_claims_version_specific_ready(monkeypatch, clock):
    client = operations.SavedModelClient()
    monkeypatch.setattr(client, '_metadata', Mock(return_value={'status': 'Ready'}))
    monkeypatch.setattr(client, 'read_content', Mock(return_value=submission()['submitted_content']))
    result = client.wait_for_submission(submission(), update=True)
    assert result['outcome'] == 'accepted'
    assert result['readiness'] == 'unconfirmed'
    assert result['freshness']['submission_version'] == 'unavailable'
    assert result['freshness']['status_transition_observed'] is False
    assert result['freshness']['readback_matches'] is True


def test_stale_ready_until_deadline_preserves_id_and_last_readback(monkeypatch, clock):
    client = operations.SavedModelClient()
    metadata = Mock(return_value={'status': 'Ready'})
    monkeypatch.setattr(client, '_metadata', metadata)
    monkeypatch.setattr(client, 'read_content', Mock(return_value={'Columns': ['Find'], 'Data': [['Old']], 'Settings': {}}))
    with pytest.raises(operations.ModelOperationError) as error:
        client.wait_for_submission(submission(), update=True, verify=True, wait_timeout=5, poll_interval=2)
    assert error.value.exit_code == 5
    assert error.value.model_id == MODEL_ID
    assert error.value.readiness == 'unconfirmed'
    assert error.value.verification == 'pending'
    assert error.value.differences['matches'] is False
    assert clock.sleeps == [2, 2, 1]
    assert metadata.call_count == 3
    assert operations._DEADLINE.get() is None


@pytest.mark.parametrize('update', [False, True])
def test_ready_readback_mismatch_has_exit_six(monkeypatch, clock, update):
    client = operations.SavedModelClient()
    monkeypatch.setattr(client, '_metadata', Mock(side_effect=[{'status': 'Processing'}, {'status': 'Ready'}]))
    monkeypatch.setattr(client, 'read_content', Mock(return_value={'Columns': ['Find'], 'Data': [['Other']], 'Settings': {}}))
    with pytest.raises(operations.ModelOperationError) as error:
        client.wait_for_submission(submission(), update=update, verify=True)
    assert error.value.exit_code == 6
    assert error.value.model_id == MODEL_ID
    assert error.value.verification == 'failed'
    assert error.value.readiness == ('unconfirmed' if update else 'ready')
    assert error.value.differences['differences'] == [{'path': '$["Data"][0][0]', 'kind': 'value'}]


@pytest.mark.parametrize('status,code', [('Failed', 'processing_failed'), ('Error', 'processing_failed'), (None, 'malformed_status'), ('unexpected', 'malformed_status')])
def test_wait_processing_failures_and_malformed_status(monkeypatch, clock, status, code):
    client = operations.SavedModelClient()
    monkeypatch.setattr(client, '_metadata', Mock(return_value={'status': status}))
    with pytest.raises(operations.ModelOperationError) as error:
        client.wait_for_submission(submission())
    assert error.value.exit_code == 4
    assert error.value.code == code
    assert error.value.model_id == MODEL_ID
    assert clock.sleeps == []


@pytest.mark.parametrize('failure,code', [(KeyboardInterrupt(), 130), (RuntimeError('SECRET'), 1)])
def test_wait_failures_after_create_retain_new_id(monkeypatch, clock, failure, code):
    client = operations.SavedModelClient()
    monkeypatch.setattr(client, '_request', Mock(return_value=response({'model_id': MODEL_ID}, 202)))
    monkeypatch.setattr(client, '_metadata', Mock(side_effect=failure))
    with pytest.raises(operations.ModelOperationError) as error:
        client.create(CONTENT, name='Synthetic', wait=True)
    assert error.value.exit_code == code
    assert error.value.model_id == MODEL_ID
    assert 'SECRET' not in str(error.value)
    assert operations._DEADLINE.get() is None


@pytest.mark.parametrize('timeout', [0, -1, float('nan'), float('inf')])
def test_invalid_wait_options_fail_before_submission(service, timeout):
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(7).create(CONTENT, name='Synthetic', wait=True, wait_timeout=timeout)
    assert error.value.exit_code == 2
    assert service['calls'] == []


def test_deadline_caps_requests_and_rejects_late_response(monkeypatch, clock):
    seen = []
    result = Mock()
    def request(session, method, url, **kwargs):
        seen.append(kwargs['timeout'])
        clock.now += 6
        return result
    monkeypatch.setattr(requests.Session, 'request', request)
    with pytest.raises(utils.RequestDeadlineExceeded):
        with utils.bounded_requests(30, deadline=105):
            utils.request_retries('GET', 'https://example.test')
    assert seen == [5]
    result.close.assert_called_once()
    assert utils._REQUEST_DEADLINE.get() is None


def test_expired_deadline_prevents_request(monkeypatch, clock):
    request = Mock()
    monkeypatch.setattr(requests.Session, 'request', request)
    with pytest.raises(utils.RequestDeadlineExceeded):
        with utils.bounded_requests(30, deadline=100):
            utils.request_retries('GET', 'https://example.test')
    request.assert_not_called()


def test_wait_rejects_readback_arriving_after_deadline(monkeypatch, clock):
    client = operations.SavedModelClient()
    monkeypatch.setattr(client, '_metadata', Mock(return_value={'status': 'Ready'}))
    def late_read(model_id):
        clock.now += 10
        return submission()['submitted_content']
    monkeypatch.setattr(client, 'read_content', late_read)
    with pytest.raises(operations.ModelOperationError) as error:
        client.wait_for_submission(submission(), verify=True, wait_timeout=5)
    assert error.value.exit_code == 5
    assert error.value.model_id == MODEL_ID


def test_deadline_returns_while_transport_is_still_blocked(monkeypatch):
    from threading import Event
    import time
    started, release, finished = Event(), Event(), Event()
    result = Mock()
    result.close.side_effect = finished.set
    def request(session, method, url, **kwargs):
        started.set()
        assert release.wait(5)
        return result
    monkeypatch.setattr(requests.Session, 'request', request)
    try:
        with pytest.raises(utils.RequestDeadlineExceeded):
            with utils.bounded_requests(30, deadline=time.monotonic() + 0.1):
                utils.request_retries('GET', 'https://example.test')
        assert started.is_set()
        assert not release.is_set()
    finally:
        release.set()
        assert finished.wait(5)
    assert result.close.called


def test_wait_network_deadline_has_model_id(monkeypatch, clock):
    monkeypatch.setattr(auth, 'get_access_token', lambda: 'synthetic')
    def request(session, method, url, **kwargs):
        assert kwargs['timeout'] == 5
        clock.now += 6
        raise requests.Timeout('SECRET')
    monkeypatch.setattr(requests.Session, 'request', request)
    with pytest.raises(operations.ModelOperationError) as error:
        operations.SavedModelClient(30).wait_for_submission(submission(), wait_timeout=5)
    assert error.value.exit_code == 5
    assert error.value.model_id == MODEL_ID
    assert 'SECRET' not in str(error.value)


def test_cli_verify_json_is_read_only(service, tmp_path, capsys):
    service['content'] = operations.ai_saved_model.prepare_content(CONTENT)
    expected = tmp_path / 'expected.json'
    expected.write_text(json.dumps(CONTENT), encoding='utf-8')
    console.main(['model', 'verify', MODEL_ID, '--file', str(expected), '--json', '--request-timeout', '7'])
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result['command'] == 'model.verify'
    assert result['outcome'] == 'verified'
    assert result['verification'] == 'passed'
    assert result['readiness'] == 'not_checked'
    assert result['comparison']['matches'] is True
    assert 'extraction accuracy' in output.err
    assert [call[0] for call in service['calls']] == ['GET', 'GET']


@pytest.mark.parametrize('failure', [False, True])
def test_cli_create_verify_forwards_options_and_retains_new_id(monkeypatch, tmp_path, capsys, failure):
    path = tmp_path / 'model.json'
    path.write_text(json.dumps(submission()['submitted_content']), encoding='utf-8')
    client = Mock(target='https://example.test')
    if failure:
        client.create.side_effect = operations.ModelOperationError('deadline', 'Timed out.', exit_code=5, model_id=MODEL_ID, readiness='unconfirmed')
    else:
        client.create.return_value = {**submission(), 'outcome': 'verified', 'readiness': 'ready', 'verification': 'passed'}
    monkeypatch.setattr(console._models, 'SavedModelClient', Mock(return_value=client))
    args = ['model', 'create', '--file', str(path), '--name', 'Synthetic', '--type', 'extract-ai', '--verify', '--wait-timeout', '12', '--json']
    if failure:
        with pytest.raises(SystemExit) as error:
            console.main(args)
        assert error.value.code == 5
    else:
        console.main(args)
    client.create.assert_called_once_with(submission()['submitted_content'], name='Synthetic', model_type='extract-ai', wait=False, verify=True, wait_timeout=12)
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result['model_id'] == MODEL_ID
    assert result['readiness'] == ('unconfirmed' if failure else 'ready')
    assert result['verification'] == ('not_checked' if failure else 'passed')
    assert len(output.out.splitlines()) == 1


def test_cli_mismatch_reports_paths_without_values(service, tmp_path, capsys):
    service['content'] = submission()['submitted_content']
    expected = tmp_path / 'expected.json'
    expected.write_text(json.dumps({'Columns': ['Find'], 'Data': [['SECRET']]}), encoding='utf-8')
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'verify', MODEL_ID, '--file', str(expected), '--json', '--request-timeout', '7'])
    assert error.value.code == 6
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result['verification'] == 'failed'
    assert result['comparison']['differences'] == [{'path': '$["Data"][0][0]', 'kind': 'value'}]
    assert '$["Data"][0][0]' in output.err
    assert 'SECRET' not in output.out + output.err


def test_cli_wait_timeout_validation_prevents_creation(service, tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        console.main(['model', 'create', '--type', 'extract-ai', '--file', 'not-needed.json', '--name', 'X', '--wait-timeout', '0', '--json'])
    assert error.value.code == 2
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'usage'
    assert service['calls'] == []


def test_cli_update_forwards_wait_and_verify(monkeypatch, tmp_path, capsys):
    path = tmp_path / 'expected.json'
    path.write_text(json.dumps(submission()['submitted_content']), encoding='utf-8')
    client = Mock(target='https://example.test')
    client.update.return_value = {**submission(), 'outcome': 'verified', 'readiness': 'unconfirmed', 'verification': 'passed',
                                 'freshness': {'limitation': 'No submission version evidence.'}}
    monkeypatch.setattr(console._models, 'SavedModelClient', Mock(return_value=client))
    console.main(['model', 'update', MODEL_ID, '--file', str(path), '--wait', '--verify', '--wait-timeout', '22', '--json'])
    client.update.assert_called_once_with(MODEL_ID, submission()['submitted_content'], wait=True, verify=True, wait_timeout=22)
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result['readiness'] == 'unconfirmed'
    assert result['verification'] == 'passed'
    assert result['freshness']['limitation'] in output.err


def test_deadline_budget_is_recomputed_after_authentication(monkeypatch, clock):
    def authenticate():
        clock.now += 3
        return 'synthetic'
    monkeypatch.setattr(auth, 'get_access_token', authenticate)
    request = Mock(return_value=response({'status': 'Ready'}))
    monkeypatch.setattr(requests.Session, 'request', request)
    result = operations.SavedModelClient(30).wait_for_submission(submission(), wait_timeout=5)
    assert result['readiness'] == 'ready'
    assert request.call_args.kwargs['timeout'] == 2
    assert utils._REQUEST_DEADLINE.get() is None


@pytest.mark.parametrize('operation', ['create', 'update'])
@pytest.mark.parametrize('difference', [None, 'wrong_parameter', 'unknown_setting', 'changed_data', 'explicit_setting'])
def test_submission_verification_checks_server_added_settings(monkeypatch, operation, difference):
    client = operations.SavedModelClient(7)
    original = {'Columns': ['Find', 'Default'], 'Data': [['Enabled', False]],
                'Settings': {'keep': {'values': [0, None, False]}}}
    parameter = 'name' if operation == 'create' else 'model_id'
    if difference == 'explicit_setting':
        original['Settings'][parameter] = 'explicit user value'
    before = copy.deepcopy(original)
    state = {'content': copy.deepcopy(original), 'writes': []}

    def request(method, endpoint, **kwargs):
        state['writes'].append(method)
        state['content'] = copy.deepcopy(kwargs['json'])
        state['content']['Settings'].update(kwargs['params'])
        if difference == 'wrong_parameter':
            state['content']['Settings'][parameter] = 'wrong'
        elif difference == 'unknown_setting':
            state['content']['Settings']['unexpected'] = True
        elif difference == 'changed_data':
            state['content']['Data'][0][1] = 0
        return response({'model_id': MODEL_ID}, 202)

    metadata = {'purpose': 'extract', 'variant': 'extract-ai', 'status': 'Ready'}
    statuses = [metadata, {**metadata, 'status': 'Processing'}, metadata] if operation == 'update' else [metadata]
    monkeypatch.setattr(client, '_request', request)
    monkeypatch.setattr(client, '_metadata', Mock(side_effect=statuses))
    monkeypatch.setattr(client, 'read_content', lambda model_id: copy.deepcopy(state['content']))
    arguments = {'name': 'Synthetic'} if operation == 'create' else {}
    args = (original,) if operation == 'create' else (MODEL_ID, original)
    if difference is None:
        result = getattr(client, operation)(*args, **arguments, verify=True, poll_interval=0.001)
        assert result['verification'] == 'passed'
        assert result['model_id'] == MODEL_ID
        assert result['readiness'] == ('ready' if operation == 'create' else 'unconfirmed')
        assert result['submitted_content'] == before
    else:
        with pytest.raises(operations.ModelOperationError) as caught:
            getattr(client, operation)(*args, **arguments, verify=True, poll_interval=0.001)
        assert caught.value.exit_code == 6
        assert caught.value.verification == 'failed'
        expected_path = ('$["Data"][0][1]' if difference == 'changed_data' else
                         '$["Settings"]["unexpected"]' if difference == 'unknown_setting' else
                         '$["Settings"]["' + parameter + '"]')
        assert caught.value.differences['differences'][0]['path'] == expected_path
    assert original == before
    assert state['writes'] == ['POST' if operation == 'create' else 'PUT']
