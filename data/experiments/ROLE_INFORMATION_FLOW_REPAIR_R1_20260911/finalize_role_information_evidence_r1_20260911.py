"""Freeze this engineering round without reading holdout or old training rows."""
from pathlib import Path
import hashlib, importlib.metadata, json, os, platform, re, shutil, subprocess
ROOT=Path('/home/chase/GitHub/RWKV-LH')
ROUND=ROOT/'data/experiments/ROLE_INFORMATION_FLOW_REPAIR_R1_20260911'
BASE=ROOT/'data/experiments/ROLE_INPUT_METHOD_REVIEW_R1_20260911'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result=(ROUND/'FULL_04.log').read_text()
match=re.search(r'^(\d+) passed in (.+)$',result,re.M)
if not match or re.search(r'\b(?:failed|skipped|error|errors|KeyboardInterrupt)\b',result):
    raise SystemExit('Final complete regression has not passed without skips')
validation=dict(command='.venv/bin/python -m pytest -q tests/',log='FULL_04.log',passed=int(match[1]),skipped=0,elapsed=match[2],
    tests_scope='tests/; no acceptance_tests or holdout',real_model_calls=0,role_training_runs=0,new_datasets=0,remote_deployment=False,
    preparation=['uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev','.venv/bin/python -m playwright install chromium'],
    environment=dict(wsl_distribution=os.environ.get('WSL_DISTRO_NAME'),platform=platform.platform(),
        packages={key:importlib.metadata.version(key) for key in ('torch','playwright','pytest')}),
    intermediate=dict(FULL_01='21 failed / 1469 passed; fixture and expectation integration failures',
        FULL_02='1500 passed; precedes final recovery tests and diagnostic wording clarification',
        FULL_03='intentionally interrupted after 908 passed to include final diagnostic wording; not final validation'))
(ROUND/'VALIDATION.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
shutil.copy2(BASE/'SUMMARY.json',ROUND/'BASELINE_SUMMARY.json')
scripts=['migrate_role_information_protocols_r1_20260911.py','rewrite_evidence_scopes_r1_20260911.py',
    'update_role_repair_regressions_r1_20260911.py','document_role_information_repair_r1_20260911.py',
    'rerender_role_prompt_fixture_r1_20260911.py','verify_selector_observation_red_green_r1_20260911.py',
    'verify_native_fact_recovery_red_green_r1_20260911.py',Path(__file__).name]
for name in scripts:
    shutil.copy2(ROOT/'temp'/name,ROUND/name)
changed=subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT,text=True).splitlines()
changed += ['tests/test_role_information_flow.py']+[f'rwkv_lh/goal_state_protocols/{name}_v7.py' for name in ('selector_intent','executor_args','auditor_step')]
changed += [f'rwkv_lh/goal_state_protocols/{name}_v6.py' for name in ('selector_intent','executor_args','auditor_step')]
source_pins={}
removed={}
for relative in sorted(set(changed)):
    if relative.startswith('data/experiments/'):
        continue
    path=ROOT/relative
    if path.is_file():
        source_pins[relative]=sha(path)
    else:
        old=subprocess.check_output(['git','show',f'HEAD:{relative}'],cwd=ROOT)
        removed[relative]=hashlib.sha256(old).hexdigest()
pins=dict(baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    scope='Changed source/tests/docs/fixture; no remote deployment manifest',files=source_pins,removed_files=removed,
    previous_audit={str((BASE/name).relative_to(ROOT)):sha(BASE/name) for name in ('REPORT.zh-CN.md','SUMMARY.json','SOURCE_PINS.json','CALLS.json')})
(ROUND/'SOURCE_PINS.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2)+'\n')
files=sorted(p for p in ROUND.iterdir() if p.is_file() and p.name!='SHA256SUMS')
(ROUND/'SHA256SUMS').write_text(''.join(f'{sha(path)}  {path.name}\n' for path in files))
print(json.dumps(dict(passed=validation['passed'],report_sha256=sha(ROUND/'REPORT.zh-CN.md'),manifest_sha256=sha(ROUND/'SHA256SUMS')),indent=2))
