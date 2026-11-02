"""Archive all real outcomes and action annotations without altering model input.

Activity labels describe observed tool categories, not a controller, inferred
correctness or a compulsory order. They remain outside the training transcript.
"""
import json
import os
import tempfile
from pathlib import Path

from rwkv_lh.data_engine.tasks import dump, checksum
from rwkv_lh.harness import ActionHarness
from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.project_runtime import agent_definitions
from rwkv_lh.transcript.export import session_transcript
from rwkv_lh.workspace_snapshot import tree_identity

ACTIVITIES = {'Read': 'inspect', 'ListDir': 'inspect', 'Grep': 'inspect',
              'Write': 'modify', 'Edit': 'modify', 'Bash': 'execute',
              'BashOutput': 'observe_background', 'KillShell': 'stop_background',
              'finish_work': 'declare'}


def write_immutable(path, raw):
    """Publish one complete file; retries must have exactly the same bytes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.publishing-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise ValueError('immutable record differs: ' + str(path))
    finally:
        temporary.unlink()


def record_episode(task, run, *, verdict=None):
    """Record an ended clean session, including failed/blocked/interrupted runs.

    Uncertain pending effects stay in the ledger; they cannot masquerade as an
    ended transcript. A later verifier result gets a separate verdict record.
    """
    run = Path(run)
    definitions = agent_definitions(ActionHarness())
    exported = session_transcript(run / 'execution', definitions)
    with ProjectLedger.read_snapshot(run / 'execution') as ledger:
        tip = ledger.scan_verified_events()
        state = tip['state']
    document = json.loads(exported['bytes'])
    receipts = {m['tool_call_id']: json.loads(m['content']) for m in document['messages'] if m['role'] == 'tool'}
    actions = []
    request_index, turn = -1, 0
    from rwkv_lh.project_protocols.agent import is_host_notice
    for message in document['messages']:
        if message['role'] == 'user' and not is_host_notice(message):
            request_index += 1
        if message['role'] != 'assistant':
            continue
        turn += 1
        for call in message['tool_calls']:
            name = call['function']['name']
            receipt = receipts.get(call['id'], {})
            actions.append({'turn': turn, 'request_index': request_index, 'call_id': call['id'],
                            'tool': name, 'activity': ACTIVITIES[name],
                            'receipt_sha256': checksum(receipt) if receipt else None,
                            'tool_success': receipt.get('success'),
                            'changed_paths': receipt.get('metadata', {}).get('changed_paths', [])})
    if verdict is not None:
        if verdict['task_digest'] != task['digest'] or verdict['workspace'] != tree_identity(run / 'workspace'):
            raise ValueError('verdict does not describe this task and workspace')
    record = {'schema_version': 'rwkv-lh.episode-record.v1', 'task_digest': task['digest'],
              'session_id': state['session_id'], 'ledger_tip': tip['digest'],
              'transcript_sha256': exported['sha256'], 'status': state['status'],
              'termination_reason': state['stop_reason'], 'declaration': state['requests'][-1]['declaration'],
              'external_acceptance': 'unverified' if verdict is None else 'passed' if verdict['passed'] else 'failed',
              'verdict_sha256': checksum(verdict) if verdict else None,
              'requests': exported['requests'], 'actions': actions,
              'annotation_authority': 'observed_tool_category_only', 'training_eligible': False}
    target = run / 'record'
    write_immutable(target / 'native_messages.json', exported['bytes'])
    # A post-hoc verifier may add evidence without overwriting the original archive.
    name = 'EPISODE.json' if verdict is None else 'VERIFIED-' + checksum(verdict) + '.json'
    write_immutable(target / name, dump(record).encode())
    return record
