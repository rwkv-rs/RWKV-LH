"""Single presentation of each current Project fact, shared by first and delta input.

Builders retain the complete semantic snapshot for validation and trace identity.
Delivery hashes and internal task-state enums stay in that snapshot, not in the
model question. Allowed parameter references, reports and verification facts
express their model-relevant meaning. Nothing truncates a plan, receipt or output.
"""
from copy import deepcopy
from collections import Counter

from .model_io import canonical_json
from .project_action_feedback import action_call, action_origin, render_result, render_action_feedback
from .project_step_progress import render_step_progress

# These are host bookkeeping or redundant identities, not missing observations.
_HOST_FIELDS = {'protocol', 'task_status', 'selected_evidence', 'information_complete', 'evidence_ids'}
_SPECIAL_FIELDS = {'instruction', 'next_decision', 'step_progress', 'action_feedback', 'references',
                   'observations', 'evidence_updates', 'latest_feedback', 'protocol_feedback', 'feedback'}
VERBATIM_ENCODING = 'verbatim-json-values.v2'


def share_verbatim_json(payload):
    """Share exact values with visible references, never null placeholders.

    The reserved reference key is absent from all source data. Each operation
    stays in its original position; only identical complete values share a
    definition. Repeated observation/result structures are covered as well as
    text, and every definition is in this same input. No summarization occurs.
    """
    original = canonical_json(payload)
    marker = 'verbatim_ref'
    while marker in original:
        marker += '_'
    occurrences = Counter()
    def visit(value):
        if isinstance(value, (str, dict, list)):
            encoded = canonical_json(value)
            if len(encoded) >= 128:
                occurrences[encoded] += 1
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(payload)
    candidates = {encoded for encoded, count in occurrences.items()
                  if count > 1 and len(encoded) * (count - 1) > count * (len(marker) + 24) + 32}
    if not candidates:
        return deepcopy(payload)
    names, shared = {}, {}
    def children(value):
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        if isinstance(value, list):
            return [encode(item) for item in value]
        return value
    def encode(value):
        encoded = canonical_json(value) if isinstance(value, (str, dict, list)) else None
        if encoded not in candidates:
            return children(value)
        if encoded not in names:
            name = 'V' + str(len(names) + 1)
            names[encoded] = name
            shared[name] = children(value)
        return {marker: names[encoded]}
    body = encode(payload)
    wire = {'encoding': VERBATIM_ENCODING, 'reference_key': marker,
            'payload': body, 'shared_values': shared}
    from .token_budget import get_token_count
    return wire if get_token_count(canonical_json(wire)) < get_token_count(original) else deepcopy(payload)


def _join_shared_blocks(lines):
    """Factor identical complete blocks within this update; retain every occurrence.

    The original semantic snapshot is untouched. References never depend on a
    previous update or State, and the literal table cannot collide with data.
    """
    original = '\n'.join(lines)
    counts = Counter(lines)
    marker = '@@SHARED'
    while marker in original:
        marker += '_'
    shared = {}
    for block, count in counts.items():
        if count < 2 or len(block) < 128:
            continue
        name = 'B' + str(len(shared) + 1)
        definition = f'{marker} BEGIN {name}\n{block}\n{marker} END {name}'
        reference = f'{marker} REF {name}'
        if len(definition) + count * len(reference) < count * len(block):
            shared[block] = name
    if not shared:
        return original
    result = ['Shared verbatim input blocks; each reference means the exact full block at that position. '
              + canonical_json(marker), marker + ' BODY']
    result.extend(marker + ' REF ' + shared[line] if line in shared else line for line in lines)
    result.append(marker + ' BLOCKS')
    for block, name in shared.items():
        result.extend([marker + ' BEGIN ' + name, block, marker + ' END ' + name])
    result.append(marker + ' END')
    rendered = '\n'.join(result)
    from .token_budget import get_token_count
    return rendered if get_token_count(rendered) < get_token_count(original) else original


def _feedback(value, rejection):
    if not isinstance(value, dict):
        return value
    if rejection and value.get('rejected_operation_id') == rejection['operation_id']:
        return _feedback(value.get('previous_feedback'), rejection)
    result = dict(value)
    if 'protocol_feedback' in result:
        result['protocol_feedback'] = _feedback(result['protocol_feedback'], rejection)
    return result


