"""Exact recorded prefixes evaluated through the production Native decoder contract."""
from copy import deepcopy
import time

from .native_state import (EXACT_TOKEN_INPUT_PROTOCOL, NATIVE_STATE_PROTOCOL_VERSION,
                          NATIVE_STATE_LIFECYCLE_VERSION, NativeStateCacheBinding)
from .native_request_protocol import native_result_digest
from .protocol import CompletionResponse, RWKVProtocolError, RWKVOutcomeUnknownError
from .structured_output import validate_decoder_contract, decoder_receipt, state_output_token_ids


def constrained_token_completion(client, request, decoder, *, record):
    validate_decoder_contract(decoder)
    if request.stop or request.stop_token_ids or request.min_tokens or request.prompt[:1] != [0]:
        raise ValueError('constrained exact prefix requires original BOS and grammar-controlled termination')
    identity = native_result_digest({'request_id': request.request_id})
    prefix_digest = native_result_digest({'input_token_ids': request.prompt})
    binding = NativeStateCacheBinding(lane_id='role-evaluation-' + identity, lane_kind='action',
        model=client.model_name, model_sha256=client.settings.model_sha256,
        state_profile_id=client.settings.state_profile_id, state_profile_sha256=client.settings.state_profile_sha256,
        state_chain_digest=native_result_digest({'input': prefix_digest, 'decoder': decoder['contract_sha256']}),
        delta_digest=prefix_digest, event_ids_digest=identity)
    record({'type': 'runtime_token_request_started', 'request_id': request.request_id,
        'input_token_protocol': EXACT_TOKEN_INPUT_PROTOCOL, 'prompt_token_ids': list(request.prompt),
        'decoder': deepcopy(decoder), 'binding': binding.to_dict(), 'max_tokens': request.max_tokens})
    capabilities, _, _ = client._request_json('GET', '/capabilities')
    record({'type': 'runtime_token_capabilities', 'request_id': request.request_id, 'raw_response': capabilities})
    advertised = capabilities.get('structured_output', {})
    if (capabilities.get('model') != client.model_name
            or capabilities.get('recurrent_state', {}).get('exact_token_input_protocol') != EXACT_TOKEN_INPUT_PROTOCOL
            or advertised.get('protocol') != decoder['protocol'] or advertised.get('backend') != decoder['backend']
            or not advertised.get('source_identity')):
        raise RWKVProtocolError('service did not attest exact Native token input and decoder identity')

    last_operation = None
    def native(operation, payload):
        nonlocal last_operation
        last_operation = operation
        record({'type': 'runtime_token_native_request', 'request_id': request.request_id,
                'operation': operation, 'payload': deepcopy(payload)})
        result = client._native_request(operation, payload)
        record({'type': 'runtime_token_native_response', 'request_id': request.request_id,
                'operation': operation, 'raw_response': deepcopy(result)})
        return result

    started = time.perf_counter()
    try:
        created = native('create', client._native_payload(binding, lane_id=binding.lane_id,
            request_id='EVALCREATE-' + identity, input_token_protocol=EXACT_TOKEN_INPUT_PROTOCOL,
            input_token_ids=list(request.prompt), input_bos_token_count=1))
        try:
            parent = client._native_snapshot(created, expected_binding=binding)
        except (KeyError, TypeError, ValueError) as exc:
            raise RWKVProtocolError('invalid exact token prefill snapshot') from exc
        if (parent.metadata.get('prompt_token_ids') != request.prompt
                or parent.metadata.get('prompt_token_ids_scope') != 'full_context'
                or parent.server_build != capabilities.get('server_build')
                or parent.metadata.get('input_bos_token_count') != 1):
            raise RWKVProtocolError('exact token prefill echo differs from original prefix')
        sampling = {name: getattr(request, name) for name in ('temperature', 'top_p', 'top_k',
            'presence_penalty', 'frequency_penalty', 'penalty_decay', 'seed')}
        returned = native('generate', client._attach_state_profile({
            'schema_version': NATIVE_STATE_PROTOCOL_VERSION, 'model': client.model_name,
            'parent_state_ref': parent.state_ref, 'parent_cache_binding_digest': binding.digest,
            'request_id': request.request_id, 'max_tokens': request.max_tokens, 'stop': [],
            'sampling': sampling, 'return_token_ids': True, 'decoder': deepcopy(decoder)}))
        candidate = returned.get('candidate', {})
        metadata = candidate.get('metadata', {})
        if (candidate.get('parent_state_digest') != parent.state_digest
                or candidate.get('parent_cache_binding_digest') != binding.digest
                or metadata.get('prompt_token_ids') != request.prompt or metadata.get('input_bos_token_count') != 1
                or metadata.get('prompt_token_ids_scope') != 'full_context'
                or metadata.get('decoder') != decoder_receipt(decoder)
                or metadata.get('response_id') != request.request_id):
            raise RWKVProtocolError('exact token generation parent, prefix or decoder attestation differs')
        try:
            state_ids = state_output_token_ids(metadata.get('token_ids'), candidate.get('finish_reason'), decoder)
        except ValueError as exc:
            raise RWKVProtocolError('invalid exact token generation EOS boundary') from exc
        if metadata.get('state_token_ids') != state_ids or len(metadata['token_ids']) > request.max_tokens:
            raise RWKVProtocolError('exact token State consumption or output budget differs')
        if not isinstance(candidate.get('content'), str) or candidate.get('finish_reason') not in ('stop', 'length'):
            raise RWKVProtocolError('invalid exact token response content or finish reason')
        record({'type': 'runtime_token_response', 'request_id': request.request_id,
                'raw_response': deepcopy(returned), 'decoder': decoder_receipt(decoder)})
        rollback = native('rollback', {'schema_version': NATIVE_STATE_PROTOCOL_VERSION, 'model': client.model_name,
            'candidate_state_ref': candidate['state_ref'], 'parent_state_ref': parent.state_ref})
        if rollback.get('rolled_back') is not True or rollback.get('parent_state_ref') != parent.state_ref:
            raise RWKVProtocolError('exact token cleanup rollback receipt differs from the parent')
        released = native('release', {'schema_version': NATIVE_STATE_PROTOCOL_VERSION, 'model': client.model_name,
            'lifecycle_protocol': NATIVE_STATE_LIFECYCLE_VERSION,
            'states': [{'state_ref': parent.state_ref, 'state_digest': parent.state_digest,
                        'cache_binding_digest': parent.cache_binding_digest}],
            'release_import_aliases': False})
        if released.get('released_state_refs') != [parent.state_ref]:
            raise RWKVProtocolError('exact token cleanup release receipt differs from the parent')
        return CompletionResponse(content=candidate['content'], finish_reason=candidate['finish_reason'],
            model=client.model_name, response_id=request.request_id,
            latency_ms=(time.perf_counter() - started) * 1000, metadata=deepcopy(metadata))
    except RWKVOutcomeUnknownError:
        record({'type': 'runtime_token_request_unknown', 'request_id': request.request_id,
                'unknown_operation': last_operation,
                'parent_preserved': True if last_operation in ('generate', 'rollback') else None,
                'known_response_persisted': last_operation in ('rollback', 'release')})
        raise
