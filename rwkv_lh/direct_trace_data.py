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


def replay_run(run_root: Path, model_sha256: str, *,
               expected_state_profile: Mapping[str, str] | None = None) -> dict[str, dict]:
    """Rebuild every generation input using production bootstrap/event renderers.

    The caller seals all source files first. Recorded workspace identity is
    preserved; tools are never executed. No inference, fabricated tool result, or target
    construction occurs here.
    """
    # Training callers deliberately keep the zero-only default. An evidence
    # exporter must supply the registered candidate identity, never infer an
    # authorization to accept an arbitrary State from the trace itself.
    profile = dict(expected_state_profile) if expected_state_profile is not None else {
        'id': 'zero', 'sha256': '0' * 64}
    import re
    core.require(set(profile) == {'id', 'sha256'}
                 and isinstance(profile['id'], str)
                 and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', profile['id'])
                 and isinstance(profile['sha256'], str)
                 and re.fullmatch(r'[0-9a-f]{64}', profile['sha256'])
                 and ((profile['id'] == 'zero') == (profile['sha256'] == '0' * 64)),
                 'invalid registered replay State profile')
    state = RunState.from_dict(json.loads((run_root / 'state_snapshot.json').read_text()))
    for checkpoint in state.model_states.values():
        binding = checkpoint.native_state_metadata.get('cache_binding', {})
        core.require(checkpoint.state_profile_id == profile['id']
                     and checkpoint.state_profile_sha256 == profile['sha256']
                     and binding.get('state_profile_id') == profile['id']
                     and binding.get('state_profile_sha256') == profile['sha256'],
                     'source State profile differs from registered replay profile (default zero)')
    events = [json.loads(line) for line in (run_root / 'model_trace.jsonl').read_text().splitlines()]
    returned = [e for e in events if e['type'] == 'model_session_generation_returned']
    starts = {e['request_id']: e for e in events if e['type'] == 'model_session_generation_started'}
    parent_trace = run_root / 'PARENT_TRACE.jsonl'
    ancestors = [json.loads(line) for line in parent_trace.read_text().splitlines()] if parent_trace.is_file() else []
    from .read_only_agent import generation_trace_integrity
    core.require(generation_trace_integrity(events)['paired']
                 and generation_trace_integrity(ancestors)['paired'], 'incomplete or duplicate generation trace')
    history = [e for e in ancestors if e['type'] == 'model_session_generation_returned'] + returned
    generations = {e['candidate_checkpoint_id']: e['raw_generation'] for e in history}
    core.require(len(generations) == len(history) and bool(returned), 'missing/duplicate generation identity')
    # Explicit inert transport: these objects are used only to render input.
    session = ModelSession(client=object(), settings=RuntimeSettings(base_url='http://unused.invalid', api_key='', model='replay-only', tool_disclosure_mode='full'))
    result_path = run_root / 'RESULT.json'
    scope = json.loads(result_path.read_text()).get('tool_scope') if result_path.is_file() else None
    if scope in (None, 'coding'):
        harness = ActionHarness()
    else:
        from rwkv_lh.read_only_agent import ReadOnlyHarness
        harness = ReadOnlyHarness(tool_scope=scope)
    model = LongHorizonModel(session, harness=harness)
    replay_goal = model.create_literal_goal(state.goal.request, state.goal.workspace_root,
                                                constraints=state.goal.constraints, runtime_policy=state.goal.runtime_policy)
    bootstraps = {}
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
            previous = state.model_states.get(current.parent_checkpoint_id)
            if previous:
                core.require(metadata.get('cache_binding', {}).get('parent_state_digest') == previous.native_state_digest,
                             'native parent digest differs')
            current = previous
        root_checkpoint = chain[-1]
        if root_checkpoint.checkpoint_id not in bootstraps:
            from dataclasses import replace
            from .correction_snapshots import validate_generation_snapshot
            initial_goal = replay_goal
            initial_starts = [item for item in starts.values()
                              if item['input_checkpoint_id'] == root_checkpoint.checkpoint_id]
            import re
            for item in initial_starts:
                core.require(isinstance(item['request_id'], str)
                             and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', item['request_id'])
                             and item['request_id'] not in ('.', '..'),
                             'unsafe initial snapshot request')
            snapshot_starts = [item for item in initial_starts if
                (run_root / 'generation_snapshots' / item['request_id']).exists()
                or any(event.get('type') == 'correction_generation_snapshot_saved'
                       and event.get('request_id') == item['request_id'] for event in events)]
            if snapshot_starts:
                core.require(len(snapshot_starts) == 1, 'ambiguous initial generation snapshot')
                first = snapshot_starts[0]
                core.require(first['input_digest'] == root_checkpoint.native_state_digest,
                             'initial snapshot root digest differs')
                directory = run_root / 'generation_snapshots' / first['request_id']
                members = {str(member.relative_to(run_root)): core.sha256_file(member)
                           for member in directory.rglob('*') if member.is_file()}
                before = validate_generation_snapshot(run_root, first, members)
                initial_goal = replace(replay_goal, workspace_root=str(before))
            initial = RunState(run_id=state.run_id, goal=initial_goal)
            bootstraps[root_checkpoint.checkpoint_id] = model_io.render_bootstrap(
                model.direct_definitions(), model._assignment(initial, recent_limit=None))
        bootstrap = bootstraps[root_checkpoint.checkpoint_id]
        core.require(root_checkpoint.transcript == bootstrap,
                     'production bootstrap replay differs')
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
            'source_model_sha256': model_sha256, 'source_state_profile': dict(profile), 'recomputed': True,
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
    envelope = json.loads(command_text)  # No transport repair or first-object extraction for training targets.
    core.require(isinstance(envelope, dict) and set(envelope) == {'function', 'params'},
                 'training target must use the production function/params envelope')
    command = model_io.parse_model_command(command_text)
    authority = row.get('label_authority')
    if authority == 'executed_read':
        core.require(command.name == 'read_file' and row.get('executed_action_id')
                     and row.get('real_tool_success') is True, 'read label lacks execution proof')
    elif authority == 'verified_stdio':
        review = row.get('stdio_review', {})
        core.require(command.name == 'write_file' and command.arguments.get('path') == 'solution.py'
                     and isinstance(row.get('stdio_validation'), Mapping)
                     and set(row['stdio_validation']) == {'path', 'sha256'},
                     'stdio label requires sealed entry-point execution proof')
        executed_arguments(command)
        core.require(isinstance(review.get('reviewer'), str) and bool(review['reviewer'].strip())
                     and review.get('accepted') is True and review.get('visible_evidence_only') is True
                     and review.get('source_consistent') is True and review.get('output_contract') == 'exact_unique'
                     and review.get('input_sha256') == hashlib.sha256(row['input_text'].encode()).hexdigest()
                     and review.get('target_sha256') == hashlib.sha256(raw_target.encode()).hexdigest(),
                     'stdio label lacks bound source review')
    elif authority in ('independent_review', 'verified_coding', 'verified_command', 'verified_read', 'verified_final'):
        target_sha = hashlib.sha256(raw_target.encode()).hexdigest()
        reviewers = row.get('reviews', [])
        if authority == 'independent_review':
            core.require(command.name == 'final_answer' and set(command.arguments) == {'text'}
                         and isinstance(command.arguments['text'], str) and bool(command.arguments['text'].strip()),
                         'summary label requires final answer')
        elif authority == 'verified_coding':
            core.require(command.name in ('write_file', 'replace_text')
                         and isinstance(row.get('correction_validation'), Mapping)
                         and set(row['correction_validation']) == {'path', 'sha256'},
                         'coding label requires sealed atomic correction proof')
            executed_arguments(command)
        elif authority in ('verified_read', 'verified_final'):
            functions = ('final_answer',) if authority == 'verified_final' else ('read_file', 'search_files', 'list_directory')
            core.require(command.name in functions and isinstance(row.get('observation_validation'), Mapping)
                         and set(row['observation_validation']) == {'path', 'sha256'},
                         'observation label requires sealed execution/grounding proof')
        else:
            core.require(command.name in ('check_command', 'run_shell')
                         and isinstance(row.get('command_validation'), Mapping)
                         and set(row['command_validation']) == {'path', 'sha256'},
                         'command label requires sealed command proof')
            executed_arguments(command)
        from .correction_review import require_source_bound_reviews
        require_source_bound_reviews(reviewers,
                                     input_sha256=hashlib.sha256(row['input_text'].encode()).hexdigest(),
                                     target_sha256=target_sha,
                                     execution_backed=authority in ('verified_coding', 'verified_command', 'verified_read', 'verified_final'))

    else:
        raise ValueError('unsupported direct label authority')
    return {'sample_id': row['sample_id'], 'input_token_ids': list(source), 'target_token_ids': list(target)}


