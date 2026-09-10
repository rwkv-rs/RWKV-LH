"""Wait for the registered collection, then run two fresh arms in fixed order."""
from pathlib import Path
import json
import os
import subprocess
import time
ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTOR_OUTPUT_BUDGET_R1_20260910'
prerequisite = ROOT / 'data/experiments/COMMAND_PATH_COLLECTION_R1_20260910/COMPLETION.json'
deadline = time.monotonic() + 7500
while not prerequisite.exists():
    if time.monotonic() >= deadline:
        raise SystemExit('Collection prerequisite did not complete within its registered budget')
    time.sleep(5)
completion = json.loads(prerequisite.read_text())
if not completion['source_unchanged'] or not all(case['result_recorded'] for case in completion['cases']):
    raise SystemExit('Collection did not preserve source or all raw outcomes')
driver = ROOT / 'temp/run_executor_output_budget_r1_20260910.py'
for arm in ('baseline1800', 'candidate3600'):
    env = {**os.environ, 'RWKV_LH_EXPERIMENT_ARM': arm}
    folder = ROOT / 'data/experiments' / ('EXECUTOR_OUTPUT_BUDGET_' + arm.upper() + '_R1_20260910')
    folder.mkdir(exist_ok=False)
    with (folder / 'PREPARE.log').open('x') as log:
        subprocess.run([str(ROOT / '.venv/bin/python'), str(driver), 'prepare'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(json.dumps({'started_arm': arm}), flush=True)
    with (folder / 'COLLECT.log').open('x') as log:
        subprocess.run([str(ROOT / '.venv/bin/python'), str(driver), 'collect'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(json.dumps({'completed_arm': arm}), flush=True)
