"""Read-only source admission preflight; no extraction, labels, or optimizer."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(ROOT))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import load_source_run, DatasetIntegrityError
R2 = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
OUT = ROOT / 'data/experiments/NATIVE_AUDIT_WIRING_REPAIR_R1_20260910'
linked = json.loads((R2 / 'LINKED_15_TASK_SUMMARY.json').read_text())
rows = []
for case in linked['cases']:
    folder = ROOT / 'data/experiments' / case['round']
    path = folder / (case['task_id'] + '.HANDOFF_VERIFICATION.json')
    # R1 handoff diagnostics live in the shared review directory.
    if not path.exists():
        path = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910' / path.name
    record = json.loads(path.read_text())['source_registration']
    try:
        load_source_run(record, base_dir=ROOT)
        rows.append({'case': case['task_id'], 'admitted': True})
    except DatasetIntegrityError as error:
        rows.append({'case': case['task_id'], 'admitted': False, 'reason': str(error)})
value = {'preflight_only': True, 'cases': rows,
         'admitted': sum(row['admitted'] for row in rows),
         'linked_source_sha256': hashlib.sha256((R2 / 'LINKED_15_TASK_SUMMARY.json').read_bytes()).hexdigest(),
         'formal_dataset_created': False, 'optimizer_steps': 0,
         'prior_waiver_scope': 'Historical accepted waiver remains pinned to its original 14 sources and old current SHAs. It does not authorize this new source revision.',
         'existing_quality_blockers': ['execute coverage absent in scoped candidate set',
                                     '101/281 cross-split pairs exceed fixed threshold',
                                     'semantic review labels not approved']}
with (OUT / 'SELECTOR_ADMISSION_PREFLIGHT.json').open('x') as stream:
    json.dump(value, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(value, ensure_ascii=False))
