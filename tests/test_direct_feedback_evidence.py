"""Public freeze evidence gate: production command projection, no model requests."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwkv_lh import model_io
from rwkv_lh.observation_funnel import project_action_result
from test_unified_controller import call


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def freeze_answer(tmp_path, monkeypatch):
    from rwkv_lh import direct_trace_data as module
    from rwkv_lh.statetune_data import FREEZE_SCHEMA

    # Isolate this evidence gate; token/review/native-replay admission have their
    # own end-to-end regressions and are deliberately not replaced in production.
    monkeypatch.setattr(module, 'normalize_direct_row', lambda *a, **k: None)
    states = {}
    actual = {'input_token_ids': [0, 1], 'input_text': 'fixture',
              'input_checkpoint_id': 'after', 'request_id': 'request'}
    monkeypatch.setattr(module, 'replay_run', lambda *a: {'candidate': actual})
    monkeypatch.setattr(module, 'RunState', SimpleNamespace(from_dict=lambda x: states['state']))
    root = tmp_path / 'source'
    root.mkdir()
    for name in ('RESULT.json', 'model_trace.jsonl', 'state_snapshot.json'):
        (root / name).write_text('{}')

    def seal(name, value):
        p = tmp_path / name
        p.write_text(json.dumps(value))
        return {'path': str(p), 'sha256': digest(p.read_text())}

    authorization = seal('authorization.json', {'scope': 'test fixture only'})
    manifest = seal('source.json', {
        'source_type': 'native_production_trace', 'model_sha256': 'a' * 64,
        'collector_source_manifest_sha256': 'b' * 64, 'server_identity_sha256': 'c' * 64,
        'files': {p.name: digest(p.read_text()) for p in root.iterdir()},
    })
    cases = []
    for split, text in [('dev', 'distinct development material'), ('confirmation', 'other confirmation material')]:
        reference = tmp_path / (split + '.txt')
        reference.write_text(text)
        cases.append({'id': split, 'split': split, 'family': split,
                      'source_content_sha256': digest(text),
                      'content_reference': {'path': str(reference), 'sha256': digest(text)}})
    regression = seal('regression.json', {'cases': cases})

    def run(projected, text, *, future=False):
        current = 'before' if future else 'after'
        actual['input_checkpoint_id'] = current
        states['state'] = SimpleNamespace(
            model_states={
                'before': SimpleNamespace(event_ids=[], parent_checkpoint_id=None),
                'after': SimpleNamespace(event_ids=['observation'], parent_checkpoint_id='before'),
            },
            model_events={'observation': SimpleNamespace(payload={'result': projected})},
        )
        content = tmp_path / 'content.txt'
        content.write_text(text)
        source = {'id': 'source', 'source_id': 'source', 'family': 'fixture',
                  'split': 'train', 'run_root': str(root), 'manifest': manifest,
                  'source_content_sha256': digest(text),
                  'content_reference': {'path': str(content), 'sha256': digest(text)}}
        row = {**actual, 'sample_id': 'sample', 'candidate_checkpoint_id': 'candidate',
               'source_id': 'source', 'family': 'fixture',
               'source_manifest_sha256': manifest['sha256'],
               'source_content_sha256': digest(text), 'label_authority': 'independent_review',
               'target_text': json.dumps(call('final_answer', text='Report actual result'))
               + model_io.JSON_CALL_STOP_SUFFIXES[0]}
        similarity = module.audit_source_similarity([source, *cases], threshold=.95)
        registration = {
            'schema_version': FREEZE_SCHEMA, 'role': module.ROLE,
            'authorization': authorization, 'reviewed_rows': seal('rows.json', {'rows': [row]}),
            'regression_registration': regression, 'regression_fingerprint': regression['sha256'],
            'sources': [source], 'similarity_threshold': .95,
            'similarity_audit': seal('similarity.json', similarity), 'model_sha256': 'a' * 64,
            'context_tokens': 8192, 'vocab_size': 65536, 'bos_token_id': 0,
            'minimum_counts': {'train': 1, 'dev': 1, 'confirmation': 1},
            'minimum_coverage': {'source_files': 1, 'families': 1, 'read_boundaries': 0,
                                 'summary_boundaries': 1},
        }
        return module.freeze_direct_dataset(registration, registration_reference=seal('registration.json', registration),
                                            output=tmp_path / 'frozen')
    return run


def command_observation(*, failed=False, operation='check_command'):
    stdout, stderr = ('', 'AssertionError: expected 2, got 1\n') if failed else ('{"passed":true}\n', '')
    raw = {'action_type': operation, 'success': not failed, 'exit_code': int(failed),
           'output': stdout + stderr,
           'metadata': {'command_streams': {'stdout': stdout, 'stderr': stderr}}}
    return project_action_result(raw, operation=operation), stderr if failed else stdout


@pytest.mark.parametrize('operation', ['check_command', 'run_command'])
@pytest.mark.parametrize('failed', [False, True])
def test_final_label_can_use_complete_visible_command_stream(freeze_answer, operation, failed):
    projected, content = command_observation(failed=failed, operation=operation)
    manifest = freeze_answer(projected, content)
    assert manifest['counts']['train'] == 1


@pytest.mark.parametrize('problem', ['future', 'partial', 'partial_stream', 'wrong_hash', 'wrong_span', 'gap', 'wrong_adapter', 'mixed_streams'])
def test_final_label_rejects_unseen_or_unproven_command_content(freeze_answer, problem):
    projected, content = command_observation()
    projected = copy.deepcopy(projected)
    stream = projected['command_streams'][0]
    if problem == 'partial':
        stream['projection_complete'] = False
        projected['observation']['projection_complete'] = False
    if problem == 'partial_stream':
        stream['projection_complete'] = False
    if problem == 'wrong_hash':
        stream['stream_sha256'] = 'f' * 64
    if problem == 'wrong_span':
        stream['exact_spans'][0]['content_sha256'] = 'f' * 64
    if problem == 'gap':
        stream['exact_spans'][0]['start_byte'] = 1
    if problem == 'wrong_adapter':
        projected['observation']['adapter'] = 'unregistered'
    if problem == 'mixed_streams':
        stream['stream'] = 'combined'
    with pytest.raises(ValueError):
        freeze_answer(projected, content, future=problem == 'future')


@pytest.mark.parametrize('content', ['文件中的信息\n', ''])
def test_existing_complete_file_and_empty_file_evidence_still_freezes(freeze_answer, content):
    projected = project_action_result({'action_type': 'read_file', 'success': True,
                                      'output': content, 'metadata': {}}, operation='read_file')
    assert freeze_answer(projected, content)['counts']['train'] == 1


def test_combined_unicode_command_output_uses_utf8_byte_boundaries(freeze_answer):
    content = '测试未通过：期望两个结果，实际一个。\n'
    projected = project_action_result({'action_type': 'check_command', 'success': False,
                                      'exit_code': 1, 'output': content, 'metadata': {}},
                                     operation='check_command')
    assert freeze_answer(projected, content)['counts']['train'] == 1
