"""Materialize only the exact proposal accepted by both independent AI reviewers."""
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
proposal = json.loads((OUT / 'SCOPED_WAIVER_PROPOSAL.json').read_text())
body = (json.dumps(proposal['proposed_waiver'], ensure_ascii=False, indent=2) + '\n').encode()
waiver_sha = hashlib.sha256(body).hexdigest()
wrapper_sha = hashlib.sha256((ROOT / 'temp/extract_scoped_waiver_r1_20260910.py').read_bytes()).hexdigest()
if waiver_sha != proposal['prospective_waiver_sha256']:
    raise SystemExit('Proposal serialization mismatch')
for suffix, reviewer in (('ONE', 'AI reviewer /root/waiver_review_one'), ('TWO', 'AI reviewer /root/waiver_review_two')):
    review = json.loads((OUT / f'SCOPED_APPROVAL_{suffix}.json').read_text())
    expected = {'decision': 'accept', 'reviewer': reviewer, 'waiver_sha256': waiver_sha,
                'wrapper_sha256': wrapper_sha, 'registration_sha256': proposal['registration_sha256'],
                'role': 'selector_intent'}
    if any(review.get(key) != value for key, value in expected.items()):
        raise SystemExit(f'Independent review mismatch: {suffix}')
with (OUT / 'SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json').open('xb') as f:
    f.write(body)
print(waiver_sha)
