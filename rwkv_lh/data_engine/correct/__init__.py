"""Offline diagnosis from student-visible evidence; no oracle contents in prompts."""
import asyncio
import json
from types import SimpleNamespace

from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.project_trace import agent_boundaries
from rwkv_lh.data_engine.tasks import checksum
from rwkv_lh.data_engine.rollout import TeacherPolicy, teacher_messages

LABELS = frozenset(('acceptance_failed', 'protocol_rejected', 'truncated', 'not_finished',
                    'tool_failure', 'repetition', 'input_capacity'))
CATEGORIES = frozenset(('task_error', 'protocol', 'truncated', 'tool_failure',
                        'repetition', 'premature_finish'))
DIAGNOSIS_FORMAT = (
    'Diagnose this offline RWKV coding-agent attempt. All supplied conversation and outputs are '
    'actual student-visible evidence. Failure labels disclose no private tests. Select the earliest '
    'substantive erroneous assistant turn, not a harmless exploratory command failure. Turns use '
    'zero-based k. For each turn its exact input is conversation[:message_count]. '
    'Return only JSON with k (integer), category (task_error, protocol, truncated, tool_failure, '
    'repetition, or premature_finish), and optionally explanation. Do not invent hidden requirements.')


def diagnosis_input(execution, *, failure_labels):
    if not set(failure_labels) <= LABELS:
        raise ValueError('unknown failure label; private verifier text is forbidden')
    with ProjectLedger.read_snapshot(execution) as ledger:
        state = ledger.scan_verified_events()['state']
        if state['pending'] or state['inbox']:
            raise ValueError('diagnosis requires a confirmed ended student attempt')
        if state['status'] not in ('finished', 'blocked', 'interrupted'):
            raise ValueError('diagnosis requires an ended student attempt')
        boundaries = list(agent_boundaries(execution))
    if not boundaries:
        raise ValueError('missing real student generations')
    conversation = boundaries[-1]['input']['messages']
    turns = []
    for k, boundary in enumerate(boundaries):
        messages = boundary['input']['messages']
        if messages != conversation[:len(messages)]:
            raise ValueError('student conversation is not a continuous prefix')
        result = boundary['result']
        raw = result.get('evidence', {}).get('raw_generation', {}).get('raw_output')
        if not isinstance(raw, str):
            raise ValueError('missing unmodified student output')
        turns.append({'k': k, 'operation_id': boundary['operation_id'],
                      'message_count': len(messages), 'output': raw})
    return {'conversation': conversation, 'turns': turns,
            'failure_labels': sorted(set(failure_labels))}


def validate_diagnosis(value, evidence):
    if not isinstance(value, dict) or set(value) - {'k', 'category', 'explanation'}:
        raise ValueError('invalid diagnosis fields')
    k = value.get('k')
    if type(k) is not int or not 0 <= k < len(evidence['turns']):
        raise ValueError('diagnosis turn is outside the actual trace')
    if value.get('category') not in CATEGORIES:
        raise ValueError('unknown correction category')
    if 'explanation' in value and not isinstance(value['explanation'], str):
        raise ValueError('diagnosis explanation must be text')
    return value


async def diagnose(pool, evidence, *, key):
    response = await pool.complete([
        {'role': 'system', 'content': DIAGNOSIS_FORMAT},
        {'role': 'user', 'content': json.dumps(evidence, ensure_ascii=False)}],
        key=key, lane='correction', max_output_tokens=4096)
    choice = response['choices'][0]
    if choice.get('finish_reason') == 'length':
        raise ValueError('truncated diagnosis is not usable')
    return validate_diagnosis(json.loads(choice['message']['content']), evidence)


class CorrectionPolicy(TeacherPolicy):
    """One replacement at an original boundary, through the existing native codec."""
    def __init__(self, pool, loop, *, episode, category, max_output_tokens=16384):
        if category not in CATEGORIES:
            raise ValueError('unknown correction category')
        super().__init__(pool, loop, episode=episode, max_output_tokens=max_output_tokens)
        self.category = category

    def complete(self, payload, definitions, key):
        from rwkv_lh.transcript.tools import canonical_definitions
        messages = teacher_messages(payload)
        messages[0]['content'] += (' This is one offline replacement for an erroneous RWKV turn. '
            'Failure category: ' + self.category + '. Produce the next useful action from this exact '
            'boundary. The student will resume after your real tool results; do not describe future '
            'results as observed or try to solve every remaining step in one oversized turn.')
        return asyncio.run_coroutine_threadsafe(self.pool.complete(messages,
            tools=canonical_definitions(definitions), key=key + ':correction:' + self.category,
            lane='correction', max_output_tokens=self.max_output_tokens), self.loop).result()


async def replacement(pool, boundary, *, category, key):
    """Fetch exactly one replacement; reuse TeacherPolicy's production parsing."""
    from rwkv_lh.transcript.tools import canonical_definitions
    if category not in CATEGORIES:
        raise ValueError('unknown correction category')
    payload = boundary['input']
    definitions = payload['native_tools']
    messages = teacher_messages(payload)
    messages[0]['content'] += (' Replace one erroneous RWKV turn offline. Failure category: ' + category +
        '. Choose a useful next action at this boundary. RWKV will continue after the real receipts. '
        'Do not claim future results or generate an oversized all-project solution.')
    response = await pool.complete(messages, tools=canonical_definitions(definitions), key=key,
                                   lane='correction', max_output_tokens=16384)
    class RecordedResponse(TeacherPolicy):
        def complete(self, payload, definitions, key):
            return response
    policy = RecordedResponse(SimpleNamespace(provider=pool.provider), None, episode=key)
    reply = policy.request(payload['session_id'], payload, definitions, None)
    if reply.command['function'] != 'assistant':
        raise ValueError('teacher replacement rejected or truncated')
    return reply.command['params']['message']
