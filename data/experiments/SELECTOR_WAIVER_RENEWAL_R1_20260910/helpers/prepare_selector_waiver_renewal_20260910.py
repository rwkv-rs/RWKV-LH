"""Freeze a scoped renewal proposal; do not approve or extract it."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
ROOT = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(ROOT))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import SOURCE_CODE_PATHS, NON_WAIVABLE_PATHS
OLD = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
OUT = ROOT / 'data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910'
OUT.mkdir(exist_ok=True)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write(encoded(value))
registration = json.loads((OLD / 'SCOPED_SOURCE_REGISTRATION.json').read_text())
shutil.copyfile(OLD / 'SCOPED_SOURCE_REGISTRATION.json', OUT / 'SCOPED_SOURCE_REGISTRATION.json')
reg_sha = sha(OUT / 'SCOPED_SOURCE_REGISTRATION.json')
manifests = [json.loads(Path(row['artifacts']['source_tree_manifest']['path']).read_text()) for row in registration['source_runs']]
maps = [{row['path']: row['sha256'] for row in manifest} for manifest in manifests]
entries = []
old_entries = {row['path']: row for row in json.loads((OLD / 'SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json').read_text())['entries']}
for path in SOURCE_CODE_PATHS:
    current = sha(ROOT / path)
    frozen = {mapping.get(path) for mapping in maps}
    if len(frozen) != 1 or None in frozen:
        raise SystemExit('Source SHA is not uniform: ' + path)
    before = frozen.pop()
    if current == before:
        continue
    if path in NON_WAIVABLE_PATHS:
        raise SystemExit('Non-waivable source changed: ' + path)
    rationale = (
        'Renewal ONLY for selector_intent in the exact 14-source registration SHA256 ' + reg_sha +
        '; excludes old RP-WEB-02 and all atom/contract-graph runs. These historical sources use stateful_goal. '
        'Since the prior scoped approval, f34e4964 and 21c0cf45 connect audit observers and event ownership; '
        'the five role protocols, prompt builders and Native State payload/transition algorithms are unchanged. '
        'This is NOT global behavioral equivalence: observer exceptions are now isolated and atom clients have different lifetimes. '
        'Atom lifecycle changes are outside these actual source paths. The older execution and recovery repairs remain subject '
        'to the original restricted approval, including no run/check commands in these 14 sources. '
        'No missing historical error events may be invented. Complete role bytes/tokens, labels, coverage and fixed-split '
        'similarity gates remain mandatory. No other source, role, or training approval is implied.'
    )
    entries.append({'path': path, 'frozen_sha256': before, 'current_sha256': current,
                    'rationale': rationale, 'evidence_refs': [
                        str((OLD / 'WAIVER_RESULT.md').relative_to(ROOT)),
                        str((OUT / 'RENEWAL_DIFF.patch').relative_to(ROOT)),
                        str((OUT / 'SCOPED_SOURCE_REGISTRATION.json').relative_to(ROOT)),
                        str((OUT / 'REVIEW_ONE.md').relative_to(ROOT)),
                        str((OUT / 'REVIEW_TWO.md').relative_to(ROOT))]})
accepted = {'schema_version': 'rwkv-lh.role-trace-source-equivalence.v1', 'decision': 'accept',
            'reviewers': ['AI reviewer /root/waiver_review_one', 'AI reviewer /root/waiver_review_two'], 'entries': entries}
write('EQUIVALENCE_WAIVER_DRAFT.json', {**accepted, 'decision': 'draft'})
wrapper = (OLD / 'helpers/extract_scoped_waiver_r1_20260910.py').read_text().replace(OLD.name, OUT.name)
wrapper_path = OUT / 'extract_renewed_scoped_waiver_r1_20260910.py'
with wrapper_path.open('x') as stream:
    stream.write(wrapper)
patch = subprocess.check_output(['git', 'diff', 'b3e89de6..21c0cf45', '--', 'rwkv_lh', 'scripts/run_rwkv_e2e_benchmark.py'], cwd=ROOT)
(OUT / 'RENEWAL_DIFF.patch').write_bytes(patch)
write('SCOPED_WAIVER_PROPOSAL.json', {
    'registration_sha256': reg_sha, 'proposed_waiver': accepted,
    'prospective_waiver_sha256': hashlib.sha256(encoded(accepted)).hexdigest(),
    'wrapper_sha256': sha(wrapper_path), 'draft_sha256': sha(OUT / 'EQUIVALENCE_WAIVER_DRAFT.json'),
    'parent_waiver_sha256': sha(OLD / 'SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json'),
    'production_commit': subprocess.check_output(['git', 'rev-parse', '21c0cf45'], cwd=ROOT, text=True).strip(),
    'source_count': 14, 'role': 'selector_intent', 'excluded_source': 'RP-WEB-02',
    'expected_automatic_candidates': 60, 'expected_review_candidates': 126,
    'prior_waived_paths': sorted(old_entries), 'new_cumulative_waived_paths': [row['path'] for row in entries],
    'status': 'awaiting two independent approvals; draft is not admission authority',
})
print(json.dumps({'entries': len(entries), 'registration_sha256': reg_sha,
                  'prospective_waiver_sha256': hashlib.sha256(encoded(accepted)).hexdigest(),
                  'wrapper_sha256': sha(wrapper_path), 'paths': [row['path'] for row in entries]}))
