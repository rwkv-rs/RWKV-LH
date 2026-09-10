"""Seal completed R1 evidence and helper bytes before the separately authorized R2."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
names = ('ULTRADATA_EXECUTION_REVALIDATION_R1_20260910', 'REALPROJECT_EXECUTION_REVALIDATION_R1_20260910')

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

helpers = set()
for pattern in ('*execution_revalidation*_20260910.py', '*scoped_waiver*_20260910.py',
                '*scoped_extraction*_20260910.py', '*legacy_review_preservation*_20260910.py',
                'waiver_review_one*_20260910.py', 'waiver_scoped_review_two_20260910.py'):
    helpers.update((ROOT / 'temp').glob(pattern))
helpers.add(ROOT / 'temp/verify_official_case_handoffs_r1_20260910.py')
(OUT / 'helpers').mkdir(exist_ok=True)
for path in sorted(helpers):
    shutil.copyfile(path, OUT / 'helpers' / path.name)
manifests = []
for name in names:
    folder = ROOT / 'data/experiments' / name
    completion = json.loads((folder / 'COMPLETION.json').read_text())
    if not completion['source_unchanged']:
        raise SystemExit('Unfrozen source')
    files = [{'path': str(p.relative_to(folder)), 'sha256': sha(p), 'bytes': p.stat().st_size}
             for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'EVIDENCE_SHA256.json']
    path = folder / 'EVIDENCE_SHA256.json'
    with path.open('x') as f:
        json.dump({'round_id': name, 'files': files}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    manifests.append({'path': str(path), 'sha256': sha(path), 'files': len(files)})
files = [{'path': str(p.relative_to(OUT)), 'sha256': sha(p), 'bytes': p.stat().st_size}
         for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'EVIDENCE_SHA256.json']
with (OUT / 'EVIDENCE_SHA256.json').open('x') as f:
    json.dump({'round_id': OUT.name, 'files': files, 'suite_manifests': manifests,
               'validation': {'production_commit': 'b3e89de6edca240a8afc1998cbf5d16772d076c0',
                              'pytest_passed': 1447, 'pytest_failed': 0, 'pytest_skipped': 0,
                              'pytest_log_sha256': sha(OUT / 'PYTEST_ISOLATED.log')},
               'server_git_executed': False, 'holdout_accessed': False}, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'report_sha256': sha(OUT / 'REPORT.zh-CN.md'),
                  'evidence_sha256': sha(OUT / 'EVIDENCE_SHA256.json'), 'suite_manifests': manifests}))
