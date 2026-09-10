"""Create a concrete waiver proposal without activating admission."""
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
binding = json.loads((OUT / 'SCOPED_WAIVER_BINDING_DRAFT.json').read_text())
waiver = json.loads((ROOT / 'data/experiments/EXECUTION_EVIDENCE_REPAIR_R1_20260910/EQUIVALENCE_WAIVER_DRAFT.json').read_text())
waiver['decision'] = 'accept'
waiver['reviewers'] = ['AI reviewer /root/waiver_review_one', 'AI reviewer /root/waiver_review_two']
for entry in waiver['entries']:
    entry['rationale'] = (
        'Source identity proxy waiver ONLY for selector_intent in the exact 14-source registration SHA-256 '
        + binding['registration_sha256'] + '. Excludes RP-WEB-02. Enforced by the separately reviewed scoped extraction wrapper. '
        'The execution repairs DO change command semantics and check_command disclosure; this is NOT whole-program behavioral equivalence. '
        'Independent actual-source audit found no run_command/check_command in the included 14 sources. '
        'Retain historical facts unchanged; do not infer success for unknown requests or approve any semantic/corrected label. '
        'All source integrity, current-role byte reconstruction, complete token evidence, fixed split, similarity and coverage gates remain mandatory. '
        'No other sources, roles or training use are approved by this document.'
    )
    entry['evidence_refs'] = [
        str(OUT.relative_to(ROOT) / 'SCOPED_SOURCE_REGISTRATION.json'),
        str(OUT.relative_to(ROOT) / 'WAIVER_REVIEW_ONE_SELECTOR_SCOPE.md'),
        str(OUT.relative_to(ROOT) / 'WAIVER_SCOPED_REVIEW_TWO.md'),
        'temp/extract_scoped_waiver_r1_20260910.py',
    ]
encoded = (json.dumps(waiver, ensure_ascii=False, indent=2) + '\n').encode()
proposal = {'status': 'proposal_only_not_a_waiver', 'prospective_waiver_sha256': hashlib.sha256(encoded).hexdigest(),
            'registration_sha256': binding['registration_sha256'], 'proposed_waiver': waiver}
with (OUT / 'SCOPED_WAIVER_PROPOSAL.json').open('x') as f:
    json.dump(proposal, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(proposal['prospective_waiver_sha256'])
