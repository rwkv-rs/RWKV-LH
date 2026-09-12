from pathlib import Path
import json,hashlib,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((D/'SUMMARY.json').read_text());assert s['gate']['passed']
rows=json.loads((D/'CALL_AUDIT.json').read_text());assert len(rows)==48
assert all(r['input_exact'] and r['zero_root'] and r['workspace_unchanged'] and r['generations']==1 for r in rows)
assert all(r['handoff']['present'] and r['handoff']['parent_matches'] for r in rows if not r['protocol_error'])
for key in ['server_build','tokenizer_build','model_sha256']:assert len({r[key] for r in rows})==1
reg=json.loads((D/'REGISTRATION.json').read_text());assert all(sha(R/p)==h for p,h in reg['source_pins'].items())
for name in ['RWKV_READ_PARAMETER_DESCRIPTION_R3_20260912']:
 old=R/'data/experiments'/name;m=json.loads((old/'SHA256SUMS.json').read_text());assert all(sha(old/p)==h for p,h in m.items())
pre=json.loads((D/'PREEXISTING_CHANGES.json').read_text());assert all(sha(R/p)==h for p,h in pre['files'].items())
record={'passed_gate':True,'model_generations':48,'input_token_exact':48,'zero_roots':48,'mutation_runs':0,'model_server_tokenizer_identity_constant':True,'source_commit_before_candidate_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'source_before_manifest_sha256':sha(D/'SOURCE_BEFORE.json'),'source_after_manifest_sha256':sha(D/'SOURCE_AFTER.json'),'preexisting_5_files_unchanged':True,'r3_sealed_evidence_unchanged':True,'test_source_sha256':sha(R/'tests/test_read_file_parameter_contract.py'),'retained':'compact R4 description only','next_stage_started':False}
(D/'FINAL_VERIFICATION.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
