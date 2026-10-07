"""Validated project contracts. Models own semantics; this module owns structure."""
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath

PLAN_PROTOCOL = 'rwkv-lh.project-plan.v5'
ASSIGNMENT_PROTOCOL = 'rwkv-lh.project-assignment.v6'
GOAL_PROTOCOL = 'rwkv-lh.project-user-goal.v1'
GOAL_ID = 'original-goal'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError(f'contract fields must be {sorted(required)}')


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty text required')
    return value


def strings(value, *, empty=True):
    if not isinstance(value, list) or (not empty and not value):
        raise ValueError('text array required')
    for item in value:
        text(item)
    if len(set(value)) != len(value):
        raise ValueError('duplicate identifiers')
    return value


def resource_budget(value=None):
    """A shared resource fact; absent standalone-fixture budgets remain unknown."""
    import math
    if value is None:
        return {'calls': None, 'seconds': None}
    fields(value, ('calls', 'seconds'))
    calls, seconds = value['calls'], value['seconds']
    if calls is not None and (type(calls) is not int or calls < 0):
        raise ValueError('remaining calls must be nonnegative or unknown')
    if seconds is not None and (type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0):
        raise ValueError('remaining seconds must be finite nonnegative or unknown')
    return deepcopy(value)


def relative_path(value):
    text(value)
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or '\\' in value or '\x00' in value:
        raise ValueError('workspace-relative path required')
    return value


def scope_path(value, *, field=None):
    """A plan scope is path authority, so require explicit path syntax."""
    try:
        relative_path(value)
        if value != '.' and (not value.startswith('./') or PurePosixPath(value) == PurePosixPath('.')):
            raise ValueError("scope path must be '.' or start with './'")
    except ValueError as exc:
        if field is not None:
            raise ValueError(f'{field}: invalid path {value!r}: {exc}') from exc
        raise
    return value


def selected_task_advice(state, task_id, advice_ids):
    """Same reference check for precommit validation and ledger mutation."""
    strings(list(advice_ids))
    selected = []
    for key in advice_ids:
        advice = state['advice'].get(key)
        if not advice or advice['subject_id'] != task_id:
            allowed = [identifier for identifier, item in state['advice'].items() if item['subject_id'] == task_id]
            raise ValueError(f'params.advice_ids: diagnostic advice must reference this task; '
                             f'task {task_id!r}, invalid {key!r}, permitted {allowed!r}')
        selected.append({'id': key, **deepcopy(advice)})
    return selected


def require_current_verification(state, task_id, verification_id, workspace_digest):
    receipt = state['verification'].get(task_id)
    if (state['active'] or state.get('pending') or not receipt or receipt['status'] != 'passed'
            or receipt['operation_id'] != verification_id
            or receipt['workspace_digest'] != workspace_digest
            or receipt['task_digest'] != digest(work_map(state).get(task_id))
            or state['task_status'].get(task_id) != 'checks_passed'):
        raise ValueError('acceptance requires current passed verification')


def make_check(check_id, argv, *, cwd='.', purpose='Verify the task contract'):
    result = {'id': check_id, 'argv': list(argv), 'cwd': cwd, 'purpose': purpose}
    validate_check(result)
    return result


def validate_check(value):
    fields(value, ('id', 'argv', 'cwd', 'purpose'))
    text(value['id']); text(value['purpose']); relative_path(value['cwd'])
    if not isinstance(value['argv'], list) or not value['argv']:
        raise ValueError('check argv required')
    for item in value['argv']:
        if not isinstance(item, str) or '\x00' in item:
            raise ValueError('invalid argv')
    text(value['argv'][0])
    from .project_check_contract import validate_literal_syntax
    validate_literal_syntax(value['argv'], check_id=value['id'])
    return value


def make_task(task_id, stage, objective, requirements, *, dependencies=(), checks=(),
              interfaces=(), scope=('.',), completion='All declared checks pass for this objective'):
    return {'id': task_id, 'stage': stage, 'objective': objective,
        'requirements': list(requirements), 'dependencies': list(dependencies),
        'checks': deepcopy(list(checks)), 'interfaces': list(interfaces),
        'scope': list(scope), 'completion': completion}


def make_plan(requirements, tasks, *, rationale, protected_paths=()):
    return validate_plan({'protocol': PLAN_PROTOCOL, 'requirements': deepcopy(requirements),
                          'tasks': deepcopy(tasks), 'rationale': rationale,
                          'protected_paths': list(protected_paths)})


