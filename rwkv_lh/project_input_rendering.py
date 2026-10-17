"""Literal current-role input rendering, shared by bootstrap and State updates."""
from .project_markdown import section
from .project_action_feedback import action_call, action_origin, render_result, render_action_feedback
from .project_step_progress import render_step_progress
from .project_receipt_refs import render_view
from .project_tool_feedback import model_tool_result

MODEL_VIEW_PROTOCOL = 'rwkv-lh.coder.model-view.v1'


def _render_references(references, previous):
    lines = []
    steps = references['execute_tool']['step_id']
    if previous is None or steps != previous['execute_tool']['step_id']:
        lines.append(section('Available steps', steps))
    receipts = references['read_receipt']['receipt_id']
    if previous is None:
        if receipts:
            lines.append(section('Available receipts (read_receipt and finish_work)', receipts))
    else:
        old = previous['read_receipt']['receipt_id']
        added = [item for item in receipts if item not in old]
        removed = [item for item in old if item not in receipts]
        if added:
            lines.append(section('Newly available receipts', added))
        if removed:
            lines.append(section('Removed receipts', removed))
    return lines


def render_fields(fields, *, previous=None):
    """Deliver every changed semantic field; present each receipt body once."""
    fields = render_view(fields)
    previous = render_view(previous) if previous is not None else {}
    lines = []
    special = {'protocol', 'receipt_bindings', 'selected_evidence', 'next_action',
               'action_feedback', 'evidence_updates', 'observations', 'step_progress', 'references'}
    for key, value in fields.items():
        if key not in special:
            if value is None or value == {} or value == []:
                continue
            lines.append(section(key, value))
    if 'references' in fields:
        lines.extend(_render_references(fields['references'], previous.get('references')))
    if 'step_progress' in fields:
        rendered = render_step_progress(fields['step_progress'], previous=previous.get('step_progress'))
        if rendered:
            lines.append(rendered)
    feedback = fields.get('action_feedback')
    delivered = set()
    if feedback is not None:
        lines.append(render_action_feedback(feedback))
        if feedback['last_execution']:
            delivered.add(feedback['last_execution']['evidence_id'])
    for identifier, receipt in fields.get('evidence_updates', {}).items():
        revision = receipt['delivery_revision']
        delivery = {'evidence_id': identifier, 'delivery_revision': revision}
        if revision > 1:
            delivery.update(explicit_reads=revision - 1, content='same as original receipt')
        lines.append(section('Receipt delivery', delivery))
        if identifier in delivered:
            continue
        lines.extend(['Evidence ' + identifier + ' (data):',
            section('Action', action_call(receipt['intent']))])
        origin = action_origin(receipt['intent'])
        if origin:
            lines.append(section('Origin', origin))
        lines.append(render_result(receipt['raw_result'] if 'raw_result' in receipt else receipt['result']))
        delivered.add(identifier)
    for observation in fields.get('observations', []):
        # The full original body above includes the projected observation.
        if observation.get('evidence_id', observation.get('action_id')) not in delivered:
            lines.append(section('Observation (data)', {
                **observation, 'result': model_tool_result(observation['result'])}))
    return '\n\n'.join(lines)
