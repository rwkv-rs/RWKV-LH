"""Publish only the exact jointly accepted proposal, then run its fixed wrapper."""
from pathlib import Path
import hashlib
import json
import subprocess
ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910'
proposal = json.loads((OUT / 'SCOPED_WAIVER_PROPOSAL.json').read_text())
wrapper = OUT / 'extract_renewed_scoped_waiver_r1_20260910.py'
for suffix, who in (('ONE', 'one'), ('TWO', 'two')):
    review = json.loads((OUT / f'SCOPED_APPROVAL_{suffix}.json').read_text())
    checks = [review['decision'] == 'accept', review['reviewer'] == 'AI reviewer /root/waiver_review_' + who,
              review['registration_sha256'] == proposal['registration_sha256'],
              review['waiver_sha256'] == proposal['prospective_waiver_sha256'],
              review['wrapper_sha256'] == hashlib.sha256(wrapper.read_bytes()).hexdigest(),
              review['role'] == 'selector_intent', proposal['source_count'] == 14]
    if not all(checks):
        raise SystemExit('Review mismatch: ' + suffix)
data = (json.dumps(proposal['proposed_waiver'], ensure_ascii=False, indent=2) + '\n').encode()
if hashlib.sha256(data).hexdigest() != proposal['prospective_waiver_sha256']:
    raise SystemExit('Prospective waiver bytes mismatch')
with (OUT / 'SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json').open('xb') as stream:
    stream.write(data)
result = subprocess.run([str(ROOT / '.venv/bin/python'), str(wrapper)], cwd=ROOT)
if result.returncode not in (0, 2):
    raise SystemExit(result.returncode)
old = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/scoped_selector_candidates'
new = OUT / 'scoped_selector_candidates'
comparisons = {}
for name in ('candidates.jsonl', 'review_queue.jsonl'):
    before = [json.loads(line) for line in (old / name).read_text().splitlines()]
    after = [json.loads(line) for line in (new / name).read_text().splitlines()]
    comparisons[name] = {'before': len(before), 'after': len(after), 'full_rows_equal': before == after}
manifest = json.loads((new / 'manifest.json').read_text())
summary = {'extractor_exit_code': result.returncode, 'source_admission_restored': True,
           'candidate_status': manifest['status'], 'row_preservation': comparisons,
           'manifest_sha256': hashlib.sha256((new / 'manifest.json').read_bytes()).hexdigest(),
           'waiver_sha256': proposal['prospective_waiver_sha256'], 'optimizer_steps': 0}
with (OUT / 'EXTRACTION_RESULT.json').open('x') as stream:
    json.dump(summary, stream, indent=2)
    stream.write('\n')
print(json.dumps(summary))
