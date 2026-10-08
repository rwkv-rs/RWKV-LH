"""Audit-only Project call framing; never repair decisions or change a candidate plan."""
from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Mapping

from . import model_io
from .model_io import ModelCommandNormalization, ModelIOError, canonical_json
from .project_model_io import parse_project_model_command_with_trace
from .project_protocols import planner

FORMAT_ADAPTER_VERSION = 'project-boundary-format.v8'

_NAME_KEYS = ('function', 'name', 'tool', 'response')
_ARGUMENT_KEYS = ('params', 'parameters', 'arguments', 'args', 'function_args')


def _explicit_flat_call(value):
    """Decode an explicitly named operation without adding any arguments."""
    if not isinstance(value, Mapping):
        raise ModelIOError('explicit function call must be an object')
    names = [key for key in _NAME_KEYS if key in value]
    arguments = [key for key in _ARGUMENT_KEYS if key in value]
    if len(names) != 1 or len(arguments) != 1 or set(value) != {names[0], arguments[0]}:
        raise ModelIOError('explicit function call requires one name and one argument field only')
    name, params = value[names[0]], value[arguments[0]]
    if not isinstance(name, str) or not name or name != name.strip():
        raise ModelIOError('function name must be a trimmed non-empty string')
    if arguments[0] in ('arguments', 'function_args') and isinstance(params, str):
        try:
            params = model_io.load_model_json(params)
        except json.JSONDecodeError as exc:
            raise ModelIOError('function arguments are not one JSON object') from exc
    if not isinstance(params, Mapping):
        raise ModelIOError('function parameters must be an object')
    return {'function': name, 'params': dict(params)}


def _explicit_tool_item(value):
    if not isinstance(value, Mapping):
        raise ModelIOError('tool call item must be an object')
    value = dict(value)
    if 'id' in value:
        identity = value.pop('id')
        if not isinstance(identity, str) or not identity or identity != identity.strip():
            raise ModelIOError('tool call id must be a trimmed non-empty string')
    if 'type' in value and value.pop('type') != 'function':
        raise ModelIOError('tool call type must be function')
    if set(value) == {'function'} and isinstance(value['function'], Mapping):
        value = value['function']
    return _explicit_flat_call(value)


def _explicit_envelope(value, *, role):
    """Recognize only one complete, unambiguous transport container."""
    if 'tool_call' in value or 'tool_calls' in value:
        if set(value) == {'tool_call'}:
            return _explicit_tool_item(value['tool_call']), ['explicit_tool_call_object']
        if set(value) == {'tool_calls'}:
            calls = value['tool_calls']
            if isinstance(calls, list) and len(calls) == 1:
                return _explicit_tool_item(calls[0]), ['explicit_single_tool_calls_item']
        raise ModelIOError('Project tool envelope requires exactly one call and no extra fields')
    if isinstance(value.get('function'), Mapping):
        if set(value) <= {'function', 'id', 'type'}:
            return _explicit_tool_item(value), ['explicit_nested_function_object']
        raise ModelIOError('nested function envelope contains conflicting or extra fields')
    if 'response' in value:
        return _explicit_flat_call(value), ['explicit_response_name']
    return value, []


def rejected_call_definition(raw, definitions, *, command=None):
    """Look up an explicitly named function for diagnostics, never repair a call.

    A parser failure can still contain one literal operation name. Keep its real
    role/Harness schema available to the model, without constructing parameters,
    accepting an envelope, or guessing through ambiguous/multiple call wrappers.
    The returned definition has no execution authority.
    """
    if command is not None:
        name = command.name
    else:
        try:
            source, surface = model_io._extract_json(raw)
            if set(surface) - {'surface:surrounding_whitespace_removed', 'surface:markdown_code_fence_removed'}:
                return None  # In particular, never infer from a discarded second call.
            # Inspect object members without collapsing duplicate parameters.
            # Tuples mark JSON objects; arrays remain lists. This diagnostic
            # projection never produces a command or chooses an argument value.
            members = json.loads(source, object_pairs_hook=tuple)
        except (ValueError, TypeError):
            return None
        if not isinstance(members, tuple):
            return None
        keys = [key for key, _value in members]
        if len(keys) != len(set(keys)):
            return None  # Even identical duplicate envelope keys are ambiguous.
        value = dict(members)
        if {'function_call', 'content', 'calls', 'tool_calls'} & value.keys():
            return None
        names = [value[key] for key in ('function', 'name', 'tool') if key in value]
        if len(names) != 1:
            return None
        name = names[0]
    if not isinstance(name, str) or not name or name != name.strip():
        return None
    matches = [item for item in definitions if item['name'] == name]
    return deepcopy(matches[0]) if len(matches) == 1 else None


