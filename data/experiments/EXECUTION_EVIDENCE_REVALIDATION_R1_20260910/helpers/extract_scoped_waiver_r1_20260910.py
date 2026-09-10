"""Enforce the independently reviewed 14-source Selector-only extraction scope."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
EXPECTED_REGISTRATION = '0317d262960128fd43884ee7191c69bb15b5e54d645912446618b4c99366f6f7'
EXPECTED_IDS = {
    'RP-API-01', 'RP-API-02', 'RP-MAINT-01', 'RP-MAINT-02', 'RP-CLI-01', 'RP-CLI-02',
    'RP-DATA-01', 'RP-DATA-02', 'RP-FULL-01', 'RP-FULL-02', 'RP-WEB-01',
    'ULTRA-Code_00001', 'ULTRA-Code_00002', 'ULTRA-Code_00003',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise SystemExit(message)

require(len(sys.argv) == 1, 'This scope has no caller-selectable source, role or output')
registration = OUT / 'SCOPED_SOURCE_REGISTRATION.json'
require(sha(registration) == EXPECTED_REGISTRATION, 'Registration SHA mismatch')
sources = json.loads(registration.read_text())['source_runs']
require(len(sources) == 14 and {s['run_id'] for s in sources} == EXPECTED_IDS, 'Source scope mismatch')
proposal_path = OUT / 'SCOPED_WAIVER_PROPOSAL.json'
proposal = json.loads(proposal_path.read_text())
require(proposal['registration_sha256'] == EXPECTED_REGISTRATION, 'Proposal registration mismatch')
waiver = OUT / 'SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json'
require(sha(waiver) == proposal['prospective_waiver_sha256'], 'Waiver SHA mismatch')
require(json.loads(waiver.read_text()) == proposal['proposed_waiver'], 'Waiver content mismatch')
for suffix, reviewer in (('ONE', 'AI reviewer /root/waiver_review_one'), ('TWO', 'AI reviewer /root/waiver_review_two')):
    review = json.loads((OUT / f'SCOPED_APPROVAL_{suffix}.json').read_text())
    require(review['decision'] == 'accept' and review['reviewer'] == reviewer, 'Reviewer decision mismatch')
    require(review['registration_sha256'] == EXPECTED_REGISTRATION, 'Review registration mismatch')
    require(review['waiver_sha256'] == sha(waiver), 'Review waiver mismatch')
    require(review['wrapper_sha256'] == sha(Path(__file__)), 'Review wrapper mismatch')
    require(review['role'] == 'selector_intent', 'Review role mismatch')
command = [sys.executable, '-m', 'rwkv_lh.goal_state_protocols.role_trace_dataset_v1', 'extract',
           '--registration', str(registration), '--output', str(OUT / 'scoped_selector_candidates'),
           '--role', 'selector_intent', '--equivalence-waiver', str(waiver), '--waiver-sha256', sha(waiver)]
with (OUT / 'SCOPED_EXTRACTION_COMMAND.json').open('x') as f:
    json.dump({'command': command, 'registration_sha256': sha(registration), 'waiver_sha256': sha(waiver),
               'wrapper_sha256': sha(Path(__file__)), 'source_count': 14, 'role': 'selector_intent'}, f, indent=2)
    f.write('\n')
with (OUT / 'SCOPED_EXTRACTION.log').open('x') as log:
    result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
print(json.dumps({'extractor_exit_code': result.returncode, 'log': str(OUT / 'SCOPED_EXTRACTION.log')}))
sys.exit(result.returncode)
