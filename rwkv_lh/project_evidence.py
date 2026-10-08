"""Shared evidence stream projection for production and exact trace replay."""
from copy import deepcopy
from .project_contracts import digest


def select_evidence(state, lane, identifier, evidence):
    """Queue exact evidence; delivery is committed with the receiving checkpoint."""
    selected = state['selected_evidence'].setdefault(lane, {})
    revision = selected.get(identifier, {}).get('revision', 0) + 1
    selected[identifier] = {'revision': revision, 'evidence': deepcopy(evidence)}


def publish_decision_receipt(state, identifier, *, raw_result=None):
    """Push an observed receipt, not a guessed next action, into Decision's lane."""
    from .project_protocols.decision import LANE
    receipt = state['evidence'][identifier]
    if receipt['kind'] == 'model':
        raise ValueError('model output is not an execution receipt')
    select_evidence(state, LANE, identifier, {
        'kind': receipt['kind'], 'intent': receipt['intent'],
        'raw_result': receipt['result'] if raw_result is None else raw_result,
        'is_execution_evidence': True})


def evidence_stream(state, lane):
    selected = state['selected_evidence'].get(lane, {})
    delivered = state['input_delivery'].get(lane, {}).get('evidence', {}) if lane in state['sessions'] else {}
    index = {key: {'digest': digest(item['evidence']), 'revision': item['revision']}
             for key, item in selected.items()}
    updates = {key: deepcopy(item['evidence']) for key, item in selected.items()
               if delivered.get(key) != item['revision']}
    return index, updates


def executor_observations(state):
    lane = state['active']['id']
    delivered = state['input_delivery'].get(lane, {}).get('observations', []) if lane in state['sessions'] else []
    return [{'action_id': key, 'result': deepcopy(value['result'])} for key, value in state['evidence'].items()
        if value['kind'] == 'tool' and value['intent']['assignment_id'] == lane and key not in delivered]


def record_delivery(state, lane, payload):
    delivered = state['input_delivery'].setdefault(lane, {'observations': [], 'evidence': {}})
    delivered['observations'] += [item['action_id'] for item in payload.get('observations', [])]
    delivered['evidence'].update({key: item['revision'] for key, item in payload.get('selected_evidence', {}).items()})


def executor_evidence_ids(state):
    active = state['active']
    allowed = {key for key, item in state['evidence'].items()
               if item['kind'] == 'tool' and item['intent']['assignment_id'] == active['id']}
    for dep in active['dependencies']:
        allowed.add(dep['verification']['operation_id'])
        allowed.update((dep.get('report') or {}).get('evidence_ids', []))
    allowed.update(active.get('local_context', {}).get('shared_evidence_ids', []))
    return allowed


def task_handoff_evidence_ids(state, task_id):
    """Current-task/dependency receipts, not model claims or implicit read authority."""
    from .project_contracts import work_map
    tasks = work_map(state)
    task = tasks.get(task_id)
    if task is None:
        return []
    workers = list(state.get('suspended', {}).values())
    if state.get('active'):
        workers.append(state['active'])
    workers.extend(receipt['intent']['input']['assignment'] for receipt in state['evidence'].values()
                   if receipt['kind'] == 'model' and receipt['intent'].get('role') == 'executor')
    lanes = {worker['id'] for worker in workers
             if worker['task']['id'] == task_id and worker['contract_digest'] == digest(task)}
    allowed = set()
    for dep in task['dependencies']:
        verification = state['verification'].get(dep, {})
        if verification.get('operation_id'):
            allowed.add(verification['operation_id'])
        allowed.update(state['reports'].get(dep, {}).get('evidence_ids', []))
    for identifier, receipt in state['evidence'].items():
        intent = receipt['intent']
        if (receipt['kind'] == 'tool' and intent['assignment_id'] in lanes
                or receipt['kind'] == 'verification' and intent['task_id'] == task_id
                   and intent.get('checks') == task['checks']):
            allowed.add(identifier)
    return [key for key, receipt in state['evidence'].items()
            if key in allowed and receipt['kind'] != 'model']


def validate_handoff(handoff, permitted):
    from .project_contracts import fields, text, strings
    fields(handoff, ('text', 'evidence_ids'))
    text(handoff['text'])
    strings(handoff['evidence_ids'])
    if set(handoff['evidence_ids']) - set(permitted):
        raise ValueError(f'params.handoff.evidence_ids: only current-task/dependency receipts '
                         f'and workspace reads are permitted: {list(permitted)!r}')


def install_decision_handoff(state, assignment, handoff):
    """Bind an explicit suggestion to its actual Decision call, and queue original receipts."""
    task_id = assignment['task']['id']
    permitted = task_handoff_evidence_ids(state, task_id)
    if handoff is None:
        assignment['local_context']['decision_handoff'] = None
        return
    validate_handoff(handoff, permitted)
    inbox = state.get('inbox') or {}
    operation = inbox.get('operation_id')
    source = state['evidence'].get(operation, {})
    command = inbox.get('command', {})
    if (inbox.get('role') != 'decision' or source.get('intent', {}).get('role') != 'decision'
            or source.get('result', {}).get('command') != command
            or command.get('function') not in ('delegate', 'continue_current')
            or command.get('params', {}).get('task_id') != task_id
            or command.get('params', {}).get('handoff') != handoff):
        raise ValueError('decision handoff requires its original model operation')
    assignment['local_context']['decision_handoff'] = {
        **deepcopy(handoff), 'authority': 'decision_suggestion', 'task_id': task_id,
        'contract_digest': assignment['contract_digest'], 'source_operation_id': operation}
    shared = assignment['local_context'].setdefault('shared_evidence_ids', [])
    shared.extend(key for key in handoff['evidence_ids'] if key not in shared)
    from .project_protocols.decision import LANE
    for identifier in handoff['evidence_ids']:
        receipt = state['evidence'][identifier]
        original = state['selected_evidence'].get(LANE, {}).get(identifier, {}).get('evidence')
        select_evidence(state, assignment['id'], identifier, original if original is not None else {
            'kind': receipt['kind'], 'intent': receipt['intent'], 'raw_result': receipt['result'],
            'is_execution_evidence': True})
