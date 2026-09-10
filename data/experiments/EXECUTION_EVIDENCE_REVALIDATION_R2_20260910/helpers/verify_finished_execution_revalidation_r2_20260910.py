"""Verify each finished case once using the existing production reconstruction checks."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
for name in ('EXECUTION_EVIDENCE_REVALIDATION_R2_20260910',):
    folder = ROOT / 'data/experiments' / name
    for case in json.loads((folder / 'REGISTRATION.json').read_text())['task_ids']:
        if not (folder / 'all_zero' / f'{case}.result.json').exists():
            continue
        commands = [
            ('HANDOFF', ROOT / 'temp/verify_official_case_handoffs_r1_20260910.py', [name, case]),
            ('PUBLIC_CAUSAL', ROOT / 'temp/inspect_execution_revalidation_case_r2_20260910.py', [case]),
        ]
        for kind, script, arguments in commands:
            artifact = (folder / f'{case}.HANDOFF_VERIFICATION.json') if kind == 'HANDOFF' else (OUT / f'{case}.PUBLIC_CAUSAL_OBSERVATION.json')
            logpath = OUT / f'{case}.{kind}.log'
            if artifact.exists() or logpath.exists():
                continue
            with logpath.open('x') as log:
                result = subprocess.run([sys.executable, str(script), *arguments], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            print(json.dumps({'case': case, 'check': kind, 'exit_code': result.returncode}))
