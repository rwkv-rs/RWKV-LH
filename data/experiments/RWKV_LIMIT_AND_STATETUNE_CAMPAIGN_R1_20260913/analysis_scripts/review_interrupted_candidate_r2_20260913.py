from pathlib import Path
import sys,json,hashlib,importlib.util
R=Path('/home/chase/GitHub/RWKV-LH');p=R/'temp/curate_direct_targets_r1_20260913.py';spec=importlib.util.spec_from_file_location('curation',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);D=m.D.parent/'curation_review_r2'
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='freeze':
 D.mkdir();save(D/'REGISTRATION.json',{'purpose':'One new externally registered review after file-05 API review interrupted; same immutable candidate and actual input; no semantic rewrite or retries','candidate_sha256':sha(m.D/'file-05/RESULT.json'),'input_sha256':sha(m.D/'file-05/SOURCE_BOUNDARY.json'),'settings':m.settings().public_dict(),'script_sha256':sha(Path(__file__)),'system':m.REVIEW_SYSTEM,'schema':m.REVIEW_SCHEMA,'max_calls':1,'max_tokens':4096})
else:
 reg=json.loads((D/'REGISTRATION.json').read_text());assert sha(Path(__file__))==reg['script_sha256'];assert sha(m.D/'file-05/RESULT.json')==reg['candidate_sha256'];assert sha(m.D/'file-05/SOURCE_BOUNDARY.json')==reg['input_sha256'];row=json.loads((m.D/'file-05/RESULT.json').read_text());e=json.loads((m.D/'file-05/SOURCE_BOUNDARY.json').read_text());request=m.payload(e,row['candidate']);save(D/'REQUEST.json',request)
 def audit(e):
  with (D/'strong_trace.jsonl').open('a') as f:f.write(json.dumps(dict(e),ensure_ascii=False)+'\n')
 client=m.OpenAICompatibleSupervisorClient(settings=m.settings(),audit_hook=audit)
 try:
  result=client._request_json(phase='candidate_review_r2',run_id='file-05',request_digest=m.digest(json.dumps(request,ensure_ascii=False,sort_keys=True)),system_prompt=reg['system'],request_payload=request,schema=reg['schema'],max_tokens=reg['max_tokens']);save(D/'RESULT.json',result)
 finally:client.close()
