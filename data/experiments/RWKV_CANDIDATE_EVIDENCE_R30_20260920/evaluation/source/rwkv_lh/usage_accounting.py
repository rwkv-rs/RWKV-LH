"""Offline accounting of recorded usage, never an inference or acceptance signal.

Rates are caller-supplied uniform token rates in one explicit currency; no live
pricing is guessed. Native logical context lengths are not physical GPU cost.
"""
import json
import hashlib
import math
from pathlib import Path


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _put(table, key, value):
    if key in table and table[key] != value:
        raise ValueError('conflicting duplicate usage identity: ' + str(key))
    table[key] = value


def summarize_usage(traces, *, rates=None, currency=None):
    rates = rates or {}
    if rates and (not isinstance(currency, str) or not currency.strip()):
        raise ValueError('rate currency required')
    for rate in rates.values():
        for field in ('input_per_million', 'output_per_million'):
            value = rate.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid uniform token rate')
    starts, returned, requests, attempts, envelopes = set(), {}, set(), set(), {}
    for records in traces.values():
        for event in records:
            kind = event.get('type')
            if kind in ('model_session_generation_started', 'model_session_generation_returned'):
                key = event.get('request_id')
                if not isinstance(key, str) or not key:
                    raise ValueError('missing generation identity')
                if kind.endswith('started'):
                    starts.add(key)
                else:
                    _put(returned, key, {'raw': event.get('raw_generation') or {}, 'transport': event.get('state_transport')})
            if kind in ('supervisor_request_started', 'supervisor_http_attempt_started', 'supervisor_response_envelope_received'):
                key = (event.get('run_id'), event.get('call_id'))
                if not all(isinstance(v, str) and v for v in key):
                    raise ValueError('missing provider identity')
                if kind == 'supervisor_request_started':
                    requests.add(key)
                else:
                    attempt = event.get('attempt')
                    if type(attempt) is not int or attempt < 1:
                        raise ValueError('invalid provider attempt identity')
                    key = (*key, attempt)
                    if kind.endswith('started'):
                        attempts.add(key)
                    else:
                        _put(envelopes, key, {'model': event.get('model'), 'usage': event.get('usage'),
                                             'latency_ms': event.get('latency_ms')})
    rows = []
    for key in sorted(attempts | envelopes.keys()):
        envelope = envelopes.get(key, {})
        usage = envelope.get('usage') or {}
        if not isinstance(usage, dict):
            usage = {}
        input_count = _count(usage.get('input_tokens', usage.get('prompt_tokens')))
        output_count = _count(usage.get('output_tokens', usage.get('completion_tokens')))
        rate = rates.get(envelope.get('model'))
        cost = None
        if rate and input_count is not None and output_count is not None:
            cost = (input_count * rate['input_per_million'] + output_count * rate['output_per_million']) / 1_000_000
        rows.append({'run_id': key[0], 'call_id': key[1], 'attempt': key[2],
                     'model': envelope.get('model'), 'input_tokens': input_count,
                     'output_tokens': output_count, 'cost': cost,
                     'latency_ms': envelope.get('latency_ms'),
                     'attempt_start_recorded': key in attempts})
    logical = []
    for key, record in returned.items():
        raw = record['raw']
        counts = []
        for field in ('prompt_token_ids', 'raw_token_ids'):
            ids = raw.get(field)
            valid = isinstance(ids, list) and bool(ids) and all(_count(t) is not None for t in ids)
            counts.append(len(ids) if valid else None)
        logical.append({'request_id': key, 'input_tokens': counts[0], 'output_tokens': counts[1],
                        'state_transport': record['transport']})
    unmatched = len(starts ^ returned.keys())
    unresolved_provider = len(requests - {k[:2] for k in attempts | envelopes.keys()})
    missing_usage = sum(r['input_tokens'] is None or r['output_tokens'] is None for r in rows)
    missing_cost = sum(r['cost'] is None for r in rows)
    # Non-native generations must have their own provider accounting; absent
    # envelopes are unknown, not a free model. Native service cost is unmeasured.
    # Existing model/provider logs do not supply a shared billing identity.
    # Matching by count would incorrectly cover a missing call with an unrelated
    # advice request, so combined ledgers conservatively leave total unknown.
    unpriced_generations = len(logical)
    known_cost = sum(r['cost'] for r in rows if r['cost'] is not None)
    complete_cost = bool(rows) and not (missing_cost or unmatched or unresolved_provider or unpriced_generations
                                       or envelopes.keys() - attempts)
    def total(field, records):
        return sum(r[field] for r in records) if all(r[field] is not None for r in records) else None
    return {'provider_attempts': len(rows), 'provider_input_tokens': total('input_tokens', rows),
            'provider_output_tokens': total('output_tokens', rows), 'missing_usage_attempts': missing_usage,
            'known_cost_subtotal': known_cost, 'total_cost': known_cost if complete_cost else None,
            'priced_attempts': len(rows) - missing_cost, 'unpriced_attempts': missing_cost,
            'currency': currency, 'cost_complete': complete_cost,
            'unresolved_provider_requests': unresolved_provider,
            'generation_started': len(starts), 'generation_returned': len(returned),
            'unpaired_generations': unmatched,
            'logical_input_tokens_known': sum(r['input_tokens'] or 0 for r in logical),
            'logical_output_tokens_known': sum(r['output_tokens'] or 0 for r in logical),
            'logical_input_tokens': total('input_tokens', logical) if not unmatched else None,
            'logical_output_tokens': total('output_tokens', logical) if not unmatched else None,
            'remote_gpu_peak_bytes': None, 'remote_gpu_seconds': None,
            'provider_rows': rows, 'generation_rows': logical,
            'scope': 'supplied traces only; logical token counts are not physical cost'}


def audit_run_usage(root, *, rates=None, currency=None):
    """Aggregate a whole workflow, including failed attempts and advice/takeover.

    Parent history copies are excluded: include their original run explicitly
    when comparing the cost of a recovery campaign.
    """
    root = Path(root).resolve(strict=True)
    names = {'model_trace.jsonl', 'strong_trace.jsonl', 'ADVICE_PROVIDER_TRACE.jsonl'}
    traces = {str(p.relative_to(root)): [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
              for p in sorted(root.rglob('*.jsonl')) if p.name in names and 'workspace' not in p.relative_to(root).parts
              and 'tool_snapshots' not in p.relative_to(root).parts}
    result = summarize_usage(traces, rates=rates, currency=currency)
    result['trace_files'] = sorted(traces)
    result['trace_sha256'] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in traces}
    result['run_root'] = str(root)
    delivery_path = next((p for p in (root / 'DELIVERY.json', root / 'RESULT.json') if p.is_file()), None)
    if delivery_path:
        delivery = json.loads(delivery_path.read_text())
        result['delivery_sha256'] = hashlib.sha256(delivery_path.read_bytes()).hexdigest()
        result['task_termination'] = delivery.get('termination')
        result['task_assistance'] = delivery.get('assistance')
        result['task_acceptance_recorded'] = delivery.get('acceptance')
        result['end_to_end_seconds'] = delivery.get('end_to_end_seconds', (delivery.get('workflow') or {}).get('end_to_end_seconds'))
        result['recorded_inner_elapsed_seconds'] = delivery.get('elapsed_seconds')
    else:
        result['end_to_end_seconds'] = None
    return result
