"""Accumulate real Executor errors and externally authored, executed corrections.

No target generator, model call, online intervention, or training admission lives
here. Original production inputs remain authoritative, including long prefixes.
"""
from copy import deepcopy
import json
from pathlib import Path

from . import statetune_core as core
from .project_contracts import digest
from .project_training_sources import load_source, read_reference
from .project_training_labels import _build
from .project_ledger import ProjectLedger
from .project_runtime import ProjectRuntime
from .project_receipt_refs import resolve_command
from .model_io import ModelCommand
from .harness import ActionHarness
from .schema import GoalState, TaskAction
from .workspace_snapshot import tree_identity, copy_verified_workspace

CORPUS_SCHEMA = 'rwkv-lh.executor-error-corpus.v1'
CORRECTION_SCHEMA = 'rwkv-lh.executor-authored-correction.v1'
PROOF_SCHEMA = 'rwkv-lh.executor-correction-execution.v1'


def _reference(path):
    return {'path': str(path), 'sha256': core.sha256_file(path)}


def _write(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n')
    return _reference(path)


def _train_source(reference):
    source = load_source(reference)
    core.require(source['registered']['split'] == 'train', 'only registered train sources enter the error corpus')
    return source


def _output(source, output):
    output = Path(output).resolve()
    root = source['ledger'].root
    core.require(output != root and root not in output.parents and output not in root.parents,
                 'correction output must not overlap original source')
    return output


def import_source(reference, output):
    """Index every real boundary once; a diagnostic signal is not an error label."""
    source = _train_source(reference)
    output = _output(source, output)
    directory = output / source['event_root']
    rows, previous = [], set()
    for operation, replay in source['replayed'].items():
        row = replay['row']
        command = row['result']['command']
        key = digest(command)
        signals = []
        if key in previous:
            signals.append('previously_observed_identical_command')
        previous.add(key)
        if command['function'] in ('protocol_rejected', 'model_output_budget_exhausted'):
            signals.append(command['function'])
        rows.append({'operation_id': operation, 'source_event_digest': row['source_event_digest'],
            'input_tokens': len(replay['input_token_ids']), 'input_sha256': digest(replay['input_text']),
            'observed_command': command, 'signals': signals,
            'status': 'awaiting_author_review', 'training_eligible': False})
    value = {'schema_version': CORPUS_SCHEMA, 'source_manifest': reference,
        'source_lineage_digest': source['event_root'], 'source_group': source['registered']['source_group'],
        'repository_family': source['registered']['repository_family'], 'boundaries': rows,
        'purpose': 'unlabelled_error_review_queue', 'training_eligible': False}
    path = directory / 'SOURCE.json'
    if path.exists():
        core.require(json.loads(path.read_text()) == value, 'existing corpus source differs; never overwrite')
        for operation, replay in source['replayed'].items():
            leaf = directory / operation
            boundary = json.loads((leaf/'BOUNDARY.json').read_text())
            for key in ('input_file', 'output_file', 'snapshot'):
                ref = boundary[key]
                core.verify_file(Path(ref['path']), ref['sha256'])
            core.require(boundary['input'] == replay['row']['input']
                         and boundary['input_token_ids'] == replay['input_token_ids']
                         and boundary['observed_result'] == replay['row']['result']
                         and (leaf/'INPUT.md').read_text() == replay['input_text']
                         and (leaf/'OBSERVED_OUTPUT.txt').read_text() == replay['row']['result']['evidence']['raw_generation']['raw_output'],
                         'existing corpus boundary differs from source')
        return _reference(path)
    directory.mkdir(parents=True, exist_ok=False)
    for operation, replay in source['replayed'].items():
        row = replay['row']
        leaf = directory / operation
        leaf.mkdir()
        (leaf / 'INPUT.md').write_text(replay['input_text'], encoding='utf-8')
        raw = row['result']['evidence']['raw_generation']
        (leaf / 'OBSERVED_OUTPUT.txt').write_text(raw['raw_output'], encoding='utf-8')
        _write(leaf / 'BOUNDARY.json', {'source_manifest': reference, 'source_operation_id': operation,
            'source_event_digest': row['source_event_digest'], 'input': row['input'],
            'input_token_ids': replay['input_token_ids'], 'observed_result': row['result'],
            'snapshot': _reference(source['snapshots'][operation].parent/'SNAPSHOT.json'),
            'input_file': _reference(leaf/'INPUT.md'), 'output_file': _reference(leaf/'OBSERVED_OUTPUT.txt'),
            'training_eligible': False})
    core.require(tree_identity(source['ledger'].root, exclude_git=False) == source['tree'], 'source changed during corpus import')
    return _write(path, value)


def author_correction(reference, operation, command, *, output, author, diagnosis, checks,
                      context_tokens, input_view=None):
    """Store an author's correction, never synthesize or silently trim its input."""
    source = _train_source(reference)
    core.require(isinstance(diagnosis, str) and diagnosis.strip(), 'author must explain the observed error')
    core.require(isinstance(checks, list), 'explicit verification checks required')
    harness = ActionHarness()
    for check in checks:
        core.require(isinstance(check, dict), 'check arguments must be objects')
        harness.normalize_action(TaskAction('check_command', check))
    packet, packed = _build(source, operation, command, context_tokens, author, input_view=input_view)
    core.require(_resolved_command(packet) != source['replayed'][operation]['row']['result']['command'],
                 'an unchanged observed action is not a correction')
    output = _output(source, output)
    output.mkdir(parents=True, exist_ok=False)
    packet_ref = _write(output/'PACKET.json', packet)
    supervision = _write(output/'SUPERVISION.json', packed)
    correction = {'schema_version': CORRECTION_SCHEMA, 'packet': packet_ref, 'supervision': supervision,
        'diagnosis': diagnosis, 'checks': deepcopy(checks), 'training_eligible': False,
        'source_lineage_digest': source['event_root'],
        'status': 'authored_awaiting_execution_and_review'}
    return _write(output/'CORRECTION.json', correction)


def _load_correction(reference, *, _source_loader=load_source):
    correction = read_reference(reference)
    core.require(correction.get('schema_version') == CORRECTION_SCHEMA, 'current authored correction required')
    packet = read_reference(correction['packet'])
    source = _source_loader(packet['source_manifest'])
    core.require(source['registered']['split'] == 'train', 'only registered train sources enter the error corpus')
    expected, packed = _build(source, packet['source_operation_id'], packet['proposed_target'],
                              packet['context_tokens'], packet['author'], input_view=packet.get('input_view'))
    core.require(packet == expected and read_reference(correction['supervision']) == packed,
                 'correction differs from the complete original input and authored target')
    core.require(correction['source_lineage_digest'] == source['event_root'], 'correction lineage differs')
    return correction, packet, packed, source


def _checks(checks, source_workspace, output):
    if not checks:
        return []
    # Before and after checks have their own disposable workspace; neither can
    # modify the snapshot or the correction execution used as evidence.
    workspace = output/'workspace'
    copy_verified_workspace(source_workspace, workspace, exclude_git=False)
    harness = ActionHarness()
    goal = GoalState.create(request='Execute the registered offline correction checks', workspace_root=str(workspace), constraints=[])
    rows = []
    for check in checks:
        action = harness.normalize_action(TaskAction('check_command', check))
        with harness.action_transaction(goal):
            result = harness.execute(action, goal)
        rows.append(result.to_dict())
    _write(output/'RESULTS.json', {'results': rows})
    return rows


def _verification_gaps(receipt, checks, before, after):
    gaps = []
    if receipt is not None and not receipt['success']:
        gaps.append('corrected_action_failed')
    changed = receipt['metadata']['changed_paths'] if receipt is not None else []
    if changed and not checks:
        gaps.append('changed_action_requires_checks')
    if after and not all(r['success'] for r in after):
        gaps.append('registered_after_checks_failed')
    if changed and before and all(r['success'] for r in before):
        gaps.append('checks_did_not_distinguish_original_from_correction')
    return gaps


def _resolved_command(packet):
    command = packet['proposed_target']
    return resolve_command(packet['input'], ModelCommand(command['function'], command['params'])).to_wire_dict()


def _control_context(source, packet):
    """Recover only evidence that existed before this actual generation.

    Imported receipts retain their original identities and bytes. The offline
    ledger explicitly imports them; it never invents past model/tool events.
    """
    snapshot = read_reference(packet['source_snapshot_manifest'])
    found = []
    with ProjectLedger.read_snapshot(source['ledger'].root) as ledger:
        def collect(event):
            if event['digest'] == snapshot['source_event_digest']:
                found.append(event)
        ledger.scan_verified_events(collect)
    core.require(len(found) == 1, 'original control boundary must be unique')
    event = found[0]
    state = event['state']
    pending = state['pending']
    core.require(event['kind'] == 'operation_started' and pending
                 and pending['id'] == packet['source_operation_id'] and pending['kind'] == 'model'
                 and state['plan'] == packet['input']['plan'], 'original control boundary differs')
    # This is the original production input, even when the training packet is
    # a separately derived window. Future results never enter either prefix.
    original = source['replayed'][packet['source_operation_id']]['row']['input']
    core.require(pending['payload']['input_digest'] == digest(original), 'original input binding differs')
    history = {key: deepcopy(state[key]) for key in ('active', 'current_step_id', 'selected_evidence')}
    history['evidence'] = {key: deepcopy(value) for key, value in state['evidence'].items()
                           if value['kind'] == 'tool'}
    files = {}
    for receipt in history['evidence'].values():
        raw = receipt['result'].get('raw_receipt')
        if raw:
            path = (ledger.root / raw['path']).resolve(strict=True)
            core.require(ledger.root in path.parents, 'imported receipt outside original records')
            body = json.loads(path.read_text())
            core.require(digest(body) == raw['content_digest'], 'original imported receipt digest differs')
            files[raw['path']] = _reference(path)
    binding = {'source_event_digest': event['digest'], 'imported_state_digest': digest(history),
               'receipt_files': files}
    return history, binding


def _import_control_context(db, source, packet):
    history, binding = _control_context(source, packet)
    for relative, reference in binding['receipt_files'].items():
        path = db.root / relative
        core.require(not Path(relative).is_absolute() and '..' not in Path(relative).parts
                     and not path.exists(), 'invalid imported receipt destination')
        core.verify_file(Path(reference['path']), reference['sha256'])
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(Path(reference['path']).read_bytes())
    def apply(state):
        state.update(deepcopy(history))
        state['offline_source_context'] = deepcopy(binding)
    db.update('offline_correction_source_imported', apply)
    return binding


def _control_event(event):
    return {key: event[key] for key in ('kind', 'digest')} | {'state_digest': digest(event['state'])}


def _verify_control_state(db, tip, source, packet, proof):
    history, binding = _control_context(source, packet)
    state = tip['state']
    command = _resolved_command(packet)
    name, params = command['function'], command['params']
    identifier = 'OFFLINE-' + digest({'source': packet['source_event_digest'], 'target': packet['target_digest']})
    core.require(proof['source_context'] == binding == state.get('offline_source_context')
                 and state['active'] == history['active'] and state['evidence'] == history['evidence']
                 and state['current_step_id'] == history['current_step_id'], 'imported control evidence differs')
    for relative, reference in binding['receipt_files'].items():
        core.verify_file(db.root / relative, reference['sha256'])
    core.require(state['calls'] == 0 and not state['sessions'] and state['pending'] is None
                 and state['inbox'] is None and proof['model_calls'] == 0,
                 'offline controls may not invent model calls or checkpoints')
    core.require(proof['execution_success'] is True and proof['receipt'] is None and proof['changed_paths'] == []
                 and proof['before_tree'] == proof['after_tree']
                 and proof['control_event'] == _control_event(tip), 'control proof is not its actual event')
    if name == 'finish_work':
        claim = state['final_claim']
        core.require(tip['kind'] == 'executor_finished' and state['status'] == params['outcome']
                     and state['final'] == params['summary'] and claim['summary'] == params['summary']
                     and claim['outcome'] == params['outcome'] and claim['receipt_ids'] == params['receipt_ids']
                     and claim['authority'] == 'executor_claim'
                     and claim['source_operation_id'] == identifier
                     and claim['workspace_digest'] == state['workspace_digest']
                     and state['feedback'] == {'kind': 'executor_finished', 'claim': claim},
                     'final declaration differs from correction')
        core.require(state['selected_evidence'] == history['selected_evidence'], 'finish changed delivered evidence')
    else:
        core.require(name == 'read_receipt' and tip['kind'] == 'evidence_selected'
                     and state['status'] == 'running' and state['final_claim'] is None,
                     'receipt correction changed final status')
        lane, receipt_id = state['active']['id'], params['receipt_id']
        expected = deepcopy(history['selected_evidence'])
        evidence = deepcopy(history['evidence'][receipt_id])
        raw = evidence['result'].get('raw_receipt')
        if raw:
            evidence['raw_result'] = json.loads((db.root / raw['path']).read_text())
        selected = expected.setdefault(lane, {})
        revision = selected.get(receipt_id, {}).get('revision', 0) + 1
        selected[receipt_id] = {'revision': revision, 'evidence': evidence}
        core.require(state['selected_evidence'] == expected
                     and state['feedback'] == {'kind': 'receipt_requested', 'evidence_id': receipt_id,
                                              'request_operation_id': identifier},
                     'receipt delivery differs from actual source')


def verify_correction(reference):
    """Execute one current Executor action through production methods offline.

    The ledger explicitly records an offline author. It contains no model call,
    checkpoint or invented RWKV response, and is not a new training source.
    """
    correction, packet, packed, source = _load_correction(reference)
    command = _resolved_command(packet)
    core.require(command['function'] in ('execute_tool', 'read_receipt', 'finish_work'),
                 'current Executor correction required')
    control = command['function'] != 'execute_tool'
    directory = Path(reference['path']).parent/'EXECUTION'
    directory.mkdir(exist_ok=False)
    before = source['snapshots'][packet['source_operation_id']]
    workspace = directory/'workspace'
    original = copy_verified_workspace(before, workspace, exclude_git=False, audit_path=directory/'COPY.json')
    plan = packet['input']['plan']
    db = ProjectLedger.create(directory/'execution', request=packet['input']['original_request'],
        workspace=workspace, max_calls=1, max_seconds=180, protected_paths=plan['protected_paths'])
    db.install_plan(plan)
    source_context = _import_control_context(db, source, packet) if control else None
    state = db.state()
    identifier = 'OFFLINE-' + digest({'source': packet['source_event_digest'], 'target': packet['target_digest']})
    def bind(s):
        s['offline_correction'] = {'authority': 'external_author_not_rwkv', 'correction': reference,
            'source_operation_id': packet['source_operation_id'], 'target_digest': packet['target_digest']}
        s['inbox'] = {'role': 'executor', 'lane': s['active']['id'], 'command': deepcopy(command),
            'operation_id': identifier, 'plan_version': s['plan_version']}
    db.update('offline_correction_authored', bind)
    checks_before = _checks(correction['checks'], before, directory/'checks_before')
    class NoModelCalls:
        def request(self, *args, **kwargs):
            raise RuntimeError('offline correction verification may not call a model')
    runtime = ProjectRuntime(db, NoModelCalls())
    params = command['params']
    with db.lease():
        if command['function'] == 'execute_tool':
            runtime._tool(params['tool'], params['arguments'], state['active']['id'], params['step_id'])
        elif command['function'] == 'read_receipt':
            runtime.expand_evidence(params['receipt_id'], executor_lane=state['active']['id'])
        else:
            db.finish_work(**params)
    receipt = None
    if not control:
        evidence = [r for r in db.state()['evidence'].values() if r['kind'] == 'tool']
        core.require(len(evidence) == 1, 'one actual correction tool receipt required')
        raw_ref = evidence[0]['result']['raw_receipt']
        receipt = json.loads((db.root/raw_ref['path']).read_text())
        core.require(digest(receipt) == raw_ref['content_digest'], 'correction receipt changed')
    checks_after = _checks(correction['checks'], workspace, directory/'checks_after')
    changed = [] if control else receipt['metadata']['changed_paths']
    gaps = _verification_gaps(receipt, correction['checks'], checks_before, checks_after)
    verified = not gaps
    if not packed['fits_context']:
        gaps.append('complete_prefix_exceeds_training_capacity')
    gaps += ['independent_review_required', 'dataset_freeze_required']
    final_tree = tree_identity(workspace, exclude_git=False)
    core.require(tree_identity(source['ledger'].root, exclude_git=False) == source['tree'], 'original source changed')
    proof = {'schema_version': PROOF_SCHEMA, 'correction': reference,
        'source_snapshot': packet['source_snapshot_manifest'], 'target_digest': packet['target_digest'],
        'input_digest': packet['input_digest'], 'before_tree': original, 'after_tree': final_tree,
        'execution_ledger': _reference(db.path), 'execution_event_tip': db.scan_verified_events()['digest'],
        'execution_tree': tree_identity(db.root, exclude_git=False),
        'checks_files': {key: _reference(directory/key/'RESULTS.json')
                         for key in ('checks_before', 'checks_after') if correction['checks']},
        'receipt': receipt, 'execution_success': True if control else receipt['success'], 'changed_paths': changed,
        'checks_before': checks_before, 'checks_after': checks_after,
        'verification_passed': verified, 'fits_context': packed['fits_context'],
        'training_eligible': False, 'admission_gaps': gaps, 'model_calls': 0,
        'implementation_sha256': core.sha256_file(__file__)}
    if control:
        tip = db.scan_verified_events()
        proof.update(source_context=source_context, control_event=_control_event(tip))
        _verify_control_state(db, tip, source, packet, proof)
    _write(directory/'PROOF.json', proof)
    return proof


def _verify_execution_for_packet(correction_reference, proof_reference, reviewed_packet, *, _source_loader=load_source):
    """Bind execution to the same original boundary and target, including a view.

    A derived window changes the evidence presented to the learner; it does not
    change the source workspace on which this exact action was verified.
    """
    correction, packet, _, source = _load_correction(correction_reference, _source_loader=_source_loader)
    proof = read_reference(proof_reference)
    directory = Path(correction_reference['path']).parent/'EXECUTION'
    core.require(Path(proof_reference['path']) == directory/'PROOF.json'
                 and proof.get('schema_version') == PROOF_SCHEMA
                 and proof['correction'] == correction_reference
                 and proof['source_snapshot'] == packet['source_snapshot_manifest']
                 and proof['target_digest'] == packet['target_digest']
                 and proof['input_digest'] == packet['input_digest'], 'execution proof binding differs')
    core.require(tree_identity(directory/'execution', exclude_git=False) == proof['execution_tree']
                 and tree_identity(directory/'workspace', exclude_git=False) == proof['after_tree']
                 and tree_identity(source['snapshots'][packet['source_operation_id']], exclude_git=False) == proof['before_tree'],
                 'correction execution evidence changed')
    core.verify_file(Path(proof['execution_ledger']['path']), proof['execution_ledger']['sha256'])
    with ProjectLedger.read_snapshot(directory/'execution') as db:
        tip = db.scan_verified_events()
        core.require(tip['digest'] == proof['execution_event_tip'], 'execution event tip differs')
        binding = tip['state']['offline_correction']
        core.require(binding['authority'] == 'external_author_not_rwkv'
                     and binding['correction'] == correction_reference
                     and binding['target_digest'] == packet['target_digest'], 'offline author binding differs')
        control = packet['proposed_target']['function'] != 'execute_tool'
        if control:
            _verify_control_state(db, tip, source, packet, proof)
            receipt = None
        else:
            evidence = [e for e in tip['state']['evidence'].values() if e['kind'] == 'tool']
            core.require(len(evidence) == 1, 'one real correction tool receipt required')
            raw = evidence[0]['result']['raw_receipt']
            receipt = json.loads((db.root/raw['path']).read_text())
            core.require(digest(receipt) == raw['content_digest'] and receipt == proof['receipt'], 'execution receipt differs')
    for key in ('checks_before', 'checks_after'):
        expected = read_reference(proof['checks_files'][key])['results'] if correction['checks'] else []
        core.require(expected == proof[key] and len(expected) == len(correction['checks']), 'check proof differs')
        for check, result in zip(correction['checks'], expected):
            core.require(result['metadata']['argv'] == check['argv']
                         and result['metadata']['expected_exit_code'] == check.get('expected_exit_code', 0),
                         'checks differ from registered commands')
    gaps = _verification_gaps(receipt, correction['checks'], proof['checks_before'], proof['checks_after'])
    core.require(not gaps
                 and proof['verification_passed'] is True, 'correction execution verification failed')
    expected, packed = _build(source, packet['source_operation_id'], packet['proposed_target'],
        packet['context_tokens'], packet['author'], input_view=reviewed_packet.get('input_view'))
    core.require(reviewed_packet == expected, 'review describes another correction')
    core.require(packed['fits_context'], 'complete training input exceeds training capacity; no truncation')


def load_executed_candidate(correction_reference, proof_reference, review_reference):
    """Return a candidate with both intact execution and independent review."""
    from .project_training_labels import load_reviewed_candidate
    artifact = read_reference(review_reference)
    registration = read_reference(artifact['review_registration'])
    _verify_execution_for_packet(correction_reference, proof_reference, read_reference(registration['packet']))
    return load_reviewed_candidate(review_reference)
