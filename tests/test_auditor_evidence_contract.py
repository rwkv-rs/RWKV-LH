"""Production evidence contradictions, using public test fixtures only."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from rwkv_lh.goal_loop_protocol import GoalPlanStep
from rwkv_lh.goal_state_protocols import auditor_step_v6 as step_protocol, auditor_final
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.schema import ActionRecord
from rwkv_lh.role_trace_labels import validate_role_target


def _source(*, root='.', operation='list_directory', observed_root=None,
            complete=True, truncated=False, succeeded=True, projection_complete=True):
    mutate = operation == 'write_file'
    step = GoalPlanStep(step_id='S1', objective='Inspect or update the assigned resource',
        phase='mutate' if mutate else 'observe',
        read_roots=() if mutate else (root,), write_roots=(root,) if mutate else (),
        success_evidence=('The recorded result meets the requested resource condition.',)).to_dict()
    path = root if observed_root is None else observed_root
    if mutate and path == '.':
        path = 'written.txt'
    output = json.dumps({'path': path, 'recursive': False, 'entries': [], 'entry_count': 0,
                         'truncated': truncated, 'next_cursor': ''}) if operation == 'list_directory' else ''
    action = ActionRecord.from_dict(dict(action_id='A1', sequence=1,
        status='succeeded' if succeeded else 'failed', action_type=operation,
        arguments={'path': path},
        result={'success': succeeded, 'action_type': operation, 'output': output,
                'metadata': {'complete': complete, 'truncated': truncated}},))
    state = SimpleNamespace(actions={'A1': action}, artifacts={}, artifact_revisions={},
                            goal=SimpleNamespace(request='Inspect the assigned resource.'))
    records = LongHorizonModel._audit_evidence_records(state, ['A1'])
    if not projection_complete:
        records[0]['action']['result']['observation']['projection_complete'] = False
    return step_protocol.build_prompt_source(immutable_goal='Complete the requested observation or mutation', boundary='mutation_transaction_complete' if mutate else 'observation_complete',
        active_step=step, available_evidence_refs=['A1'], evidence_records=records)


def _repair(source, gap):
    return dict(verdict='repair', step_id=source['active_step']['step_id'], step_complete=False,
        evidence_refs=['A1'], gaps=[gap], reason=step_protocol.REASON_INCOMPLETE)


@pytest.mark.parametrize('root', ['.', 'nested/source', '资源/子目录'])
@pytest.mark.parametrize('operation', ['list_directory', 'write_file'])
def test_proved_scope_is_not_offered_as_a_missing_fact(root, operation):
    source = _source(root=root, operation=operation)
    prefix = 'write_root_unproved' if operation == 'write_file' else 'read_root_unproved'
    assert f'{prefix}:{root}' not in {item['code'] for item in source['gap_catalog']}


@pytest.mark.parametrize('operation', ['list_directory', 'write_file'])
def test_production_and_data_reject_the_same_contradictory_gap(operation):
    source = _source(operation=operation)
    prefix = 'write_root_unproved' if operation == 'write_file' else 'read_root_unproved'
    decision = _repair(source, prefix + ':.')
    with pytest.raises(ValueError, match='contradict'):
        step_protocol.validate_source({**source, 'decision': decision, 'completion_verifier_id': 'TEST'})
    rebuilt = dict(protocol_version=step_protocol.INPUT_SCHEMA_VERSION, prompt_source=source)
    with pytest.raises(ValueError, match='contradict'):
        validate_role_target('auditor_step', rebuilt, ModelCommand('audit_decision', decision).canonical,
                             verifier_id='TEST')


@pytest.mark.parametrize('changes', [
    {'complete': False}, {'truncated': True}, {'succeeded': False},
    {'observed_root': 'other'}, {'operation': 'check_command'},
    {'complete': None}, {'projection_complete': False},
])
def test_unproved_or_incomplete_observation_remains_a_possible_gap(changes):
    source = _source(root='assigned', **changes)
    decision = _repair(source, 'read_root_unproved:assigned')
    step_protocol.validate_source({**source, 'decision': decision, 'completion_verifier_id': 'TEST'})
    assert 'read_root_unproved:assigned' in {item['code'] for item in source['gap_catalog']}
    rebuilt = dict(protocol_version=step_protocol.INPUT_SCHEMA_VERSION, prompt_source=source)
    target = ModelCommand('audit_decision', decision).canonical
    assert validate_role_target('auditor_step', rebuilt, target, verifier_id='TEST') == target


def test_proved_mechanics_do_not_complete_the_semantic_step():
    source = _source()
    gap = next(item['code'] for item in source['gap_catalog'] if item['code'].startswith('success_criterion_unproved:'))
    decision = _repair(source, gap)
    step_protocol.validate_source({**source, 'decision': decision, 'completion_verifier_id': 'TEST'})
    assert decision['verdict'] == 'repair' and not decision['step_complete']


@pytest.mark.parametrize('role', ['auditor_step', 'auditor_final'])
def test_catalog_is_explicitly_presented_as_conditions_not_findings(role):
    source = _source(complete=False)
    protocol = step_protocol
    if role == 'auditor_final':
        protocol = auditor_final
        source = protocol.build_prompt_source(immutable_goal='Report the observation',
            completed_steps=[{'step_id': 'S1', 'evidence_refs': ['A1']}],
            available_evidence_refs=['A1'], evidence_records=source['evidence_records'],
            final_candidate={'function': 'final_answer', 'params': {'text': 'Observed.'}})
    payload = json.loads(protocol.render_prompt(source).removeprefix(protocol.PROMPT_PREFIX))
    assert payload['catalog_semantics'] == 'possible_unmet_conditions'
    assert 'lacks a successful complete observation' not in protocol.render_prompt(source)
    assert 'The final candidate omits a result' not in protocol.render_prompt(source)
    assert 'The final candidate contains a claim not supported' not in protocol.render_prompt(source)
