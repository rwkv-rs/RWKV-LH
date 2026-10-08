"""Validated project contracts. Models own semantics; this module owns structure."""
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath

PLAN_PROTOCOL = 'rwkv-lh.project-plan.v6'
ASSIGNMENT_PROTOCOL = 'rwkv-lh.project-assignment.v7'
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


def make_task(task_id, stage, objective, requirements, *, dependencies=(), interfaces=(),
              scope=('.',), completion='Deliver the stated objective'):
    return {'id': task_id, 'stage': stage, 'objective': objective, 'requirements': list(requirements),
        'dependencies': list(dependencies), 'interfaces': list(interfaces),
        'scope': list(scope), 'completion': completion}


def make_plan(requirements, tasks, *, rationale, protected_paths=()):
    return validate_plan({'protocol': PLAN_PROTOCOL, 'requirements': deepcopy(requirements),
        'tasks': deepcopy(tasks), 'rationale': rationale, 'protected_paths': list(protected_paths)})


def validate_plan(value):
    fields(value, ('protocol', 'requirements', 'tasks', 'rationale', 'protected_paths'))
    if value['protocol'] != PLAN_PROTOCOL:
        raise ValueError('unsupported plan protocol')
    text(value['rationale']); strings(value['protected_paths'])
    for path in value['protected_paths']:
        scope_path(path)
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
    tasks, covered = {}, set()
    for task in value['tasks']:
        fields(task, ('id', 'stage', 'objective', 'requirements', 'dependencies', 'interfaces', 'scope', 'completion'))
        for key in ('id', 'stage', 'objective', 'completion'):
            text(task[key])
        if task['id'] in tasks or task['id'] == GOAL_ID:
            raise ValueError('duplicate or reserved task identity')
        for key in ('requirements', 'dependencies', 'interfaces', 'scope'):
            strings(task[key], empty=key in ('dependencies', 'interfaces'))
        if set(task['requirements']) - requirements.keys():
            raise ValueError('unknown requirement')
        covered.update(task['requirements'])
        for index, path in enumerate(task['scope']):
            scope_path(path, field=f"tasks[{task['id']}].scope[{index}]")
        tasks[task['id']] = task
    if covered != requirements.keys():
        raise ValueError('uncovered requirements: ' + ', '.join(sorted(requirements.keys() - covered)))
    for task in tasks.values():
        if set(task['dependencies']) - tasks.keys():
            raise ValueError('unknown dependency')
    waiting, resolved = {key: set(t['dependencies']) for key, t in tasks.items()}, set()
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
    return deepcopy(state['plan']['tasks']) if state['plan'] is not None else []


def work_map(state):
    return {item['id']: item for item in work_items(state)}


def protected_paths(state):
    paths = state['goal']['protected_paths']
    if state['plan'] is not None:
        paths = [*paths, *state['plan']['protected_paths']]
    return list(dict.fromkeys(paths))


def make_assignment(goal, *, assignment_id, plan_version, workspace_digest):
    # This stable project contract outlives step focus changes.
    task = make_task(GOAL_ID, 'project', goal['request'], [GOAL_ID], scope=goal['scope'],
                     completion=goal['request'])
    return {'protocol': ASSIGNMENT_PROTOCOL, 'id': assignment_id, 'task': task,
            'contract_digest': digest(task), 'plan_version': plan_version,
            'workspace_digest': workspace_digest, 'protected_paths': list(goal['protected_paths'])}
