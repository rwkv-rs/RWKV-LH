"""Explicit step ownership for tools in the one current Executor contract."""
WITH_TOOL = 'with_tool'
BEFORE_TOOL = 'before_tool'
CONTROL_ACTIONS = frozenset(('select_step', 'report_step', 'finish_work', 'read_receipt'))


def validate_binding(value):
    if value not in (WITH_TOOL, BEFORE_TOOL):
        raise ValueError('unsupported Executor step binding')
    return value


def tool_steps(payload):
    """All model choices, or the explicit earlier choice for the paired control."""
    binding = validate_binding(payload['step_binding'])
    if binding == BEFORE_TOOL:
        return [payload['current_step']['id']] if payload['current_step'] else []
    return payload['references']['tool_step']['task_id']


def validate_action_binding(payload, name, params):
    binding = validate_binding(payload['step_binding'])
    if name == 'select_step' and binding != BEFORE_TOOL:
        raise ValueError('select the task_id in the workspace tool call')
    if name not in CONTROL_ACTIONS and params.get('task_id') not in tool_steps(payload):
        raise ValueError('workspace tool task_id must be an available explicit step choice')
