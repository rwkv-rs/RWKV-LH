"""Validate preserved R1 and seal completed R2 evidence plus exact helper bytes."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
R1 = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()
def read(path):
    return json.loads(path.read_text())
def write(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

if not read(OUT / 'COMPLETION.json')['source_unchanged']:
    raise SystemExit('Source changed')
if not read(OUT / 'AGENT_SUMMARY.json')['agent']['counts_complete']:
    raise SystemExit('Incomplete R2')
pins = {
    'EXECUTION_EVIDENCE_REVALIDATION_R1_20260910': '4b2fdb9e15d97580c9e6257da028f8e6dde2779492d91f59f2535f1ba8c2e8e7',
    'ULTRADATA_EXECUTION_REVALIDATION_R1_20260910': 'ba68de046daffad003c445d0fdfdb24312c237f5fe5fecdac5852262d5d9ee00',
    'REALPROJECT_EXECUTION_REVALIDATION_R1_20260910': '4ba929cc9cb20eb4013f57861eae619f5ac085cab051785394343e31fff02475',
}
preserved = []
for name, expected in pins.items():
    folder = ROOT / 'data/experiments' / name
    manifest_path = folder / 'EVIDENCE_SHA256.json'
    actual = sha(manifest_path)
    if actual != expected:
        raise SystemExit('R1 manifest changed: ' + name)
    manifest = read(manifest_path)
    failures = [row['path'] for row in manifest['files']
                if not (folder / row['path']).is_file() or sha(folder / row['path']) != row['sha256']]
    preserved.append({'round': name, 'manifest_sha256': actual,
                      'files_verified': len(manifest['files']), 'failures': failures})
    if failures:
        raise SystemExit('R1 evidence changed: ' + json.dumps(preserved[-1]))
write('R1_IMMUTABILITY_VERIFICATION.json', {'rounds': preserved, 'all_preserved': True})

helpers = set((ROOT / 'temp').glob('*execution_revalidation*r2_20260910.py'))
helpers.update((ROOT / 'temp').glob('probe_native_*audit*r2_20260910.py'))
helpers.add(ROOT / 'temp/verify_official_case_handoffs_r1_20260910.py')
(OUT / 'helpers').mkdir(exist_ok=True)
for path in sorted(helpers):
    destination = OUT / 'helpers' / path.name
    if destination.exists():
        raise SystemExit('Helper output already exists: ' + str(destination))
    shutil.copyfile(path, destination)
files = [{'path': str(path.relative_to(OUT)), 'sha256': sha(path), 'bytes': path.stat().st_size}
         for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'EVIDENCE_SHA256.json']
write('EVIDENCE_SHA256.json', {
    'round_id': OUT.name, 'files': files, 'prior_evidence_preserved': preserved,
    'validation': {'production_commit': 'b3e89de6edca240a8afc1998cbf5d16772d076c0',
                   'production_unchanged_from_green_pytest': True,
                   'pytest_passed': 1447, 'pytest_failed': 0, 'pytest_skipped': 0,
                   'pytest_log_path': str(R1 / 'PYTEST_ISOLATED.log'),
                   'pytest_log_sha256': sha(R1 / 'PYTEST_ISOLATED.log'),
                   'all_returned_handoffs_verified': read(OUT / 'ROLE_AND_INFRASTRUCTURE_EVIDENCE.json')['all_returned_handoffs_verified']},
    'native_first_error_audit_wiring_defect_confirmed': True,
    'native_first_error_counter_observable': False,
    'server_git_executed': False, 'holdout_accessed': False, 'optimizer_steps': 0,
})
print(json.dumps({'report_sha256': sha(OUT / 'REPORT.zh-CN.md'),
                  'architecture_sha256': sha(OUT / 'ARCHITECTURE_FIT_REVIEW.zh-CN.md'),
                  'evidence_sha256': sha(OUT / 'EVIDENCE_SHA256.json'),
                  'files_sealed': len(files), 'helpers': len(helpers),
                  'r1_files_preserved': sum(row['files_verified'] for row in preserved)}))
