"""Literal current-role input rendering, shared by bootstrap and State updates."""
from .project_markdown import section
from .project_action_feedback import action_call, action_origin, render_result, render_action_feedback
from .project_step_progress import render_step_progress
from .project_receipt_refs import render_view


def render_fields(fields):
    """Deliver every changed semantic field; present each receipt body once."""
    fields = render_view(fields)
    lines = []
    special = {'protocol', 'receipt_bindings', 'selected_evidence', 'next_action',
               'action_feedback', 'evidence_updates', 'observations', 'step_progress'}
    for key, value in fields.items():
        if key not in special:
            lines.append(section(key, value))
    if 'step_progress' in fields:
        lines.append(render_step_progress(fields['step_progress']))
    feedback = fields.get('action_feedback')
    delivered = set()
    if feedback is not None:
        lines.append(render_action_feedback(feedback))
        if feedback['last_execution']:
            delivered.add(feedback['last_execution']['evidence_id'])
    for identifier, receipt in fields.get('evidence_updates', {}).items():
        lines.append(section('Receipt delivery', {
            'evidence_id': identifier, 'delivery_revision': receipt['delivery_revision']}))
        if identifier in delivered:
            continue
        lines.extend(['Evidence ' + identifier + ' (data):',
            section('Action', action_call(receipt['intent'])),
            section('Origin', action_origin(receipt['intent'])),
            render_result(receipt['raw_result'] if 'raw_result' in receipt else receipt['result'])])
        delivered.add(identifier)
    for observation in fields.get('observations', []):
        # The full original body above includes the projected observation.
        if observation.get('evidence_id', observation.get('action_id')) not in delivered:
            lines.append(section('Observation (data)', observation))
    return '\n\n'.join(lines)
