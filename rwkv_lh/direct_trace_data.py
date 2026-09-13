"""StateTune admission for the existing direct actor; never constructs a new protocol.

Only frozen production inputs are replayed through the production renderers.
The optimizer receives train rows; source families and evaluation stay isolated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from rwkv_lh import model_io, statetune_core as core
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import RunState
from rwkv_lh.token_budget import VOCAB_PATH, tokenizer

ROW_SCHEMA = "rwkv-lh.statetune-direct-row.v1"
ROLE = "direct_actor"


def protocol_identity() -> tuple[str, str]:
    return model_io.MODEL_COMMAND_NORMALIZER_VERSION, core.sha256_file(model_io.__file__)


def executed_arguments(command) -> dict:
    """Replay the existing tool contract; never change the raw training target."""
    from rwkv_lh.schema import TaskAction
    return dict(ActionHarness().normalize_action(TaskAction(command.name, command.arguments)).arguments)


def validate_split_isolation(records: Sequence[Mapping]) -> None:
    families, contents = {}, {}
    for row in records:
        split = row['split']
        core.require(split in {'train', 'dev', 'confirmation'}, 'unknown split')
        for mapping, key, label in ((families, row['family'], 'family'),
                                    (contents, row['source_content_sha256'], 'content')):
            core.require(bool(key), 'missing source ' + label)
            core.require(key not in mapping or mapping[key] == split, 'cross-split ' + label)
            mapping[key] = split


def replay_run(run_root: Path, model_sha256: str) -> dict[str, dict]:
    """Rebuild every generation input using production bootstrap/event renderers.

    The caller seals all source files first. Workspace must still match its
    frozen read-only snapshot. No inference, fabricated tool result, or target
    construction occurs here.
    """
    state = RunState.from_dict(json.loads((run_root / 'state_snapshot.json').read_text()))
    events = [json.loads(line) for line in (run_root / 'model_trace.jsonl').read_text().splitlines()]
    returned = [e for e in events if e['type'] == 'model_session_generation_returned']
    starts = {e['request_id']: e for e in events if e['type'] == 'model_session_generation_started'}
    generations = {e['candidate_checkpoint_id']: e['raw_generation'] for e in returned}
    core.require(len(generations) == len(returned) > 0, 'missing/duplicate generation identity')
    # Explicit inert transport: these objects are used only to render input.
    session = ModelSession(client=object(), settings=RuntimeSettings(base_url='http://unused.invalid', api_key='', model='replay-only', tool_disclosure_mode='full'))
    model = LongHorizonModel(session, harness=ActionHarness())
    replay_goal = model.create_literal_goal(state.goal.request, str(run_root / 'workspace'),
                                                constraints=state.goal.constraints, runtime_policy=state.goal.runtime_policy)
    initial = RunState(run_id=state.run_id, goal=replay_goal)
    bootstrap = model_io.render_bootstrap(model.direct_definitions(), model._assignment(initial, recent_limit=None))
    rows = {}
    for e in returned:
        raw = e['raw_generation']
        start = starts[e['request_id']]
        parent = state.model_states[start['input_checkpoint_id']]
        chain = []
        current = parent
        visited = set()
        while current is not None:
            core.require(current.checkpoint_id not in visited, 'cyclic State ancestry')
            visited.add(current.checkpoint_id)
            chain.append(current)
            metadata = current.native_state_metadata
            core.require(metadata.get('model_sha256') == model_sha256, 'source model identity differs')
            core.require(current.state_profile_id == 'zero' and current.state_profile_sha256 == '0'*64,
                         'this initial direct dataset requires zero production traces')
            previous = state.model_states.get(current.parent_checkpoint_id)
            if previous:
                core.require(metadata.get('cache_binding', {}).get('parent_state_digest') == previous.native_state_digest,
                             'native parent digest differs')
            current = previous
        core.require(chain[-1].transcript == bootstrap, 'production bootstrap replay differs')
        ids = []
        used_events = set()
        for cp in reversed(chain):
            if cp.checkpoint_id in generations:
                ids.extend(generations[cp.checkpoint_id]['raw_token_ids'])
            elif cp.parent_checkpoint_id:
                parent_events = state.model_states[cp.parent_checkpoint_id].event_ids
                delta_events = [event_id for event_id in cp.event_ids if event_id not in parent_events]
                core.require(len(delta_events) == 1, 'non-generation checkpoint needs one new real event')
                event_id = delta_events[0]
                core.require(event_id not in used_events and event_id in state.model_events, 'missing/repeated observation')
                used_events.add(event_id)
                expected = model_io.render_event_append(state.model_events[event_id],
                    previous_transcript=state.model_states[cp.parent_checkpoint_id].transcript)
                core.require(expected == cp.transcript, 'production observation replay differs')
                ids.extend(tokenizer().encode(expected))
            else:
                ids.extend(tokenizer().encode(bootstrap))
        bos_count = raw['input_bos_token_count']
        core.require(bos_count == 1 and raw['prompt_token_ids'][:1] == [0]
                     and raw['prompt_token_ids'][1:] == ids, 'full server input token replay differs')
        core.require(start['input_digest'] == parent.native_state_digest, 'generation did not use registered parent')
        rows[e['candidate_checkpoint_id']] = {
            'input_token_ids': list(raw['prompt_token_ids']), 'input_text': tokenizer().decode(ids),
            'input_checkpoint_id': parent.checkpoint_id, 'candidate_checkpoint_id': e['candidate_checkpoint_id'],
            'request_id': e['request_id'], 'raw_generation': raw,
            'source_model_sha256': model_sha256, 'recomputed': True,
        }
    return rows


def normalize_direct_row(row: Mapping, *, model_sha256: str, context_tokens: int,
                         vocab_size: int, bos_token_id: int, expected_split: str = 'train') -> dict:
    core.require(row.get('schema_version') == ROW_SCHEMA and row.get('recomputed') is True,
                 'recomputed direct production row required')
    core.require(row.get('role') == ROLE and row.get('split') == expected_split, 'direct role/split differs')
    core.require((row.get('input_protocol'), row.get('protocol_sha256')) == protocol_identity(), 'direct protocol differs')
    core.require(row.get('model_sha256') == model_sha256
                 and row.get('tokenizer_sha256') == core.sha256_file(VOCAB_PATH), 'direct model/tokenizer differs')
    source, target = row.get('input_token_ids'), row.get('target_token_ids')
    core.require(all(isinstance(ids, list) and ids and all(type(t) is int and 0 <= t < vocab_size for t in ids)
                     for ids in (source, target)), 'invalid direct token IDs')
    core.require(source[:1] == [bos_token_id] and row.get('input_token_source') == 'server_returned_full',
                 'complete server input including BOS required')
    core.require(tokenizer().decode(source[1:]) == row.get('input_text')
                 and tokenizer().decode(target) == row.get('target_text'), 'direct token/text mismatch')
    core.require(len(source) + len(target) - 1 <= context_tokens, 'direct sample exceeds context; no truncation')
    for key in ('sample_id', 'input_checkpoint_id', 'request_id', 'source_manifest_sha256', 'source_content_sha256', 'family'):
        core.require(bool(row.get(key)), 'direct row lacks ' + key)
    raw_target = row['target_text']
    core.require(raw_target.endswith(model_io.JSON_CALL_STOP_SUFFIXES[0]), 'direct target needs exact production stop')
    command_text = raw_target[:-len(model_io.JSON_CALL_STOP_SUFFIXES[0])]
    json.loads(command_text)  # No transport repair or first-object extraction for training targets.
    command = model_io.parse_model_command(command_text)
    authority = row.get('label_authority')
    if authority == 'executed_read':
        core.require(command.name == 'read_file' and row.get('executed_action_id')
                     and row.get('real_tool_success') is True, 'read label lacks execution proof')
    elif authority == 'independent_review':
        target_sha = hashlib.sha256(raw_target.encode()).hexdigest()
        reviewers = row.get('reviews', [])
        core.require(command.name == 'final_answer' and set(command.arguments) == {'text'}
                     and isinstance(command.arguments['text'], str) and bool(command.arguments['text'].strip()) and len({r.get('reviewer') for r in reviewers}) >= 2
                     and all(isinstance(r.get('reviewer'), str) and bool(r['reviewer'].strip()) and r.get('accepted') is True and r.get('target_sha256') == target_sha
                             and r.get('input_sha256') == hashlib.sha256(row['input_text'].encode()).hexdigest()
                             and r.get('visible_evidence_only') is True for r in reviewers),
                     'summary label lacks two source-bound independent reviews')
    else:
        raise ValueError('unsupported direct label authority')
    return {'sample_id': row['sample_id'], 'input_token_ids': list(source), 'target_token_ids': list(target)}


def freeze_direct_dataset(registration: Mapping, *, registration_reference: Mapping, output: Path) -> dict:
    """Publish only reviewed rows rechecked against sealed native production traces."""
    from rwkv_lh.statetune_data import sealed, FREEZE_SCHEMA, DATASET_SCHEMA
    from rwkv_lh.role_trace_artifacts import _canonical_bytes, _publish_no_replace
    import shutil
    import tempfile

    core.require(registration.get('schema_version') == FREEZE_SCHEMA and registration.get('role') == ROLE,
                 'direct freeze registration differs')
    core.verify_file(**{'path': registration['authorization']['path'],
                       'expected_sha256': registration['authorization']['sha256']})
    rows = sealed(registration['reviewed_rows'])['rows']
    regression = sealed(registration['regression_registration'])
    fingerprint = registration['regression_registration']['sha256']
    core.require(fingerprint == registration['regression_fingerprint'], 'direct regression fingerprint differs')
    sources = registration['sources']
    validate_split_isolation([*sources, *regression['cases']])
    similarity = audit_source_similarity([*sources, *regression['cases']], threshold=registration['similarity_threshold'])
    core.require(similarity['passed'] and similarity == sealed(registration['similarity_audit']),
                 'source similarity audit failed or changed')
    replayed, states = {}, {}
    for source in sources:
        source_id = source['source_id']
        core.require(source_id not in replayed and source['split'] == 'train', 'duplicate or non-train source')
        manifest = sealed(source['manifest'])
        core.require(manifest.get('source_type') == 'native_production_trace'
                     and manifest.get('model_sha256') == registration['model_sha256']
                     and manifest.get('collector_source_manifest_sha256')
                     and manifest.get('server_identity_sha256'), 'production source attestation missing')
        root = Path(source['run_root'])
        for name, checksum in manifest['files'].items():
            relative = Path(name)
            core.require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe source member')
            core.verify_file(root / relative, checksum)
        for required in ('state_snapshot.json', 'model_trace.jsonl', 'RESULT.json'):
            core.require(required in manifest['files'], 'missing sealed production artifact')
        replayed[source_id] = replay_run(root, registration['model_sha256'])
        states[source_id] = RunState.from_dict(json.loads((root / 'state_snapshot.json').read_text()))
    lookup = {s['source_id']: s for s in sources}
    identities = set()
    for row in rows:
        normalize_direct_row(row, model_sha256=registration['model_sha256'], context_tokens=registration['context_tokens'],
                             vocab_size=registration['vocab_size'], bos_token_id=registration['bos_token_id'])
        core.require(row['sample_id'] not in identities, 'duplicate direct sample')
        identities.add(row['sample_id'])
        source = lookup[row['source_id']]
        core.require(row['source_manifest_sha256'] == source['manifest']['sha256']
                     and row['family'] == source['family']
                     and row['source_content_sha256'] == source['source_content_sha256'], 'row source binding differs')
        actual = replayed[row['source_id']][row['candidate_checkpoint_id']]
        for key in ('input_token_ids', 'input_text', 'input_checkpoint_id', 'request_id'):
            core.require(row[key] == actual[key], 'row differs from actual production ' + key)
        state = states[row['source_id']]
        command_text = row['target_text'][:-len(model_io.JSON_CALL_STOP_SUFFIXES[0])]
        if row['label_authority'] == 'executed_read':
            action = state.actions[row['executed_action_id']]
            original = model_io.parse_model_command(actual['raw_generation']['raw_output'])
            target = model_io.parse_model_command(command_text)
            core.require(target == original and action.action_type == target.name
                         and dict(action.arguments) == executed_arguments(target) and action.result.get('success') is True
                         and target.arguments.get('path') == source['path']
                         and hashlib.sha256(action.result['output'].encode()).hexdigest() == row['source_content_sha256'],
                         'executed read target differs from actual command/result')
        else:
            # Only observations in this generation's ancestry may justify labels.
            content_hashes = []
            current = state.model_states[actual['input_checkpoint_id']]
            visible = set()
            while current is not None:
                visible.update(current.event_ids)
                current = state.model_states.get(current.parent_checkpoint_id)
            for event_id in visible:
                event = state.model_events[event_id]
                observation = event.payload.get('result', {}).get('observation', {})
                if observation.get('projection_complete'):
                    text = ''.join(span['content'] for span in observation.get('exact_spans', []))
                    content_hashes.append(hashlib.sha256(text.encode()).hexdigest())
            core.require(row['source_content_sha256'] in content_hashes, 'summary target uses unobserved source')
    coverage = registration['minimum_coverage']
    core.require(len({row['source_id'] for row in rows}) >= coverage['source_files']
                 and len({row['family'] for row in rows}) >= coverage['families']
                 and sum(row['label_authority'] == 'executed_read' for row in rows) >= coverage['read_boundaries']
                 and sum(row['label_authority'] == 'independent_review' for row in rows) >= coverage['summary_boundaries'],
                 'direct coverage requirement not met')
    counts = {'train': len(rows), **{split: sum(c['split'] == split for c in regression['cases'])
                                   for split in ('dev', 'confirmation')}}
    core.require(all(counts[k] >= registration['minimum_counts'][k] > 0 for k in counts), 'direct minimum counts not met')
    output = Path(output).absolute()
    core.require(not output.exists(), 'dataset output already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.direct-freeze-', dir=output.parent))
    try:
        (staging / 'train.jsonl').write_bytes(b''.join(_canonical_bytes(row) + b'\n' for row in rows))
        shutil.copyfile(registration['regression_registration']['path'], staging / 'regression.json')
        version, protocol_sha = protocol_identity()
        manifest = {'schema_version': DATASET_SCHEMA, 'purpose': 'frozen_role_training', 'role': ROLE,
                    'input_protocol': version, 'protocol_sha256': protocol_sha,
                    'tokenizer_sha256': core.sha256_file(VOCAB_PATH), 'model_sha256': registration['model_sha256'],
                    'freeze_registration': dict(registration_reference), 'authorization': registration['authorization'],
                    'counts': counts, 'count_units': {'train': 'reviewed generation boundaries', 'dev': 'tasks', 'confirmation': 'tasks'},
                    'sources': sources, 'similarity_audit': registration['similarity_audit'],
                    'candidate_audit': {'status': 'valid', 'quality_gates': {'exact_native_replay': True,
                        'labels_bound_to_visible_evidence': True, 'source_family_isolation': True}},
                    'train': {'file': 'train.jsonl', 'sha256': core.sha256_file(staging / 'train.jsonl')},
                    'regression': {'file': 'regression.json', 'sha256': core.sha256_file(staging / 'regression.json'),
                                   'fingerprint': fingerprint}}
        (staging / 'manifest.json').write_bytes(_canonical_bytes(manifest) + b'\n')
        _publish_no_replace(staging, output)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def audit_source_similarity(records: Sequence[Mapping], *, threshold: float) -> dict:
    from rwkv_lh.role_trace_artifacts import byte_5gram_cosine
    core.require(0 < threshold <= 1, 'invalid source similarity threshold')
    texts = []
    for row in records:
        ref = row['content_reference']
        core.require(ref['sha256'] == row['source_content_sha256'], 'source content reference differs')
        texts.append(core.verify_file(ref['path'], ref['sha256']).read_text())
    pairs = []
    for i, left in enumerate(records):
        for j in range(i + 1, len(records)):
            right = records[j]
            if left['split'] != right['split']:
                cosine = byte_5gram_cosine(texts[i], texts[j])
                pairs.append({'left': left['id'], 'right': right['id'], 'cosine': cosine})
    violations = [p for p in pairs if p['cosine'] >= threshold]
    return {'algorithm': 'utf8_byte_5gram_count_cosine', 'threshold': threshold,
            'pairs': pairs, 'violations': violations, 'passed': not violations}
