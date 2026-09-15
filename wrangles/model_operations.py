"""Reusable operations for saved Extract-AI models using the SDK transport.

Submission success means accepted, not Ready. No operation retries a write.
"""
import copy
import json
import math
import re
import time
from contextvars import ContextVar
from urllib.parse import urlsplit, urlunsplit

import requests

from . import ai_saved_model, auth, config, utils


class ModelOperationError(RuntimeError):
    """Safe diagnostic with an exit code and the known model ID, if any."""
    def __init__(self, code, message, *, exit_code=4, model_id=None, outcome='error',
                 readiness='not_checked', verification='not_checked', differences=None, freshness=None):
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.model_id = model_id
        self.outcome = outcome
        self.readiness = readiness
        self.verification = verification
        self.differences = differences
        self.freshness = freshness


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}', value):
        raise ModelOperationError('input', 'Model ID must have the form XXXXXXXX-XXXX-XXXX.', exit_code=2)
    return value


def _content(value, model_id=None):
    try:
        json.dumps(value, allow_nan=False)
        return ai_saved_model.prepare_content(value)
    except (ValueError, TypeError, RecursionError):
        raise ModelOperationError('authoring_validation', 'Invalid saved-model definition; use model validate for locations.',
                                  exit_code=2, model_id=model_id) from None


_DEADLINE = ContextVar('wrangles_model_deadline', default=None)
_UPDATE_LIMITATION = ('The API does not provide a confirmed submission-to-version link. '
                      'Matching readback does not prove readiness of this particular update.')


def compare_content(expected, actual, *, max_differences=20):
    """Compare JSON trees without printing values or ignoring unknown fields.

    Object-key order is insignificant; array order and JSON value types matter.
    Paths identify fields, while difference entries never contain field values.
    """
    if isinstance(max_differences, bool) or not isinstance(max_differences, int) or max_differences <= 0:
        raise ValueError('max_differences must be a positive integer')
    differences = []
    def visit(left, right, path):
        if len(differences) > max_differences:
            return
        if type(left) is not type(right):
            differences.append({'path': path, 'kind': 'type'})
        elif isinstance(left, dict):
            for key in sorted(left.keys() | right.keys()):
                child = path + '[' + json.dumps(key, ensure_ascii=True) + ']'
                if key not in left:
                    differences.append({'path': child, 'kind': 'unexpected'})
                elif key not in right:
                    differences.append({'path': child, 'kind': 'missing'})
                else:
                    visit(left[key], right[key], child)
                if len(differences) > max_differences:
                    break
        elif isinstance(left, list):
            for index in range(max(len(left), len(right))):
                child = f'{path}[{index}]'
                if index >= len(left):
                    differences.append({'path': child, 'kind': 'unexpected'})
                elif index >= len(right):
                    differences.append({'path': child, 'kind': 'missing'})
                else:
                    visit(left[index], right[index], child)
                if len(differences) > max_differences:
                    break
        elif left != right:
            differences.append({'path': path, 'kind': 'value'})
    visit(expected, actual, '$')
    return {'matches': not differences, 'differences': differences[:max_differences],
            'differences_truncated': len(differences) > max_differences}


def _wait_options(wait_timeout, poll_interval):
    for value in (wait_timeout, poll_interval):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ModelOperationError('input', 'Wait timeout and polling interval must be finite positive seconds.', exit_code=2)


def _deadline_error(model_id):
    return ModelOperationError('deadline', 'Waiting deadline exceeded. The submitted model may still complete; reconcile using its ID.',
                               exit_code=5, model_id=model_id, readiness='unconfirmed')


