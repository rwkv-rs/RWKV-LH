"""Plan progress is a projection of confirmed tool receipts, never a completion judgment."""
from .project_contracts import work_items, fields, strings, relative_path


def _check_observations(state, checks):
    """Latest root-directory run_shell of each literal plan check; the host never runs it."""
    ordered = [(key, r) for key, r in state['evidence'].items() if r['kind'] == 'tool']
    observed = []
    for command in checks:
        runs = [index for index, (_, r) in enumerate(ordered) if r['intent'].get('name') == 'run_shell'
                and r['intent'].get('arguments', {}).get('command') == command
                and r['intent']['arguments'].get('cwd', '.') in ('.', './')]
        row = {'command': command, 'runs': len(runs), 'last_receipt_id': None, 'last_exit_code': None,
               'last_success': None, 'workspace_changed_since': None}
        if runs:
            key, receipt = ordered[runs[-1]]
            row.update(last_receipt_id=key, last_exit_code=receipt['result'].get('exit_code'),
                       last_success=receipt['result'].get('success') is True,
                       workspace_changed_since=any(bool(r['result'].get('metadata', {}).get('workspace_committed'))
                                                   for _, r in ordered[runs[-1] + 1:]))
        observed.append(row)
    return observed


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
            'implementation_paths': sorted(paths), 'evidence_ids': [key for key, _ in receipts],
            'checks': _check_observations(state, task['checks'])})
    return {'steps': steps}


def render_step_progress(progress, *, previous=None):
    from .project_markdown import section
    def view(key, item):
        if key != 'checks':
            return item
        # The commands are in the plan; only run checks carry observations.
        return [{k: v for k, v in check.items() if v is not None} for check in item if check['runs']]
    def rows(value):
        return {row['step_id']: {key: view(key, item) for key, item in row.items()
                if key not in ('step', 'step_id', 'evidence_ids') and not (key == 'checks' and not view(key, item))}
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
                      'implementation_paths', 'evidence_ids', 'checks'))
        if not isinstance(step['checks'], list) or [c.get('command') if isinstance(c, dict) else None
                                                   for c in step['checks']] != task['checks']:
            raise ValueError('check observations differ from the plan checks')
        for check in step['checks']:
            fields(check, ('command', 'runs', 'last_receipt_id', 'last_exit_code', 'last_success',
                           'workspace_changed_since'))
            if type(check['runs']) is not int or check['runs'] < 0:
                raise ValueError('invalid check run count')
            ran = check['runs'] > 0
            if (ran != isinstance(check['last_receipt_id'], str) or ran != (type(check['last_success']) is bool)
                    or ran != (type(check['workspace_changed_since']) is bool)
                    or (check['last_exit_code'] is not None and (type(check['last_exit_code']) is not int or not ran))):
                raise ValueError('invalid check observation')
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
