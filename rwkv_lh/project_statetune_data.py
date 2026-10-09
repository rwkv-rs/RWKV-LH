"""Shared validation for current production Executor training rows."""
import json
from . import statetune_core as core
from .project_contracts import digest
from .project_protocols import executor
from .project_output_validation import validate_role_output
from .project_runtime import role_definitions
from .model_io import JSON_CALL_STOP_SUFFIXES
from .harness import ActionHarness
from .token_budget import tokenizer, VOCAB_PATH

def _normalize_project_row(row, *, role, row_schema, protocol, model_sha256, context_tokens,
                           vocab_size, bos_token_id, expected_split):
    core.require(expected_split in {'train', 'dev', 'confirmation'}, 'unknown registered split')
    core.require(row.get('input_digest') == digest(row.get('input')), 'project payload digest differs')
    core.require(row.get('schema_version') == row_schema and row.get('role') == role
                 and row.get('split') == expected_split and row.get('recomputed') is True,
                 'current recomputed project row and registered split required')
    core.require((row.get('input_protocol'), row.get('protocol_sha256')) == protocol,
                 'project training protocol differs')
    core.require(role == 'project_executor', 'only current Executor rows are supported')
    executor.validate_input(row['input'])
    # Shape validation is not provenance. Formal admission re-extracts the
    # original ledger through the same production builder and exact Native replay.
    core.require(row.get('model_sha256') == model_sha256
                 and row.get('tokenizer_sha256') == core.sha256_file(VOCAB_PATH), 'model/tokenizer differs')
    source, target = row.get('input_token_ids'), row.get('target_token_ids')
    core.require(all(isinstance(ids, list) and ids and all(type(t) is int and 0 <= t < vocab_size for t in ids)
                     for ids in (source, target)), 'invalid project token IDs')
    core.require(source[:1] == [bos_token_id] and row.get('server_input_verified') is True,
                 'full server input with true BOS required')
    core.require(len(source) + len(target) - 1 <= context_tokens, 'executor source exceeds context; no truncation')
    try:
        input_text = tokenizer().decode_bytes(source[1:]).decode('utf-8')
        target_text = tokenizer().decode_bytes(target).decode('utf-8')
    except (KeyError, UnicodeError) as exc:
        raise ValueError('invalid decodable project tokens') from exc
    core.require(input_text == row.get('input_text') and target_text == row.get('target_text'),
                 'project token/text mismatch')
    core.require(row.get('loss_mask') == [0] * len(source) + [1] * len(target), 'target-only mask differs')
    core.require(row.get('target_text', '').endswith(JSON_CALL_STOP_SUFFIXES[0]), 'production stop required')
    text = row['target_text'][:-len(JSON_CALL_STOP_SUFFIXES[0])]
    wire = json.loads(text)
    core.require(set(wire) == {'function', 'params'}, 'exact training call envelope required')
    from .project_model_io import parse_role_call
    native_role = 'executor'
    command, _ = parse_role_call(text, role=native_role, payload=row['input'])
    validate_role_output(native_role, row['input'], command, role_definitions(native_role, ActionHarness()))
    core.require(row.get('review', {}).get('verdict') == 'accept'
                 and row['review'].get('issues') == [] and row.get('review_sha256') == digest(row['review']),
                 'accepted independently recorded review required')
    core.require(row.get('source_purpose') == 'production_training_source' and row.get('source_group')
                 and row.get('source_event_digest') and row.get('source_registration_sha256')
                 and row.get('source_ledger_sha256') and row.get('sample_id'), 'project production provenance missing')
    return {'sample_id': row['sample_id'], 'input_token_ids': list(source), 'target_token_ids': list(target)}