def parse_role_call(raw: str, *, role: str, payload: Mapping):
    command, trace = _parse_role_call(raw, role=role, payload=payload)
    if role == 'planner':
        return command, trace
    from .project_receipt_refs import resolve_command
    resolved = resolve_command(payload, command)
    if resolved == command:
        return command, trace
    return resolved, ModelCommandNormalization(
        input_payload=trace.input_payload, normalized_payload=resolved.to_wire_dict(),
        transformations=(*trace.transformations, 'receipt_handles:exact_ledger_binding'),
        normalizer_version=FORMAT_ADAPTER_VERSION)


def _parse_role_call(raw: str, *, role: str, payload: Mapping):
    """Map only exact, unambiguous envelopes to the one existing call contract.

    The independent schema/role/boundary checks run after this function. Invalid
    or ambiguous content goes to the unchanged parser and is rejected there.
    """
    try:
        text, surface = model_io._extract_json(raw)
    except (ModelIOError, TypeError):
        return parse_project_model_command_with_trace(raw)
    if 'surface:trailing_second_object_removed' in surface:
        raise ModelIOError('Project output must contain exactly one operation')
    try:
        original = model_io.load_model_json(text)
    except (ModelIOError, json.JSONDecodeError, TypeError):
        return parse_project_model_command_with_trace(raw)
    if not isinstance(original, Mapping):
        return parse_project_model_command_with_trace(raw)
    wire, transformations = _explicit_envelope(dict(original), role=role)
    # This is an explicitly named single operation, not a role-inferred call.
    # Unknown fields and missing or non-object parameters remain invalid.
    if (set(wire) == {'function', 'id', 'type', 'calls'} and wire['type'] == 'function'
            and isinstance(wire['id'], str) and wire['id'] and isinstance(wire['calls'], list)
            and len(wire['calls']) == 1):
        call = wire['calls'][0]
        if (isinstance(call, Mapping) and set(call) == {'arguments', 'id', 'type'}
                and call['type'] == 'function' and call['id'] == wire['id']
                and isinstance(call['arguments'], Mapping)):
            wire = {'function': wire['function'], 'params': dict(call['arguments'])}
            transformations.append('explicit_single_call_container')
    if set(wire) == {'function', 'params', 'type'} and wire['type'] == 'json_object':
        wire.pop('type')
        transformations.append('json_mode_annotation')
    if role == 'planner':
        mode = payload.get('mode')
        if mode in ('review', 'review_checks') and set(wire) == {'verdict', 'issues'}:
            name = 'review_checks' if mode == 'review_checks' else 'review_plan'
            wire = {'function': name, 'params': wire}
            transformations.append('call_envelope:bare_role_parameters->' + name)
        elif mode == 'checks' and set(wire) == {'checks', 'rationale', 'replacements'}:
            wire = {'function': 'submit_checks', 'params': wire}
            transformations.append('call_envelope:bare_role_parameters->submit_checks')
        elif mode == 'diagnose' and set(wire) == {'text', 'evidence_ids'}:
            wire = {'function': 'advise', 'params': wire}
            transformations.append('call_envelope:bare_role_parameters->advise')
        elif mode == 'plan' and payload.get('plan') is None:
            if set(wire) == {'plan'}:
                wire = {'function': 'submit_plan', 'params': wire}
                transformations.append('bare_initial_plan_parameters')
            elif set(wire) == set(planner.PLAN_SCHEMA['properties']):
                wire = {'function': 'submit_plan', 'params': {'plan': wire}}
                transformations.append('bare_initial_plan_object')
            elif set(wire) == {'action', 'plan'} and wire['action'] == 'submit_plan':
                wire = {'function': 'submit_plan', 'params': {'plan': wire['plan']}}
                transformations.append('explicit_initial_action')
    if not transformations:
        return parse_project_model_command_with_trace(raw)
    # The normalizer edits the envelope only; the model's plan, direction and
    # parameters are untouched. Downstream validation still may (and must) reject.
    command, nested = parse_project_model_command_with_trace(canonical_json(wire))
    return command, ModelCommandNormalization(
        input_payload=dict(original), normalized_payload=command.to_wire_dict(),
        transformations=tuple(surface) + tuple(transformations) + nested.transformations,
        normalizer_version=FORMAT_ADAPTER_VERSION,
    )
