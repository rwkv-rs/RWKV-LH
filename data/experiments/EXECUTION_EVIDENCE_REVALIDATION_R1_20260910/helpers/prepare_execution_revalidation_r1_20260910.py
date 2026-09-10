"""Prepare immutable new collection drivers and verify existing uploaded services."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
OUT.mkdir(exist_ok=True)
for old, new in (
    ('realproject_official_collection_r3', 'realproject_execution_revalidation_r1'),
    ('ultradata_official_collection_r6', 'ultradata_execution_revalidation_r1'),
):
    src = ROOT / f'temp/run_{old}_20260910.py'
    dst = ROOT / f'temp/run_{new}_20260910.py'
    body = src.read_text().replace(old.upper(), new.upper())
    body = body.replace("supervisor_pending_resume_attempts=0, stateful_goal=True)",
                        "supervisor_pending_resume_attempts=0, native_transport_resume_attempts=1, stateful_goal=True)")
    body = body.replace("'supervisor_pending_resume_attempts': 0, 'per_case_reruns': 0,",
                        "'supervisor_pending_resume_attempts': 0, 'native_transport_resume_attempts': 1, 'per_case_reruns': 0,")
    body = body.replace("'purpose': 'actual production Agent observation and current Selector evidence collection',",
                        "'purpose': 'Owner requested 15-task evaluation after b3e89de6; preserve historical scores and record first transport errors',")
    body = body.replace("'owner_authorization': '", "'owner_authorization': '2026-09-10 current owner explicitly requests rerunning all fixed 15 tasks after execution and transport repair. Prior scope: ", 1)
    assert 'native_transport_resume_attempts=1' in body
    with dst.open('x') as f:
        f.write(body)
    (OUT / dst.name).write_text(body)

launcher = ROOT / 'data/experiments/OFFICIAL_PLANNER_TRACE_REPAIR_R1_20260910/deployment_final/launch_native.sh'
verification = launcher.read_text().split('\nexec ', 1)[0] + '\n'
result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'rwkv-8222', 'bash', '-s'],
                        input=verification, text=True, capture_output=True)
(OUT / 'UPLOADED_SOURCE_VERIFICATION.log').write_text(result.stdout + result.stderr)
assert result.returncode == 0, result.stderr
registration = {
    'round_id': OUT.name,
    'client_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'server_identity': json.loads(result.stdout.strip().splitlines()[-1].replace("'", '"')),
    'server_source': 'existing frozen uploaded official-planner-repair-r1-final; verified actual files against both full manifests',
    'server_git_executed': False,
    'evaluation': {'realproject': 12, 'ultradata': 3, 'all_roles': 'zero', 'native_transport_resume_attempts': 1},
    'comparison': {
        'baseline_runs': ['REALPROJECT_OFFICIAL_COLLECTION_R3_20260910', 'ULTRADATA_OFFICIAL_COLLECTION_R6_20260910'],
        'baseline_strict': 0, 'baseline_completed': 0, 'baseline_mutations': 3,
        'baseline_supervisor_generation_interrupted': 0,
        'keep': ['no unknown chain losing original error', 'Strict >= historical 0/15', 'SupervisorGenerationInterrupted strictly below baseline'],
        'limitation': 'Historical latest 15-task baseline has zero Supervisor failures: strict decrease is mathematically impossible. Report gate unmet; do not replace baseline or silently weaken to non-increase. Cross-code historical observations are not controlled same-code A/B or causal improvement evidence.'
    },
    'review_authorization': 'Owner explicitly permits two independent AI reviewers; identities must disclose AI, never human signatures',
    'optimizer_steps': 0, 'holdout_accessed': False,
}
(OUT / 'REGISTRATION.json').write_text(json.dumps(registration, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(registration, ensure_ascii=False))
