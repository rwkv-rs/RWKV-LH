"""Prepare exactly the seven unfunded, zero-generation cases after owner recharge."""
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OLD = ROOT / 'data/experiments/REALPROJECT_EXECUTION_REVALIDATION_R1_20260910'
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
OUT.mkdir(exist_ok=False)
case_ids = ('RP-CLI-02', 'RP-DATA-01', 'RP-DATA-02', 'RP-FULL-01', 'RP-FULL-02', 'RP-WEB-01', 'RP-WEB-02')
predecessors = []
for case in case_ids:
    path = OLD / 'all_zero' / f'{case}.result.json'
    result = json.loads(path.read_text())
    if result['model_requests'] != 0 or result['action_count'] != 0 or result['supervisor_failure']['http_status'] != 402:
        raise SystemExit(f'Case is not an unfunded zero-generation predecessor: {case}')
    predecessors.append({'case': case, 'result_path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
source = ROOT / 'temp/run_realproject_execution_revalidation_r1_20260910.py'
driver = ROOT / 'temp/run_execution_revalidation_r2_20260910.py'
body = source.read_text().replace('REALPROJECT_EXECUTION_REVALIDATION_R1_20260910', OUT.name)
body = body.replace('Collect all twelve authorized development tasks', 'Collect the seven explicitly authorized balance-recovery development tasks')
body = body.replace('21600', '12600')
body = body.replace("    return {'public_task_sha256': digest(BUNDLE / 'tasks.json')}, tasks",
                    "    tasks = [task for task in tasks if task['task_id'] in " + repr(case_ids) + "]\n"
                    "    assert tuple(task['task_id'] for task in tasks) == " + repr(case_ids) + "\n"
                    "    return {'public_task_sha256': digest(BUNDLE / 'tasks.json')}, tasks")
body = body.replace("'owner_authorization': '", "'owner_authorization': '2026-09-10 owner explicitly confirmed account recharge and requested continuation. This separate run retries ONLY the seven HTTP402 zero-generation cases, retaining R1 unchanged. Prior scope: ", 1)
body = body.replace("'purpose': 'Owner requested 15-task evaluation after b3e89de6; preserve historical scores and record first transport errors',",
                    "'purpose': 'Complete model observation for the seven HTTP402 cases after owner recharge; R1 scores immutable; report R2 separately and a linked 15-task coverage view',")
with driver.open('x') as f:
    f.write(body)
(OUT / driver.name).write_text(body)
record = {'owner_authorization': 'Owner: 我充值好了，可以继续使用了', 'selected_cases': list(case_ids),
          'selection_rule': 'All and only R1 HTTP402 initial-Planner failures with zero RWKV calls/actions; no selection on model score',
          'predecessor_results': predecessors, 'prior_result_rewriting': False,
          'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
          'per_case_wall_seconds': 1800, 'total_wall_seconds': 12600,
          'production_source': 'identical to b3e89de6; R1 only added records/docs',
          'sampling_scoring_and_case_budgets': 'unchanged', 'native_transport_resume_attempts': 1,
          'full_15_task_view': 'R1 eight actually generated cases plus R2 seven cases; explicit cross-run provenance, never overwrite R1 0/15',
          'optimizer_steps': 0, 'holdout_accessed': False}
with (OUT / 'BALANCE_RECOVERY_REGISTRATION.json').open('x') as f:
    json.dump(record, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'prepared_driver': str(driver), 'cases': case_ids}))
