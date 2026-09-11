"""Bind authored private grading to immutable run events; never alter Agent behavior."""
import copy
import hashlib
import json
from pathlib import Path
from rwkv_lh.benchmark_verifier import run_isolated_verifier
MARKER = 'BOUND_EVENTS = None  # trusted-event-binding-v1'

def verify_with_event_binding(acceptance, workspace, events, observations, *, private_root, timeout_seconds=180.0):
    selected = copy.deepcopy(acceptance)
    bindings = []
    for check in selected.get('checks', []):
        program = check.get('program', '')
        if MARKER not in program:
            continue
        if check.get('kind') != 'project_behavior' or program.count(MARKER) != 1 or hashlib.sha256(program.encode()).hexdigest() != check.get('program_sha256'):
            raise ValueError('private event-binding template identity mismatch')
        finished = [e for e in events if e.get('type') == 'action_finished']
        encoded = json.dumps(finished, ensure_ascii=False, separators=(',', ':'))
        bound = program.replace(MARKER, 'BOUND_EVENTS = json.loads(' + repr(encoded) + ')')
        bindings.append({'template_sha256': check['program_sha256'], 'events_sha256': hashlib.sha256(encoded.encode()).hexdigest(), 'bound_program_sha256': hashlib.sha256(bound.encode()).hexdigest(), 'finished_actions': len(finished)})
        check.update(program=bound, program_sha256=bindings[-1]['bound_program_sha256'])
    result = run_isolated_verifier(selected, workspace, events, observations, private_root=private_root, timeout_seconds=timeout_seconds)
    if bindings:
        p = Path(private_root).parent / 'DIAGNOSTIC_GRADER_BINDING.json'
        p.write_text(json.dumps({'bindings': bindings, 'agent_workspace_modified': False, 'acceptance_bound_before_evaluation': True}, indent=2) + '\n')
    return result