def _complete_observed_text_hashes(result: Mapping) -> list[str]:
    """Bind labels to complete visible file text or typed command streams."""
    observation = result.get('observation', {})
    if observation.get('projection_complete') is not True:
        return []
    if observation.get('adapter') != 'command_streams':
        if 'exact_spans' not in observation:
            return []
        text = ''.join(span['content'] for span in observation['exact_spans'])
        return [hashlib.sha256(text.encode()).hexdigest()]
    core.require(result.get('action_type') in ('check_command', 'run_shell')
                 and observation.get('fact_authority') == 'exit_code_and_exact_stream_spans',
                 'command evidence authority differs')
    hashes = []
    names = set()
    for stream in result.get('command_streams', []):
        core.require(stream.get('stream') in ('stdout', 'stderr', 'combined')
                     and stream['stream'] not in names, 'command stream identity differs')
        names.add(stream['stream'])
        core.require(stream.get('projection_complete') is True, 'command stream is incomplete')
        parts = []
        offset = 0
        for span in stream.get('exact_spans', []):
            text = span['content']
            encoded = text.encode()
            core.require(span.get('start_byte') == offset
                         and span.get('end_byte') == offset + len(encoded)
                         and span.get('content_sha256') == hashlib.sha256(encoded).hexdigest()
                         and span.get('snapshot_sha256') == stream.get('stream_sha256'),
                         'command span content or range differs')
            offset += len(encoded)
            parts.append(text)
        text = ''.join(parts)
        checksum = hashlib.sha256(text.encode()).hexdigest()
        core.require(offset == stream.get('stream_bytes')
                     and len(text) == stream.get('stream_chars')
                     and checksum == stream.get('stream_sha256'), 'command stream content differs')
        hashes.append(checksum)
    core.require('combined' not in names or len(names) == 1, 'mixed combined and separate streams')
    return hashes


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
    boundaries = set()
    coding_proofs = []
    command_proofs = []
    stdio_proofs = []
    observation_proofs = []
    for row in rows:
        normalize_direct_row(row, model_sha256=registration['model_sha256'], context_tokens=registration['context_tokens'],
                             vocab_size=registration['vocab_size'], bos_token_id=registration['bos_token_id'])
        core.require(row['sample_id'] not in identities, 'duplicate direct sample')
        identities.add(row['sample_id'])
        boundary = (row['source_manifest_sha256'], row['candidate_checkpoint_id'])
        core.require(boundary not in boundaries, 'duplicate direct production boundary')
        boundaries.add(boundary)
        source = lookup[row['source_id']]
        core.require(row['source_manifest_sha256'] == source['manifest']['sha256']
                     and row['family'] == source['family']
                     and row['source_content_sha256'] == source['source_content_sha256'], 'row source binding differs')
        actual = replayed[row['source_id']][row['candidate_checkpoint_id']]
        for key in ('input_token_ids', 'input_text', 'input_checkpoint_id', 'request_id'):
            core.require(row[key] == actual[key], 'row differs from actual production ' + key)
        state = states[row['source_id']]
        proof = None
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
        elif row['label_authority'] == 'verified_stdio':
            from .stdio_corrections import revalidate_training_stdio
            with tempfile.TemporaryDirectory(prefix='rwkv-stdio-freeze-') as temporary:
                proof = revalidate_training_stdio(row, run_root=source['run_root'],
                    source_files=sealed(source['manifest'])['files'],
                    model_sha256=registration['model_sha256'], output=Path(temporary) / 'validation')
                stdio_proofs.append({'sample_id': row['sample_id'], 'validation': proof})
        elif row['label_authority'] == 'verified_coding':
            from .coding_corrections import revalidate_training_correction
            with tempfile.TemporaryDirectory(prefix='rwkv-coding-freeze-') as temporary:
                proof = revalidate_training_correction(row, run_root=source['run_root'],
                    source_files=sealed(source['manifest'])['files'],
                    model_sha256=registration['model_sha256'], output=Path(temporary) / 'validation')
                coding_proofs.append({'sample_id': row['sample_id'], 'validation': proof})
        elif row['label_authority'] == 'verified_command':
            from .command_corrections import revalidate_training_command
            with tempfile.TemporaryDirectory(prefix='rwkv-command-freeze-') as temporary:
                proof = revalidate_training_command(row, run_root=source['run_root'],
                    source_files=sealed(source['manifest'])['files'],
                    model_sha256=registration['model_sha256'], output=Path(temporary) / 'validation')
                command_proofs.append({'sample_id': row['sample_id'], 'validation': proof})
        elif row['label_authority'] in ('verified_read', 'verified_final'):
            from .observation_corrections import revalidate_training_observation
            with tempfile.TemporaryDirectory(prefix='rwkv-observation-freeze-') as temporary:
                proof = revalidate_training_observation(row, run_root=source['run_root'],
                    source_files=sealed(source['manifest'])['files'],
                    model_sha256=registration['model_sha256'], output=Path(temporary) / 'validation')
                observation_proofs.append({'sample_id': row['sample_id'], 'validation': proof})
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
                content_hashes.extend(_complete_observed_text_hashes(event.payload.get('result', {})))
            core.require(row['source_content_sha256'] in content_hashes, 'summary target uses unobserved source')
        policy = row.get('public_validation_policy')
        if policy is not None:
            if 'learning_contract' in policy:
                from .trace_correction_pipeline import validate_learning_contract
                validate_learning_contract(policy['learning_contract'], row['input_text'],
                    function=model_io.parse_model_command(
                        row['target_text'][:-len(model_io.JSON_CALL_STOP_SUFFIXES[0])]).name)
            core.require(type(policy.get('read_only')) is bool and isinstance(policy.get('protected_paths'), list),
                         'invalid frozen public validation policy')
            from .correction_snapshots import validate_generation_snapshot
            from .workspace_snapshot import tree_identity
            before = tree_identity(validate_generation_snapshot(Path(source['run_root']), actual,
                                   sealed(source['manifest'])['files']))
            core.require(proof is not None, 'public policy requires fresh execution proof')
            after = proof.get('corrected_tree', proof.get('after_tree'))
            core.require(isinstance(after, dict), 'fresh workspace identity missing')
            for name in policy['protected_paths']:
                path = Path(name)
                core.require(not path.is_absolute() and '..' not in path.parts and bool(name), 'unsafe protected path')
                core.require(before.get(name) == after.get(name), 'protected file changed in fresh validation')
            core.require(not policy['read_only'] or before == after, 'read-only workspace changed in fresh validation')
    coverage = registration['minimum_coverage']
    core.require(len({row['source_id'] for row in rows}) >= coverage['source_files']
                 and len({row['family'] for row in rows}) >= coverage['families']
                 and sum(row['label_authority'] in ('executed_read', 'verified_read') for row in rows) >= coverage['read_boundaries']
                 and sum(row['label_authority'] in ('independent_review', 'verified_final') for row in rows) >= coverage['summary_boundaries'],
                 'direct coverage requirement not met')
    action_counts = {
        'coding_boundaries': sum(row['label_authority'] == 'verified_coding' for row in rows),
        'command_boundaries': len(command_proofs),
        'stdio_boundaries': len(stdio_proofs),
    }
    for name, actual_count in action_counts.items():
        minimum = coverage.get(name, 0)
        core.require(type(minimum) is int and minimum >= 0 and actual_count >= minimum
                     and (not actual_count or minimum > 0),
                     name + ' coverage must be explicitly registered and met')
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
        if observation_proofs:
            (staging / 'observation_validation.json').write_bytes(_canonical_bytes({'rows': observation_proofs}) + b'\n')
        if coding_proofs:
            (staging / 'coding_validation.json').write_bytes(_canonical_bytes({'rows': coding_proofs}) + b'\n')
        if command_proofs:
            (staging / 'command_validation.json').write_bytes(_canonical_bytes({'rows': command_proofs}) + b'\n')
        if stdio_proofs:
            (staging / 'stdio_validation.json').write_bytes(_canonical_bytes({'rows': stdio_proofs}) + b'\n')
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
        if observation_proofs:
            manifest['observation_validation'] = {'file': 'observation_validation.json',
                'sha256': core.sha256_file(staging / 'observation_validation.json'), 'count': len(observation_proofs)}
        if coding_proofs:
            manifest['coding_validation'] = {'file': 'coding_validation.json',
                'sha256': core.sha256_file(staging / 'coding_validation.json'), 'count': len(coding_proofs)}
        if command_proofs:
            manifest['command_validation'] = {'file': 'command_validation.json',
                'sha256': core.sha256_file(staging / 'command_validation.json'), 'count': len(command_proofs)}
        if stdio_proofs:
            manifest['stdio_validation'] = {'file': 'stdio_validation.json',
                'sha256': core.sha256_file(staging / 'stdio_validation.json'), 'count': len(stdio_proofs),
                'contract': 'one bound source review plus fresh isolated exact-output execution'}
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