def _shared_goal_text(fields):
    """Factor only identical goal text, with explicit paths and a visible source.

    Never summarize an interpretation, a report or a receipt. Deltas which do
    not contain the source text keep their full literals: presentation must not
    create a dangling reference to a section absent from this update.
    """
    view = dict(fields)
    shared = []
    for source, section in (('request', 'goal'), ('original_request', 'assignment')):
        original = fields.get(source)
        if not isinstance(original, str) or not original or not fields.get(section):
            continue
        value = deepcopy(fields[section])
        paths = []

        def factor(parent, key, path):
            if parent.get(key) == original:
                del parent[key]
                paths.append(path)

        if section == 'goal':
            factor(value, 'request', 'goal.request')
        else:
            for key in ('objective', 'completion'):
                factor(value['task'], key, 'assignment.task.' + key)
            for number, requirement in enumerate(value['requirements']):
                factor(requirement, 'text', f'assignment.requirements[{number}].text')
            handoff = value.get('local_context', {}).get('decision_handoff')
            if isinstance(handoff, dict):
                factor(handoff, 'text', 'assignment.local_context.decision_handoff.text')
        if paths:
            view[section] = value
            shared.append({'source': source, 'equal_fields': paths})
    return view, shared


def render_fields(fields):
    """Render a whole semantic snapshot or set-fields of an exact input delta."""
    lines = []
    from .project_receipt_refs import render_view
    fields = render_view(fields)
    fields, shared = _shared_goal_text(fields)
    # The authority precedes any task interpretation or reference to its text.
    for key in ('request', 'original_request'):
        if key in fields:
            lines.append(key + ': ' + canonical_json(fields[key]))
    adjacent = fields.get('action_feedback') or {}
    last = adjacent.get('last_execution')
    rejected = adjacent.get('rejected_call')
    last_id = last['evidence_id'] if last else None
    rejected_id = rejected['operation_id'] if rejected else None
    for key, value in fields.items():
        if key in _HOST_FIELDS or key in _SPECIAL_FIELDS or key in ('request', 'original_request'):
            continue
        if key == 'boundary':
            lines.append('Current question: ' + value['question'])
            continue  # options reappear once, typed by parameter, in references below.
        if key == 'active' and value is not None:
            # The full task and requirement text already live in the untruncated plan.
            value = {name: item for name, item in value.items() if name not in ('task', 'requirements')}
            value = {**value, 'task_id': fields[key]['task']['id']}
        label = ('Worker reports (claims; submitted is not verified)' if key == 'reports'
                 else 'Independent verification facts' if key == 'verification'
                 else 'Explicit goal acceptance' if key == 'acceptance' else key)
        lines.append(label + ': ' + canonical_json(value))
    if shared:
        lines.append('Verbatim shared text (each equal_fields path has exactly its source text): '
                     + canonical_json(shared))
    for key in ('latest_feedback', 'protocol_feedback', 'feedback'):
        value = _feedback(fields.get(key), rejected)
        if not value:
            continue
        if (last_id is not None and isinstance(value, dict) and value.get('evidence_id') == last_id
                and value.get('kind') in ('tool_returned', 'execution_failed')):
            # Same confirmed action/result appears intact in the adjacent section.
            continue
        if (last is not None and isinstance(value, dict) and value.get('kind') == 'verification'
                and value.get('checks') == last['result'].get('checks')):
            value = {key: item for key, item in value.items() if key != 'checks'}
        if value in fields.get('reports', {}).values():
            continue
        lines.append('Control feedback (not an execution fact): ' + canonical_json(value))
    for identifier, receipt in fields.get('evidence_updates', {}).items():
        if identifier in (last_id, rejected_id):
            continue
        lines.append('Evidence ' + identifier + ' (data):')
        if 'intent' in receipt and ('raw_result' in receipt or 'result' in receipt):
            lines.extend(['Action: ' + canonical_json(action_call(receipt['intent'])),
                          'Origin: ' + canonical_json(action_origin(receipt['intent'])),
                          render_result(receipt.get('raw_result', receipt.get('result'))),
                          'Receipt attributes: ' + canonical_json({key: value for key, value in receipt.items()
                              if key not in ('intent', 'raw_result', 'result')})])
        else:
            lines.append(canonical_json(receipt))
    for observation in fields.get('observations', []):
        if last_id is not None and observation.get('action_id') == last_id:
            continue
        lines.append('Tool observation (data): ' + canonical_json(observation))
    if adjacent:
        lines.append(render_action_feedback(adjacent))
    if 'step_progress' in fields:
        lines.append(render_step_progress(fields['step_progress']))
        lines.append('已做 means a confirmed tool action occurred, including failures. It is not report_work.status or goal acceptance.')
    if 'references' in fields:
        role = adjacent.get('receiving_role')
        note = ('only listed Decision directions are available; empty advice lists mean use []'
                if role == 'decision' else 'receipt references for these functions; other tools keep their declared schemas')
        lines.append('Current parameter references (' + note + '): ' + canonical_json(fields['references']))
    return _join_shared_blocks(lines)
