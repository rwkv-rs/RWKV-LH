"""Prove the production grammar rejects each violation class, without sampling.

An earlier negative control asked an unconstrained model to emit a malformed
output and then checked that the constrained arm did not. The model never
emitted the planned violation, so the constrained arm's silence proved nothing:
you cannot order a model to produce a specific malformed string.

These controls remove the model from the question. The grammar is advanced over
a literal prefix and the decoder's own bitmask is read at the exact position
where the violation would have to begin. A violation is proven rejected when
every tokenization of its first bytes is masked out, and the control is only
meaningful when the legal alternative at that same position is allowed -- a
grammar that forbade everything would otherwise look like a success.
"""
from copy import deepcopy
import hashlib
import json

CONTROL_PROTOCOL = 'rwkv-lh.transcript-mask-controls.v1'


def _allowed(mask, token):
    return bool(token >= 0 and token // 8 < len(mask) and mask[token // 8] & (1 << (token % 8)))


def _matcher_at(contract, prefix, *, llguidance, tokenizer_wrapper):
    """Advance a fresh matcher over the literal prefix and return it."""
    matcher = llguidance.LLMatcher(
        tokenizer_wrapper, llguidance.LLMatcher.grammar_from_lark(contract['grammar']))
    tokens = tokenizer_wrapper.tokenize_str(prefix) if prefix else []
    if tokens:
        accepted = matcher.try_consume_tokens(tokens)
        if accepted != len(tokens):
            raise ValueError('control prefix is not accepted by the production grammar: ' + prefix)
    if matcher.is_error():
        raise ValueError('matcher error after control prefix: ' + str(matcher.get_error()))
    return matcher


def probe(contract, *, prefix, violation, legal, llguidance, tokenizer_wrapper):
    """Read the live mask where `violation` would start after `prefix`.

    Both continuations are tokenized in context: a token boundary differs
    between `prefix + violation` and `violation` alone, so a naive encode of
    the fragment would test a position the decoder never visits.
    """
    matcher = _matcher_at(contract, prefix, llguidance=llguidance, tokenizer_wrapper=tokenizer_wrapper)
    mask = matcher.compute_bitmask()
    result = {'prefix': prefix, 'violation': violation, 'legal': legal}
    for name, continuation in (('violation', violation), ('legal', legal)):
        tokens = tokenizer_wrapper.tokenize_str(prefix + continuation)
        consumed = tokenizer_wrapper.tokenize_str(prefix)
        tail = tokens[len(consumed):]
        if not tail:
            raise ValueError('control continuation adds no token: ' + continuation)
        result[name + '_first_token'] = tail[0]
        result[name + '_allowed'] = _allowed(mask, tail[0])
    result['rejected'] = not result['violation_allowed']
    result['discriminating'] = result['legal_allowed']
    result['passed'] = result['rejected'] and result['discriminating']
    return result


def reach(contract, seed, *, llguidance, tokenizer_wrapper, steps=200):
    """Advance from `seed` through every byte the grammar forces, and stop.

    Hand-written prefixes drift as the grammar evolves: a transcript call is
    wrapped in a message envelope whose exact shape -- content, then
    reasoning_content, then tool_calls -- is the grammar's to decide, not ours.
    Following `compute_ff_bytes` derives the prefix from the live grammar, so a
    control always probes a position the decoder really visits.
    """
    matcher = _matcher_at(contract, seed, llguidance=llguidance,
                          tokenizer_wrapper=tokenizer_wrapper)
    reached = seed
    for _ in range(steps):
        forced = matcher.compute_ff_bytes()
        if not forced:
            break
        text = forced.decode('utf-8', 'strict')
        if matcher.try_consume_tokens(tokenizer_wrapper.tokenize_str(text)) == 0:
            break
        reached += text
    return reached


def control_cases(contract, *, llguidance, tokenizer_wrapper):
    """One case per violation class, each anchored at a derived decode position."""
    tools = [t['function']['name'] if 'function' in t else t['name']
             for t in (contract.get('native_tools') or [])]

    def at(*parts):
        """Advance through forced bytes after each literal the caller supplies.

        `reach` consumes whatever the grammar forces, so the caller writes only
        the bytes the grammar leaves free. Writing a forced literal again would
        build a prefix the decoder never visits.
        """
        reached = ''
        for literal in parts:
            reached = reach(contract, reached + literal, llguidance=llguidance,
                            tokenizer_wrapper=tokenizer_wrapper)
        return reached

    # Reaching this point already forces id/type/function and the "name": key.
    named = at('{"role":"assistant","content":null,"reasoning_content":n', '{"id":"c1",')
    return [
        {'case': 'unknown_tool',
         'prefix': named, 'violation': 'Nonexistent', 'legal': 'Read',
         'why': 'a tool outside the registered catalog must be unreachable'},
        {'case': 'retired_action',
         'prefix': named, 'violation': 'submit_plan', 'legal': 'Edit',
         'why': 'a retired action name must be unreachable'},
        # The comma is legal -- Read has optional parameters -- and the opening
        # quote after it is forced, so the probe sits on the key's first byte,
        # where only a declared name may begin.
        {'case': 'additional_property',
         'prefix': at(named, 'Read', 'a.txt\\",'), 'violation': 'extra', 'legal': 'start_byte',
         'why': 'additionalProperties is false, so only a declared key may open'},
    ], tools


def forced_cases(contract, *, llguidance, tokenizer_wrapper):
    """Classes the grammar settles by forcing bytes rather than by masking.

    Where a tool's argument object has one reachable continuation, the decoder
    emits the parameter name itself: the native spelling and a wrong key order
    are not rejected at a branch, they are unreachable because no branch exists.
    That is the stronger property, so it is asserted as forcing rather than
    recorded as a masked alternative.
    """
    def at(*parts):
        reached = ''
        for literal in parts:
            reached = reach(contract, reached + literal, llguidance=llguidance,
                            tokenizer_wrapper=tokenizer_wrapper)
        return reached

    named = at('{"role":"assistant","content":null,"reasoning_content":n', '{"id":"c1",')
    rows = []
    for case, tool, expected, forbidden in (
            ('native_parameter_name', 'Read', 'file_path', 'path'),
            ('key_order', 'Edit', 'file_path', 'old_string'),
            ('native_parameter_name_write', 'Write', 'file_path', 'path')):
        reached = at(named, tool)
        tail = reached[len(named) + len(tool):]
        rows.append({'case': case, 'tool': tool, 'forced_tail': tail,
                     'forces_expected_key': ('\\"%s\\"' % expected) in tail,
                     'never_emits_forbidden': ('\\"%s\\"' % forbidden) not in tail,
                     'why': 'the grammar forces this key, so the violation has no branch to take'})
        rows[-1]['passed'] = rows[-1]['forces_expected_key'] and rows[-1]['never_emits_forbidden']
    return rows


def run_controls(contract, *, llguidance, tokenizer_wrapper):
    """Return one verdict per violation class and the overall result."""
    cases, tools = control_cases(contract, llguidance=llguidance,
                                 tokenizer_wrapper=tokenizer_wrapper)
    results = []
    for case in cases:
        row = dict(case)
        row.update(probe(contract, prefix=case['prefix'], violation=case['violation'],
                         legal=case['legal'], llguidance=llguidance,
                         tokenizer_wrapper=tokenizer_wrapper))
        results.append(row)
    forced = forced_cases(contract, llguidance=llguidance, tokenizer_wrapper=tokenizer_wrapper)
    evidence = {'protocol': CONTROL_PROTOCOL, 'grammar_sha256': contract['grammar_sha256'],
                'contract_sha256': contract['contract_sha256'], 'registered_tools': tools,
                'cases': results, 'forced': forced,
                'scope': 'decoder bitmask and forced bytes at real decode positions; '
                         'it does not measure model quality',
                'all_rejected': all(r['rejected'] for r in results),
                'all_discriminating': all(r['discriminating'] for r in results),
                'all_forced': all(r['passed'] for r in forced)}
    evidence['passed'] = (evidence['all_rejected'] and evidence['all_discriminating']
                          and evidence['all_forced'])
    evidence['evidence_sha256'] = hashlib.sha256(
        json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    return deepcopy(evidence)