class SavedModelClient:
    """Use existing SDK credentials and target; bound every HTTP request.

    ``request_timeout`` is in seconds and applies to connection/read inactivity,
    including token refresh. Returned submission content is for Python readback
    verification; the CLI never includes it in its status envelope.
    """
    def __init__(self, request_timeout=30):
        if isinstance(request_timeout, bool) or not isinstance(request_timeout, (int, float)) or not math.isfinite(request_timeout) or request_timeout <= 0:
            raise ModelOperationError('input', 'Request timeout must be a finite positive number of seconds.', exit_code=2)
        self.request_timeout = request_timeout
        self._target = config.api_host.rstrip('/')
        parts = urlsplit(self._target)
        # Do not print userinfo, query strings, or fragments from configuration.
        self.target = urlunsplit((parts.scheme, parts.hostname or '', parts.path, '', ''))
        if parts.port:
            self.target = urlunsplit((parts.scheme, f'{parts.hostname}:{parts.port}', parts.path, '', ''))

    def _request(self, method, endpoint, *, model_id=None, **kwargs):
        with utils.bounded_requests(self.request_timeout, deadline=_DEADLINE.get()):
            try:
                token = auth.get_access_token()
            except Exception as error:
                # Refresh-token auth wraps its transport exceptions. Preserve
                # timeout/network classification without exposing the raw text.
                cause = error
                seen = set()
                while cause is not None and id(cause) not in seen:
                    seen.add(id(cause))
                    if isinstance(cause, utils.RequestDeadlineExceeded):
                        raise _deadline_error(model_id) from None
                    if isinstance(cause, KeyboardInterrupt):
                        raise cause
                    if isinstance(cause, requests.RequestException):
                        if _DEADLINE.get() is not None and time.monotonic() >= _DEADLINE.get():
                            raise _deadline_error(model_id) from None
                        raise ModelOperationError('authentication_transport', 'Could not contact the authentication service.', model_id=model_id) from None
                    cause = cause.__cause__ or cause.__context__
                raise ModelOperationError('authentication', 'Authentication failed. Check existing Wrangles credentials.', exit_code=3, model_id=model_id) from None
            try:
                response = utils.request_retries(method, self._target + endpoint,
                    headers={'Authorization': f'Bearer {token}'}, **kwargs)
            except utils.RequestDeadlineExceeded:
                raise _deadline_error(model_id) from None
            except requests.RequestException:
                if _DEADLINE.get() is not None and time.monotonic() >= _DEADLINE.get():
                    raise _deadline_error(model_id) from None
                if method in {'POST', 'PUT'}:
                    raise ModelOperationError('submission_unknown',
                        'Submission outcome is unknown. Do not repeat creation. Reconcile with the service; use the known ID for readback when available.',
                        model_id=model_id, outcome='unknown') from None
                raise ModelOperationError('network', 'Could not read the model from the service.', model_id=model_id) from None
        if not isinstance(getattr(response, 'status_code', None), int):
            write = method in {'POST', 'PUT'}
            raise ModelOperationError('malformed_response', 'The service returned no valid HTTP status; reconcile any submitted write.',
                                      model_id=model_id, outcome='unknown' if write else 'error')
        if response.status_code in (401, 403):
            raise ModelOperationError('access', 'Authentication or model access was denied.', exit_code=3, model_id=model_id)
        if not 200 <= response.status_code < 300:
            uncertain = method in {'POST', 'PUT'} and (response.status_code >= 500 or response.status_code == 408)
            raise ModelOperationError('submission_unknown' if uncertain else 'service',
                'Submission outcome is unknown; reconcile before repeating a write.' if uncertain else 'The service rejected the request.',
                model_id=model_id, outcome='unknown' if uncertain else 'error')
        return response

    @staticmethod
    def _json(response, model_id=None):
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError()
            json.dumps(result, allow_nan=False)
            return result
        except (ValueError, TypeError, RecursionError):
            raise ModelOperationError('malformed_response', 'The service returned an invalid model document.', model_id=model_id) from None

    def _metadata(self, model_id):
        model_id = _id(model_id)
        result = self._json(self._request('GET', '/model/metadata', model_id=model_id, params={'id': model_id}), model_id)
        if result.get('id') not in (None, model_id):
            raise ModelOperationError('malformed_response', 'Metadata ID does not match the requested model.', model_id=model_id)
        return result

    @staticmethod
    def _require_extract_ai(metadata, model_id):
        # The existing SDK uses purpose for the model family; type can describe
        # other metadata. Accept type as a fallback for responses without purpose.
        purpose = metadata.get('purpose', metadata.get('type'))
        if purpose != 'extract' or metadata.get('variant') != 'extract-ai':
            raise ModelOperationError('unsupported_type', 'This operation requires an extract / extract-ai model.', exit_code=2, model_id=model_id)

    def read_content(self, model_id):
        """Read the full saved definition; never request a secret store."""
        model_id = _id(model_id)
        result = self._json(self._request('GET', '/model/content', model_id=model_id, params={'model_id': model_id}), model_id)
        try:
            ai_saved_model.prepare_content(result)
        except (ValueError, TypeError, RecursionError):
            raise ModelOperationError('malformed_content', 'Saved content does not satisfy the authoring contract.', model_id=model_id) from None
        return result

    def create(self, content, *, name, model_type='extract-ai', wait=False, verify=False, wait_timeout=300, poll_interval=2):
        _wait_options(wait_timeout, poll_interval)
        if model_type != 'extract-ai':
            raise ModelOperationError('unsupported_type', 'Only extract-ai model creation is supported.', exit_code=2)
        if not isinstance(name, str) or not name.strip():
            raise ModelOperationError('input', 'A non-empty model name is required.', exit_code=2)
        prepared = _content(content)
        response = self._request('POST', '/model/content', params={'type': 'extract', 'variant': 'extract-ai', 'name': name}, json=prepared)
        try:
            body = self._json(response)
            identifiers = [body[key] for key in ('model_id', 'id', 'modelId', 'model') if body.get(key) is not None]
            model_id = _id(identifiers[0])
            if any(value != model_id for value in identifiers):
                raise ValueError()
        except (ModelOperationError, IndexError, ValueError):
            raise ModelOperationError('missing_model_id', 'Submission was accepted, but no unambiguous model ID was returned. Reconcile with the service; do not repeat creation.', outcome='accepted') from None
        result = {'outcome': 'accepted', 'model_id': model_id, 'submitted_content': prepared}
        return self.wait_for_submission(result, verify=verify, wait_timeout=wait_timeout, poll_interval=poll_interval) if wait or verify else result

    def update(self, model_id, content, *, wait=False, verify=False, wait_timeout=300, poll_interval=2):
        _wait_options(wait_timeout, poll_interval)
        model_id = _id(model_id)
        prepared = _content(content, model_id)
        metadata = self._metadata(model_id)
        self._require_extract_ai(metadata, model_id)
        existing = self.read_content(model_id)
        prepared['Settings'] = ai_saved_model.merge_settings(existing.get('Settings'), prepared['Settings'])
        self._request('PUT', '/model/content', model_id=model_id, params={'type': 'extract', 'model_id': model_id}, json=prepared)
        result = {'outcome': 'accepted', 'model_id': model_id, 'submitted_content': prepared}
        return self.wait_for_submission(result, update=True, verify=verify, wait_timeout=wait_timeout, poll_interval=poll_interval) if wait or verify else result

    def inspect(self, model_id):
        """Return safe metadata, not definition content or credential settings."""
        metadata = self._metadata(model_id)
        allowed = ('id', 'name', 'type', 'purpose', 'variant', 'status', 'date_created', 'date_modified')
        safe = {key: metadata[key] for key in allowed if isinstance(metadata.get(key), (str, int, float, bool))}
        return {'outcome': 'success', 'model_id': model_id, 'metadata': safe}

    def export_definition(self, model_id):
        """Return an independent full document suitable for validation/update."""
        metadata = self._metadata(model_id)
        self._require_extract_ai(metadata, model_id)
        return copy.deepcopy(self.read_content(model_id))


    def verify(self, model_id, expected):
        """Read-only comparison against a complete expected authoring document."""
        model_id = _id(model_id)
        prepared = _content(expected, model_id)
        self._require_extract_ai(self._metadata(model_id), model_id)
        comparison = compare_content(prepared, self.read_content(model_id))
        if not comparison['matches']:
            raise ModelOperationError('verification_mismatch', 'Saved content differs from the expected definition.',
                exit_code=6, model_id=model_id, verification='failed', differences=comparison)
        return {'outcome': 'verified', 'model_id': model_id, 'verification': 'passed',
                'readiness': 'not_checked', 'comparison': comparison}

    def wait_for_submission(self, submission, *, update=False, verify=False, wait_timeout=300, poll_interval=2):
        """Poll read-only after acceptance; never repeat the submission.

        Updates cannot claim version-specific readiness without a service version
        correlation contract. Matching readback is reported with that limitation.
        """
        _wait_options(wait_timeout, poll_interval)
        model_id = _id(submission['model_id'])
        expected = submission['submitted_content']
        deadline = time.monotonic() + wait_timeout
        token = _DEADLINE.set(deadline)
        observed_processing = False
        comparison = None
        freshness = {'submission_version': 'unavailable', 'status_transition_observed': False,
                     'readback_matches': False}
        if update:
            freshness['limitation'] = _UPDATE_LIMITATION
        try:
            while True:
                if time.monotonic() >= deadline:
                    raise _deadline_error(model_id)
                metadata = self._metadata(model_id)
                status = metadata.get('status')
                if not isinstance(status, str) or not status.strip():
                    raise ModelOperationError('malformed_status', 'Model metadata has no usable processing status.', model_id=model_id)
                status = status.strip().lower()
                if status in {'failed', 'error'}:
                    raise ModelOperationError('processing_failed', 'Model processing failed.', model_id=model_id, readiness='failed')
                if status == 'ready':
                    freshness['status_transition_observed'] = observed_processing
                    if update or verify:
                        comparison = compare_content(expected, self.read_content(model_id))
                        freshness['readback_matches'] = comparison['matches']
                    if time.monotonic() >= deadline:
                        raise _deadline_error(model_id)
                    if not update or comparison['matches']:
                        readiness = 'unconfirmed' if update else 'ready'
                        if verify and not comparison['matches']:
                            raise ModelOperationError('verification_mismatch', 'Saved content differs from the effective submitted definition.',
                                exit_code=6, model_id=model_id, readiness=readiness, verification='failed', differences=comparison)
                        return {**submission, 'outcome': 'verified' if verify else 'accepted' if update else 'ready',
                                'readiness': readiness, 'verification': 'passed' if verify else 'not_checked',
                                'freshness': freshness}
                    # Old Ready plus old content is not evidence the update ran.
                    # Even a processing transition does not identify its version.
                    if observed_processing and verify:
                        raise ModelOperationError('verification_mismatch', 'Readback after a processing transition differs from the effective submitted definition.',
                            exit_code=6, model_id=model_id, readiness='unconfirmed', verification='failed', differences=comparison)
                elif status in {'processing', 'pending', 'training', 'queued', 'accepted', 'running', 'updating'}:
                    observed_processing = True
                else:
                    raise ModelOperationError('malformed_status', 'The service returned an unsupported processing status.', model_id=model_id)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _deadline_error(model_id)
                time.sleep(min(poll_interval, remaining))
        except ModelOperationError as error:
            error.model_id = model_id
            error.freshness = freshness
            if error.code == 'deadline' and comparison is not None:
                error.differences = comparison
                error.verification = 'pending' if verify else 'not_checked'
            raise
        except KeyboardInterrupt:
            raise ModelOperationError('interrupted', 'Waiting interrupted; the submission may still complete.',
                exit_code=130, model_id=model_id, outcome='interrupted', readiness='unconfirmed', freshness=freshness) from None
        except Exception:
            raise ModelOperationError('unexpected', 'Unexpected wait/readback failure.', exit_code=1, model_id=model_id, readiness='unconfirmed', freshness=freshness) from None
        finally:
            _DEADLINE.reset(token)