def validate_plan(value):
    fields(value, ('protocol', 'requirements', 'tasks', 'rationale', 'protected_paths'))
    if value['protocol'] != PLAN_PROTOCOL:
        raise ValueError('unsupported plan protocol')
    text(value['rationale'])
    strings(value['protected_paths'])
    for index, path in enumerate(value['protected_paths']):
        scope_path(path, field=f'protected_paths[{index}]')
    if not isinstance(value['requirements'], list) or not value['requirements']:
        raise ValueError('requirements required')
    requirements = {}
    for requirement in value['requirements']:
        fields(requirement, ('id', 'text'))
        key = text(requirement['id']); text(requirement['text'])
        if key in requirements:
            raise ValueError('duplicate requirement')
        requirements[key] = requirement['text']
    if not isinstance(value['tasks'], list) or not value['tasks']:
        raise ValueError('tasks required')
    tasks, checks, covered = {}, set(), set()
    for task in value['tasks']:
        fields(task, ('id', 'stage', 'objective', 'requirements', 'dependencies',
                      'checks', 'interfaces', 'scope', 'completion'))
        for key in ('id', 'stage', 'objective', 'completion'):
            text(task[key])
        if task['id'] in tasks:
            raise ValueError('duplicate task')
        if task['id'] == GOAL_ID:
            raise ValueError('plan task cannot replace the original goal identity')
        for key in ('requirements', 'dependencies', 'interfaces', 'scope'):
            strings(task[key], empty=key in ('dependencies', 'interfaces'))
        if set(task['requirements']) - requirements.keys():
            raise ValueError('unknown requirement')
        covered.update(task['requirements'])
        for index, path in enumerate(task['scope']):
            scope_path(path, field=f"tasks[{task['id']}].scope[{index}]")
        if not isinstance(task['checks'], list):
            raise ValueError('public completion checks must be a list')
        for check in task['checks']:
            validate_check(check)
            if check['id'] in checks:
                raise ValueError('duplicate check identity')
            checks.add(check['id'])
        tasks[task['id']] = task
    if covered != requirements.keys():
        raise ValueError('uncovered requirements: ' + ', '.join(sorted(requirements.keys() - covered)))
    for task in tasks.values():
        if set(task['dependencies']) - tasks.keys():
            raise ValueError('unknown dependency')
    # Iterative topological validation: no arbitrary plan length or recursion cap.
    waiting = {key: set(task['dependencies']) for key, task in tasks.items()}
    resolved = set()
    while waiting:
        ready = {key for key, deps in waiting.items() if deps <= resolved}
        if not ready:
            raise ValueError('dependency cycle')
        resolved.update(ready)
        waiting = {key: deps for key, deps in waiting.items() if key not in ready}
    return deepcopy(value)


def task_map(plan):
    return {task['id']: task for task in plan['tasks']}


def make_goal(request, protected_paths=()):
    """Record user authority verbatim; this creates no plan or chosen action."""
    return {'protocol': GOAL_PROTOCOL, 'id': GOAL_ID, 'request': text(request),
            'scope': ['.'], 'protected_paths': list(protected_paths)}


def validate_goal(goal):
    fields(goal, ('protocol', 'id', 'request', 'scope', 'protected_paths'))
    if goal['protocol'] != GOAL_PROTOCOL or goal['id'] != GOAL_ID:
        raise ValueError('unsupported user goal contract')
    text(goal['request'])
    for key in ('scope', 'protected_paths'):
        strings(goal[key], empty=key == 'protected_paths')
        for path in goal[key]:
            scope_path(path)
    return goal


def work_items(state):
    """Project either optional decomposition or the verbatim goal to the shared work contract.

    The goal is not installed into plan.tasks and receives no fabricated review.
    Only a model decision may delegate it; proof is bound separately after work.
    """
    if state['plan'] is not None:
        return deepcopy(state['plan']['tasks'])
    goal = validate_goal(state['goal'])
    return [make_task(goal['id'], 'original_goal', goal['request'], [goal['id']],
        scope=goal['scope'], completion=goal['request'], checks=state['goal_checks'])]


def work_map(state):
    return {item['id']: item for item in work_items(state)}


def affected_work(tasks, changed):
    """Contracts and their transitive dependents share one invalidation closure."""
    affected = set(changed)
    while True:
        expanded = affected | {t['id'] for t in tasks if set(t['dependencies']) & affected}
        if expanded == affected:
            return affected
        affected = expanded


def work_requirements(state, task):
    if task['id'] == GOAL_ID:
        return [{'id': GOAL_ID, 'text': state['goal']['request']}]
    return [r for r in state['plan']['requirements'] if r['id'] in task['requirements']]


def protected_paths(state):
    paths = state['goal']['protected_paths']
    if state['plan'] is not None:
        paths = [*paths, *state['plan']['protected_paths']]
    return list(dict.fromkeys(paths))


def work_check_context(state):
    task = work_map(state)[state['planner_subject_id']]
    return {'goal': deepcopy(state['goal']), 'task': task,
        'requirements': deepcopy(work_requirements(state, task)),
        'worker_report': deepcopy(state['reports'].get(task['id'])),
        'candidate': deepcopy(state['pending_checks'])}


def make_assignment(task, *, assignment_id, plan_version, workspace_digest, dependencies, requirements):
    return {'protocol': ASSIGNMENT_PROTOCOL, 'id': assignment_id,
        'origin': 'user_goal' if task['id'] == GOAL_ID else 'planned_task',
        'plan_version': plan_version, 'task': deepcopy(task), 'contract_digest': digest(task),
        'workspace_digest': workspace_digest, 'dependencies': deepcopy(dependencies),
        'requirements': deepcopy(requirements)}


def assignment_dependencies_resumable(state, assignment):
    """Continue an existing contract without granting new or final acceptance.

    A confirmed write invalidates workspace-bound checks. It must not deadlock
    the assignment that made that write. Its delegation snapshots may bridge
    only stale evidence for unchanged dependency contracts, never failed checks
    or a revised/unverified prerequisite. Final acceptance remains workspace-bound.
    """
    tasks = work_map(state)
    snapshots = {item['task_id']: item['verification'] for item in assignment['dependencies']}
    for key in assignment['task']['dependencies']:
        task = tasks.get(key)
        if task is None:
            return False
        status = state['task_status'].get(key)
        if status == 'verified':
            continue
        prior = snapshots.get(key, {})
        current = state['verification'].get(key, {})
        if not (status == 'awaiting_verification' and current.get('status') == 'stale'
                and prior.get('status') == 'passed'
                and prior.get('task_digest') == current.get('task_digest') == digest(task)):
            return False
    return True
