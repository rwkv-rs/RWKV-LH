"""Link R1's eight generated cases and R2's seven replacements without rewriting scores."""
from collections import Counter
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
R1 = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
R2 = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
RP1 = ROOT / 'data/experiments/REALPROJECT_EXECUTION_REVALIDATION_R1_20260910'
UP1 = ROOT / 'data/experiments/ULTRADATA_EXECUTION_REVALIDATION_R1_20260910'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

recovery = read(R2 / 'BALANCE_RECOVERY_REGISTRATION.json')
replace_ids = set(recovery['selected_cases'])
before = read(R1 / 'AGENT_SUMMARY.json')
after = read(R2 / 'AGENT_SUMMARY.json')
if not after['agent']['counts_complete'] or after['agent']['selected'] != 7:
    raise SystemExit('All seven R2 cases must have final records')
if {r['task_id'] for r in after['cases']} != replace_ids:
    raise SystemExit('R2 source scope changed')
same = {}
new_protocol = read(R2 / 'all_zero/RUN_PROTOCOL.json')
for folder in (RP1, UP1):
    old_protocol = read(folder / 'all_zero/RUN_PROTOCOL.json')
    checks = {
        'source_files': read(folder / 'all_zero/source_tree_manifest.json') == read(R2 / 'all_zero/source_tree_manifest.json'),
        'runner': old_protocol['code']['runner_sha256'] == new_protocol['code']['runner_sha256'],
        'supervisor_settings': old_protocol['supervisor']['settings'] == new_protocol['supervisor']['settings'],
    }
    for key in ('goal_role_runtimes', 'sampling', 'stateful_goal', 'tokenizer', 'independent_selector'):
        checks[key] = old_protocol[key] == new_protocol[key]
    same[folder.name] = checks
    if not all(checks.values()):
        raise SystemExit('Frozen run conditions differ: ' + folder.name)
rows = [r for r in before['cases'] if r['task_id'] not in replace_ids] + after['cases']
if len(rows) != 15 or len({r['task_id'] for r in rows}) != 15:
    raise SystemExit('Linked denominator is not exactly 15 unique tasks')
summary = {'selected': 15, 'recorded': 15, 'strict': sum(r['strict'] for r in rows),
           'completed': sum(r['completed'] for r in rows), 'mutation_count': sum(r['mutation_count'] for r in rows),
           'action_count': sum(r['action_count'] for r in rows),
           'termination_reasons': dict(Counter(r['termination'] for r in rows)),
           'supervisor_failures': sum(len(r['supervisor_failures']) for r in rows),
           'supervisor_generation_interruptions': sum(len(r['supervisor_generation_interruptions']) for r in rows),
           'runtime_transport_failures': sum(len(r['runtime_failures']) for r in rows),
           'native_first_errors': sum(sum(e.get('type') == 'native_request_transport_error' for e in r['native_transport_events']) for r in rows),
           'native_first_error_counter_observable': False,
           'native_first_error_counter_limitation': 'Logged count only; actual factory drops client audit events. R1 zero-event interpretation is superseded by R2 offline wiring evidence.'}
value = {'view_kind': 'linked_same_source_task_coverage_not_a_new_single_run_or_rescore',
         'agent': summary, 'same_frozen_conditions': same, 'cases': rows,
         'r1_original_15_task_result_preserved': before['agent'], 'r2_separate_result': after['agent'],
         'r1_summary_sha256': sha(R1 / 'AGENT_SUMMARY.json'), 'r2_summary_sha256': sha(R2 / 'AGENT_SUMMARY.json'),
         'selection_rule': recovery['selection_rule'], 'optimizer_steps': 0, 'holdout_accessed': False}
with (R2 / 'LINKED_15_TASK_SUMMARY.json').open('x') as f:
    json.dump(value, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'linked_agent': summary, 'conditions_equal': all(all(c.values()) for c in same.values())}, ensure_ascii=False))
