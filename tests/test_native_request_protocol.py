"""Transport conformance with the deployed Native journal; no role examples."""
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from rwkv_lh.runtime.native_state import NATIVE_STATE_PROTOCOL_VERSION, NativeStateCacheBinding
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.protocol import RWKVHTTPError, RWKVOutcomeUnknownError, RuntimeCapabilities
from rwkv_lh.runtime.settings import RuntimeSettings

RECOVERY = 'rwkv-lh.native-request-recovery.v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def binding():
    return NativeStateCacheBinding(lane_id='LANE:ACTION', lane_kind='action', model='opaque-model',
        model_sha256='a' * 64, state_profile_id='zero', state_profile_sha256='0' * 64,
        state_chain_digest='b' * 64, delta_digest='c' * 64, event_ids_digest='d' * 64)


def snapshot():
    return {'state_ref': 'WKV-result', 'state_digest': 'e' * 64,
        'export_record': {'locator': 'opaque-export'}, 'state_format_version': 'opaque-format',
        'server_build': 'opaque-server', 'tokenizer_build': 'opaque-tokenizer',
        'cache_binding_digest': binding().digest, 'protocol_version': NATIVE_STATE_PROTOCOL_VERSION,
        'metadata': {'prompt_token_ids': [0, 1], 'prompt_token_ids_scope': 'full'}}


class Response:
    def __init__(self, value, status=200):
        self.content = json.dumps(value).encode()
        self.text = self.content.decode()
        self.status_code = status
        self.headers = {}


class JournalServer:
    def __init__(self, *, lose_response=False, corrupt=None):
        self.calls = []
        self.records = {}
        self.effects = 0
        self.lose_response = lose_response
        self.corrupt = corrupt

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs.get('json')))
        if method == 'GET':
            parsed = urlparse(url)
            key = parsed.path.rsplit('/', 1)[1]
            record = dict(self.records[key])
            assert parse_qs(parsed.query)['request_digest'] == [record['request_digest']]
            if self.corrupt:
                record.update(self.corrupt)
            return Response(record)
        payload = kwargs['json']
        operation = url.rsplit('/', 1)[1]
        if payload.get('recovery_protocol') != RECOVERY or not payload.get('request_id'):
            return Response({'detail': 'invalid request recovery identity'}, 400)
        request_digest = digest({'operation': operation, 'payload': payload})
        self.effects += 1
        body = snapshot()
        if operation == 'generate':
            body = {'state_ref': 'WKV-candidate', 'state_digest': 'f' * 64, 'content': 'unchanged raw bytes',
                'finish_reason': 'stop', 'parent_state_digest': 'e' * 64,
                'parent_cache_binding_digest': binding().digest, 'metadata': {'token_ids': [1]}}
        self.records[payload['request_id']] = {
            'schema_version': RECOVERY, 'request_id': payload['request_id'], 'operation': operation,
            'request_digest': request_digest, 'status': 'completed', 'http_status': 200,
            'result': body, 'result_sha256': digest(body)}
        if self.lose_response:
            raise requests.ReadTimeout('response lost after durable effect')
        return Response(body)

    def close(self):
        pass


def client(monkeypatch, server):
    monkeypatch.setattr(OpenAICompatibleRWKVClient, '_new_session', lambda self: server)
    return OpenAICompatibleRWKVClient(RuntimeSettings(base_url='http://native.invalid/v1', api_key='',
        model='opaque-model', backend_profile='vllm-rwkv-native', model_sha256='a' * 64,
        state_profile_id='zero', state_profile_sha256='0' * 64,
        read_timeout_seconds=0.05, retry_attempts=3, retry_backoff_seconds=0))


def invoke(runtime, operation):
    args = dict(lane_id='LANE:ACTION', text='opaque transport payload', cache_binding=binding())
    if operation == 'create':
        return runtime.state_create(**args)
    if operation in ('append', 'fork'):
        return getattr(runtime, 'state_' + operation)(parent_state_ref='WKV-parent', **args)
    if operation == 'generate':
        return runtime.state_generate(parent_state_ref='WKV-parent', request_id='MR-durable-id',
            max_tokens=16, stop=['opaque stop'], sampling={'temperature': 0.1},
            parent_cache_binding_digest=binding().digest)
    if operation == 'commit':
        return runtime.state_commit(candidate_state_ref='WKV-candidate', cache_binding=binding())
    if operation == 'rollback':
        return runtime.state_rollback(candidate_state_ref='WKV-candidate', parent_state_ref='WKV-parent')
    if operation == 'import':
        return runtime.state_import(export_record={'locator': 'opaque-export'}, cache_binding=binding())
    raise AssertionError(operation)


def test_native_generation_requests_actual_full_input_token_evidence(monkeypatch):
    server = JournalServer()
    runtime = client(monkeypatch, server)
    from dataclasses import replace
    runtime.settings = replace(runtime.settings, return_token_ids=True)
    assert runtime.settings.return_token_ids is True
    invoke(runtime, 'generate')
    assert server.calls[0][2].get('return_token_ids') is True


@pytest.mark.parametrize('operation', ['create', 'append', 'fork', 'generate', 'commit', 'rollback', 'import'])
@pytest.mark.parametrize('lose_response', [False, True])
def test_all_native_mutations_carry_identity_and_recover_without_resubmission(monkeypatch, operation, lose_response):
    server = JournalServer(lose_response=lose_response)
    result = invoke(client(monkeypatch, server), operation)
    assert server.effects == 1
    assert [method for method, _, _ in server.calls] == (['POST', 'GET'] if lose_response else ['POST'])
    payload = server.calls[0][2]
    if operation == 'generate':
        assert payload['request_id'] == 'MR-durable-id'
        assert result.content == 'unchanged raw bytes'
    else:
        without_id = {key: value for key, value in payload.items() if key != 'request_id'}
        assert payload['request_id'] == 'NR-' + digest({'operation': operation, 'payload': without_id})
    if operation not in ('generate', 'rollback'):
        assert result.metadata['prompt_token_ids'] == [0, 1]


@pytest.mark.parametrize('corrupt', [
    {'request_id': 'different-request'}, {'request_digest': '0' * 64},
    {'operation': 'fork'}, {'result_sha256': '0' * 64}, {'status': 'unknown'},
    {'http_status': True}, {'schema_version': 'future-protocol'},
])
def test_unknown_or_mismatched_recovery_never_submits_another_operation(monkeypatch, corrupt):
    server = JournalServer(lose_response=True, corrupt=corrupt)
    with pytest.raises(RWKVOutcomeUnknownError):
        invoke(client(monkeypatch, server), 'generate')
    assert server.effects == 1
    assert [method for method, _, _ in server.calls] == ['POST', 'GET']


def test_capability_admission_requires_the_current_recovery_protocol():
    state = {key: True for key in ('create', 'resume', 'fork', 'commit', 'rollback', 'export', 'import')}
    state['protocol'] = NATIVE_STATE_PROTOCOL_VERSION
    assert not RuntimeCapabilities.from_mapping({'recurrent_state': state}, source='test').durable_recurrent_state
    state.update(request_recovery=True, request_recovery_protocol=RECOVERY)
    capabilities = RuntimeCapabilities.from_mapping({'recurrent_state': state}, source='test')
    assert capabilities.durable_recurrent_state
    assert capabilities.to_dict()['recurrent_state']['request_recovery_protocol'] == RECOVERY
    state['request_recovery_protocol'] = 'unknown-version'
    assert not RuntimeCapabilities.from_mapping({'recurrent_state': state}, source='test').durable_recurrent_state
