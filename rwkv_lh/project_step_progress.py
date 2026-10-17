"""Plan progress is a projection of confirmed tool receipts, never a completion judgment."""
from .project_contracts import work_items, fields, strings, relative_path


def build_step_progress(state):
    steps = []
    for number, task in enumerate(work_items(state), 1):
        receipts = [(key, r) for key, r in state['evidence'].items()
                    if r['kind'] == 'tool' and r['intent'].get('step_id') == task['id']]
        paths = set()
        for _, receipt in receipts:
            metadata = receipt['result'].get('metadata', {})
            if metadata.get('workspace_committed'):
                paths.update(metadata.get('changed_paths', []))
        steps.append({'step': number, 'step_id': task['id'],
            'selected': state['current_step_id'] == task['id'],
            'tool_calls': len(receipts),
            'failed_tool_calls': sum(r['result'].get('success') is False for _, r in receipts),
            'mutation_count': sum(bool(r['result'].get('metadata', {}).get('workspace_committed')) for _, r in receipts),
            'implementation_paths': sorted(paths), 'evidence_ids': [key for key, _ in receipts]})
    return {'steps': steps}


def render_step_progress(progress, *, previous=None):
    from .project_markdown import section
    def rows(value):
        return {row['step_id']: {key: item for key, item in row.items()
                if key not in ('step', 'step_id', 'evidence_ids')}
                for row in value['steps'] if row['selected'] or row['tool_calls']}
    current = rows(progress)
    old = rows(previous) if previous is not None else {}
    changed = {key: value for key, value in current.items() if old.get(key) != value}
    lines = [section('Observed plan steps (updates by step_id; not verified completion)', changed)] if changed else []
    removed = [key for key in old if key not in current]
    if removed:
        lines.append(section('Removed step observations', removed))
    return '\n\n'.join(lines)


def validate_step_progress(progress, *, tasks):
    fields(progress, ('steps',))
    if not isinstance(progress['steps'], list) or len(progress['steps']) != len(tasks):
        raise ValueError('step progress must cover the whole plan')
    for index, (step, task) in enumerate(zip(progress['steps'], tasks), 1):
        fields(step, ('step', 'step_id', 'selected', 'tool_calls', 'failed_tool_calls', 'mutation_count',
                      'implementation_paths', 'evidence_ids'))
        if step['step'] != index or type(step['step']) is not int or step['step_id'] != task['id']:
            raise ValueError('step order or identity differs')
        if type(step['selected']) is not bool:
            raise ValueError('invalid step claim or selection')
        if any(type(step[k]) is not int or step[k] < 0 for k in ('tool_calls', 'failed_tool_calls', 'mutation_count')):
            raise ValueError('invalid observed action counts')
        strings(step['evidence_ids']); strings(step['implementation_paths'])
        if step['tool_calls'] != len(step['evidence_ids']) or max(step['failed_tool_calls'], step['mutation_count']) > step['tool_calls']:
            raise ValueError('action counts differ from receipt count')
        for path in step['implementation_paths']:
            relative_path(path)
    return progress
