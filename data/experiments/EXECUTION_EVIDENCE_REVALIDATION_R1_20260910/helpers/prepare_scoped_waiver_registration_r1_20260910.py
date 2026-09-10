"""Prepare a reviewable fixed source subset; this does not grant a waiver."""
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
names = ('REALPROJECT_OFFICIAL_COLLECTION_R3_20260910', 'ULTRADATA_OFFICIAL_COLLECTION_R6_20260910')
records = []
inputs = []
coverage = None
for name in names:
    path = ROOT / 'data/experiments' / name / 'SOURCE_REGISTRATION.json'
    raw = path.read_bytes()
    value = json.loads(raw)
    inputs.append({'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()})
    if coverage is None:
        coverage = value['coverage_scope']
    else:
        assert coverage['sha256'] == value['coverage_scope']['sha256']
    records.extend(value['source_runs'])
assert len(records) == 15
excluded = [r for r in records if r['run_id'] == 'RP-WEB-02']
included = [r for r in records if r['run_id'] != 'RP-WEB-02']
assert len(excluded) == 1 and len(included) == 14
registration = {'schema_version': value['schema_version'], 'source_runs': included, 'coverage_scope': coverage}
path = OUT / 'SCOPED_SOURCE_REGISTRATION.json'
with path.open('x') as f:
    json.dump(registration, f, ensure_ascii=False, indent=2)
    f.write('\n')
scope = {'decision': 'pending_independent_reviews', 'role': 'selector_intent',
         'registration_path': str(path), 'registration_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
         'input_registrations': inputs,
         'included_run_ids': [r['run_id'] for r in included], 'excluded_run_ids': ['RP-WEB-02'],
         'reason': 'Conservative source-level exclusion of old check_command behavior affected by execution repairs; no labels fabricated, no score or evaluation denominator changed.',
         'evaluation_denominator': 15, 'source_rows_unchanged': True,
         'legacy_reviews': 'Preserve all historical work, including excluded source; this is not label approval or permission to train.'}
with (OUT / 'SCOPED_WAIVER_BINDING_DRAFT.json').open('x') as f:
    json.dump(scope, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps(scope, ensure_ascii=False))
