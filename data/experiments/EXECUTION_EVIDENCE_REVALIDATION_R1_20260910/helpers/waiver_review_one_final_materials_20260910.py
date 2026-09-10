from pathlib import Path
import hashlib,json
r=Path('/home/chase/GitHub/RWKV-LH');d=r/'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
original=json.loads((r/'data/experiments/REALPROJECT_OFFICIAL_COLLECTION_R3_20260910/COMBINED_SOURCE_REGISTRATION.json').read_text())
scoped=json.loads((d/'SCOPED_SOURCE_REGISTRATION.json').read_text());expected=dict(original);expected['source_runs']=[x for x in original['source_runs'] if x['run_id']!='RP-WEB-02']
scoped['source_runs'].sort(key=lambda x:x['run_id']);expected['source_runs'].sort(key=lambda x:x['run_id'])
p=json.loads((d/'SCOPED_WAIVER_PROPOSAL.json').read_text());encoded=(json.dumps(p['proposed_waiver'],ensure_ascii=False,indent=2)+'\n').encode()
print(json.dumps({'registration_exact_original_minus_web02':scoped==expected,'prospective_hash_matches':hashlib.sha256(encoded).hexdigest()==p['prospective_waiver_sha256'],'registration_sha':hashlib.sha256((d/'SCOPED_SOURCE_REGISTRATION.json').read_bytes()).hexdigest(),'wrapper_sha':hashlib.sha256((r/'temp/extract_scoped_waiver_r1_20260910.py').read_bytes()).hexdigest()}))
