"""Work-order contract and the host's ledger-fact report.

The planner issues one work order at a time and receives a report built only
from confirmed ledger facts. The report calls no model, judges no correctness
and gates no completion; it states what the checks exited with, what was
actually committed and what budget remains. Work-order granularity is the
autonomy dial: the same contract carries a single-file order today and a whole
feature once the Executor earns it.
"""
from copy import deepcopy

from .project_contracts import GOAL_ID, digest, fields, scope_path, strings, text

ORDER_PROTOCOL = 'rwkv-lh.coder.work-order.v1'
REPORT_PROTOCOL = 'rwkv-lh.coder.work-order-report.v1'
STDERR_TAIL_CHARS = 2000


def order_schema(path_schema, text_schema, texts_schema):
    """One schema shared by the planner tool, the decoder and validation."""
    def obj(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties),
                'additionalProperties': False}
    return obj({
        'protocol': {'type': 'string', 'enum': [ORDER_PROTOCOL]},
        'id': {**deepcopy(text_schema), 'description': 'Unique work-order identifier within this project.'},
        'goal': {**deepcopy(text_schema), 'description': 'What this work order must achieve, faithful to the original request.'},
        'scope': {**deepcopy(texts_schema), 'items': deepcopy(path_schema),
                  'description': 'Permitted literal write paths. Empty means read-only; it grants no write authority.'},
        'checks': {**deepcopy(texts_schema),
                   'description': 'Literal run_shell commands, run from the workspace root, whose exit code 0 shows the '
                                  'expected behavior once implemented; empty when no command check applies. The Executor '
                                  'decides whether and when to run them; the host never runs or judges them.'},
        'call_budget': {'type': 'integer', 'minimum': 1,
                        'description': 'Maximum Executor model calls for this work order. Exhaustion interrupts the '
                                       'order; it is never a completion.'}})


def validate_order(value, *, issued_ids=(), total_remaining_calls=None):
    """Structure, identity and budget only; the host never judges whether the order is right."""
    fields(value, ('protocol', 'id', 'goal', 'scope', 'checks', 'call_budget'))
    if value['protocol'] != ORDER_PROTOCOL:
        raise ValueError('unsupported work order protocol')
    identifier = text(value['id'])
    if identifier == GOAL_ID or identifier in set(issued_ids):
        raise ValueError('duplicate or reserved work order identity')
    text(value['goal'])
    strings(value['scope'], empty=True)
    strings(value['checks'], empty=True)
    for path in value['scope']:
        scope_path(path)
    if type(value['call_budget']) is not int or value['call_budget'] < 1:
        raise ValueError('work order call_budget must be a positive integer')
    if total_remaining_calls is not None and value['call_budget'] > total_remaining_calls:
        raise ValueError('work order call_budget exceeds the remaining project budget')
    return deepcopy(value)


def _check_facts(order, receipts):
    """Project confirmed run_shell receipts onto this order's literal checks.

    A check counts only when the command text matches literally and the receipt
    is a confirmed workspace-root run. Similar-but-different commands never
    count, and a zero exit proves the command exited zero, not that the order
    is complete.
    """
    facts = []
    for command in order['checks']:
        runs = [r for r in receipts if r.get('name') == 'run_shell'
                and r.get('command') == command and r.get('confirmed')]
        latest = runs[-1] if runs else None
        fact = {'command': command, 'runs': len(runs), 'exit_code': None,
                'stderr_tail': '', 'receipt_id': None}
        if latest is not None:
            stderr = str(latest.get('stderr') or '')
            fact.update(exit_code=latest.get('exit_code'), receipt_id=latest.get('receipt_id'),
                        stderr_tail=stderr[-STDERR_TAIL_CHARS:])
        facts.append(fact)
    return facts


def build_report(order, *, receipts, committed_paths, calls_used, declaration,
                 remaining=None, interrupted_reason=''):
    """Render one report from confirmed facts only.

    `declaration` is the Executor's own ending text. It is carried verbatim and
    labelled as a declaration; the host neither validates nor rewrites it, and
    an ending declaration is never acceptance.
    """
    validate_order(order)
    report = {
        'protocol': REPORT_PROTOCOL,
        'work_order_id': order['id'],
        'checks': _check_facts(order, receipts),
        'committed_paths': sorted(set(committed_paths)),
        'calls_used': int(calls_used),
        'call_budget': order['call_budget'],
        'executor_declaration': deepcopy(declaration) if declaration else None,
        'interrupted_reason': str(interrupted_reason or ''),
    }
    if remaining is not None:
        report['project_remaining'] = {'calls': int(remaining['calls']), 'seconds': int(remaining['seconds'])}
    report['report_digest'] = digest({k: v for k, v in report.items() if k != 'report_digest'})
    return report


def validate_report(value):
    expected = ('protocol', 'work_order_id', 'checks', 'committed_paths', 'calls_used', 'call_budget',
                'executor_declaration', 'interrupted_reason', 'report_digest')
    present = tuple(k for k in expected if k in value)
    fields(value, present + (('project_remaining',) if 'project_remaining' in value else ()))
    if value['protocol'] != REPORT_PROTOCOL:
        raise ValueError('unsupported work order report protocol')
    if value['report_digest'] != digest({k: v for k, v in value.items() if k != 'report_digest'}):
        raise ValueError('work order report digest differs')
    return deepcopy(value)
