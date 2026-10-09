"""Explicit offline views of real Executor boundaries, using its sole builder.

These are fresh initial-State training episodes, not original Native prompts or
online memory changes. Source snapshots, decisions and receipt bodies stay intact.
"""
from copy import deepcopy
import hashlib
from . import statetune_core as core
from .project_contracts import digest, fields, strings
from .project_ledger import ProjectLedger
from .project_protocols import executor
from .project_runtime import role_definitions
from .project_decoder import available_definitions
from .project_model_io import render_project_bootstrap, render_project_assignment
from .harness import ActionHarness
from .token_budget import tokenizer

WINDOW_SCHEMA = 'rwkv-lh.executor-training-window.v1'


def window_spec(history_rounds, *, required_receipts=()):
    value = {'schema_version': WINDOW_SCHEMA, 'history_rounds': history_rounds,
             'required_receipts': list(required_receipts)}
    return validate_spec(value)


def validate_spec(value):
    fields(value, ('schema_version', 'history_rounds', 'required_receipts'))
    core.require(value['schema_version'] == WINDOW_SCHEMA, 'unknown Executor training window')
    core.require(type(value['history_rounds']) is int and value['history_rounds'] > 0,
                 'positive confirmed tool receipt window required')
    strings(value['required_receipts'])
    return deepcopy(value)


def _boundary_state(source, operation):
    found = []
    row = source['replayed'][operation]['row']
    def capture(event):
        pending = event['state']['pending']
        if event['kind'] == 'operation_started' and pending and pending['id'] == operation:
            core.require(pending['kind'] == 'model' and pending['payload']['role'] == 'executor'
                         and event['digest'] == row['source_event_digest']
                         and pending['payload']['input'] == row['input'], 'window boundary differs from actual model input')
            found.append(deepcopy(event['state']))
    with ProjectLedger.read_snapshot(source['ledger'].root) as ledger:
        ledger.scan_verified_events(capture)
    core.require(len(found) == 1, 'one original Executor boundary required')
    return found[0]


def materialize(source, operation, specification):
    """Internal: the caller must first load/reverify the original source seal."""
    spec = validate_spec(specification)
    core.require(source['registered']['split'] == 'train', 'only train sources may have derived windows')
    core.require(operation in source['replayed'], 'original source operation required')
    original = source['replayed'][operation]
    state = _boundary_state(source, operation)
    lane = state['active']['id']
    original_payload = executor.build_input(state['active'], project_state=state,
        remaining=original['row']['input']['remaining'])
    core.require(original_payload == original['row']['input'], 'original builder replay differs')
    allowed = original_payload['references']['read_receipt']['receipt_id']
    core.require(set(spec['required_receipts']) <= set(allowed), 'required receipt was not visible at this boundary')
    recent = allowed[-spec['history_rounds']:]
    selected = [key for key in allowed if key in set(recent) | set(spec['required_receipts'])]
    # Only delivery cursors change. The production builder still determines all
    # goals, authority, references, feedback and exact raw receipt bodies.
    delivery = state['input_delivery'].setdefault(lane, {})
    delivery['observations'] = [key for key in allowed if key not in selected]
    delivery['evidence'] = {key: value['revision'] for key, value in state['selected_evidence'].get(lane, {}).items()
                            if key not in selected}
    payload = executor.build_input(state['active'], project_state=state, remaining=original_payload['remaining'])
    executor.validate_input(payload)
    core.require(set(payload['evidence_updates']) == set(selected)
                 and all(payload[key] == original_payload[key]
                         for key in payload.keys() - {'evidence_updates', 'observations'}),
                 'window changed facts beyond explicit receipt delivery')
    definitions = available_definitions(role_definitions('executor', ActionHarness()), role='executor', payload=payload)
    text = render_project_bootstrap(definitions, render_project_assignment(payload))
    ids = [0, *tokenizer().encode(text)]
    proof = {'policy': spec, 'source_event_digest': original['row']['source_event_digest'],
        'original_payload_digest': digest(original_payload),
        'original_input_tokens_sha256': digest(original['input_token_ids']),
        'original_input_tokens': len(original['input_token_ids']),
        'view_input_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'view_input_tokens_sha256': digest(ids), 'view_input_digest': digest(payload),
        'included_receipts': selected, 'recent_receipts': recent,
        'additional_required_receipts': [key for key in selected if key not in recent],
        'omitted_receipt_bodies': [key for key in allowed if key not in selected],
        'initialization': 'trainable_initial_state_at_window_start',
        'original_native_input': False,
        'materializer_sha256': core.sha256_file(__file__)}
    return {**original, 'input_text': text, 'input_token_ids': ids,
            'row': {**original['row'], 'input': payload}}, proof


def validate_row_view(row):
    """Shape/content checks; formal admission re-materializes sealed sources."""
    spec = validate_spec(row['input_view'])
    proof = row['input_view_proof']
    core.require(row.get('split') == 'train' and row.get('server_input_verified') is False
                 and row.get('source_server_input_verified') is True
                 and row.get('derived_input_verified') is True,
                 'derived window cannot claim the original server input')
    core.require(proof['policy'] == spec and proof['source_event_digest'] == row['source_event_digest']
                 and proof['view_input_digest'] == digest(row['input'])
                 and proof['view_input_tokens_sha256'] == digest(row['input_token_ids'])
                 and proof['view_input_sha256'] == hashlib.sha256(row['input_text'].encode()).hexdigest()
                 and proof['materializer_sha256'] == core.sha256_file(__file__)
                 and proof['original_native_input'] is False
                 and proof['initialization'] == 'trainable_initial_state_at_window_start',
                 'derived window proof differs')
    # JSON object key order is not receipt chronology. Dataset freezing sorts
    # object keys; chronology remains in the builder's explicit reference list.
    included = proof['included_receipts']
    chronological = [key for key in row['input']['references']['read_receipt']['receipt_id'] if key in included]
    core.require(included == chronological and set(included) == set(row['input']['evidence_updates'])
                 and set(spec['required_receipts']) <= set(proof['included_receipts']),
                 'window receipt closure differs')
