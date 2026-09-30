"""Two-state execution progress: 已做 / 未做, independent of check success."""
from .project_contracts import digest, work_items


def build_step_progress(state, *, assignment=None):
    """A confirmed returned tool action marks its current-contract step 已做."""
    if state is None:
        tasks = [assignment['task']] if assignment else []
        return {'steps': [{'step': number, 'task_id': task['id'], 'status': '未做',
                          'implementation_paths': [], 'evidence_ids': []}
                         for number, task in enumerate(tasks, 1)]}
    tasks = work_items(state)
    assignments = {item['id']: item for item in state.get('suspended', {}).values()}
    if state['active']:
        assignments[state['active']['id']] = state['active']
    for receipt in state['evidence'].values():
        intent = receipt['intent']
        if receipt['kind'] == 'model' and intent.get('role') == 'executor':
            original = intent['input']['assignment']
            assignments[original['id']] = original
    steps = []
    for number, task in enumerate(tasks, 1):
        if assignment is not None and task['id'] != assignment['task']['id']:
            continue
        matching = {key for key, value in assignments.items()
                    if value['task']['id'] == task['id'] and value['contract_digest'] == digest(task)}
        if assignment is not None:
            matching &= {assignment['id']}
        receipts = [(key, value) for key, value in state['evidence'].items()
                    if value['kind'] == 'tool' and value['intent']['assignment_id'] in matching]
        paths = set()
        for _, receipt in receipts:
            metadata = receipt['result'].get('metadata', {})
            if metadata.get('workspace_committed') is True:
                paths.update(metadata.get('changed_paths', []))
        steps.append({'step': number, 'task_id': task['id'],
                      'status': '已做' if receipts else '未做',
                      'implementation_paths': sorted(paths),
                      'evidence_ids': [key for key, _ in receipts]})
    return {'steps': steps}


def render_step_progress(progress):
    from .model_io import canonical_json
    lines = ['Steps:']
    for step in progress['steps']:
        # Paths and usable receipt IDs are facts, not additional step states.
        lines.append(f"step{step['step']}（{step['status']}）：" + canonical_json({
            'task_id': step['task_id'], 'implementation_paths': step['implementation_paths'],
            'evidence_ids': step['evidence_ids']}))
    return '\n'.join(lines)


def validate_step_progress(progress, *, tasks=None, assignment=None, evidence_ids=None):
    """Validate the display shape; original ledger re-extraction proves its facts."""
    from .project_contracts import fields, relative_path, strings
    fields(progress, ('steps',))
    if not isinstance(progress['steps'], list):
        raise ValueError('step progress requires an array')
    expected = [assignment['task']] if assignment is not None else tasks
    if expected is not None and len(progress['steps']) != len(expected):
        raise ValueError('step progress must cover its complete task scope')
    for index, step in enumerate(progress['steps']):
        fields(step, ('step','task_id','status','implementation_paths','evidence_ids'))
        if type(step['step']) is not int or step['step'] < 1:
            raise ValueError('positive step number required')
        if assignment is None and step['step'] != index + 1:
            raise ValueError('plan step order differs')
        if expected is not None and step['task_id'] != expected[index]['id']:
            raise ValueError('step task differs from current scope')
        strings(step['implementation_paths'])
        strings(step['evidence_ids'])
        for path in step['implementation_paths']:
            relative_path(path)
        if step['status'] != ('已做' if step['evidence_ids'] else '未做'):
            raise ValueError('step status must be 已做 with receipts or 未做 without receipts')
        if not step['evidence_ids'] and step['implementation_paths']:
            raise ValueError('implementation paths require a confirmed receipt')
        if evidence_ids is not None and set(step['evidence_ids']) - set(evidence_ids):
            raise ValueError('step receipt is not in the current evidence catalog')
    return progress
