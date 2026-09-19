from pathlib import Path
import sys,json,time,hashlib
from dataclasses import replace
D=Path('/home/chase/GitHub/RWKV-LH-unified-train-r29-647-20260920/evaluation_r30');sys.path.insert(0,str(D/'source'))
from rwkv_lh.runtime.settings import get_runtime_settings,direct_agent_settings
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.coding_agent import CodingJob,run_coding_job
from rwkv_lh.model_session import create_model_session,SessionSampling
from rwkv_lh.correction_snapshots import generation_snapshot_audit
from rwkv_lh.collection_retirement import seal_run,release_sealed_run
from rwkv_lh.collection_execution import service_fingerprint
from rwkv_lh.inference.uploaded_sources import verify_manifest,PROJECT_SCHEMA,digest

def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.pending');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
reg=json.loads((D/'REGISTRATION.json').read_text());identity=json.loads((D/'RUNNER_IDENTITY.json').read_text());assert digest(Path(__file__))==identity['runner_sha256'];assert digest(D/'REGISTRATION.json')==identity['registration_sha256'];assert digest(D/'EXECUTION_TASKS.json')==reg['cases_sha256'];assert json.loads((D/'MODEL_SOURCE_PREFLIGHT.json').read_text())['status']=='passed';verify_manifest(D/'PROJECT_SOURCE.json',reg['source_manifest_sha256'],expected_schema=PROJECT_SCHEMA)
p=reg['sampling'];config=direct_agent_settings(replace(get_runtime_settings(),base_url=reg['base_url'],model=reg['model'],model_sha256=reg['model_sha256'],max_model_len=reg['context_tokens'],state_profile_id='zero',state_profile_sha256='0'*64,state_transport='native_required',return_token_ids=True,read_timeout_seconds=300,action_max_output_tokens=reg['output_tokens'],default_temperature=p['temperature'],default_top_p=p['top_p'],default_top_k=p['top_k'],default_presence_penalty=p['presence_penalty'],default_frequency_penalty=p['frequency_penalty'],default_penalty_decay=p['penalty_decay'],tool_disclosure_mode='full'))
service=service_fingerprint(config);client=OpenAICompatibleRWKVClient(config);save(D/'CAPABILITIES.json',client._request_json('GET','/capabilities')[0]);expected_sampling=SessionSampling.from_settings(config).to_dict();cases=json.loads((D/'EXECUTION_TASKS.json').read_text());records=[];start=time.monotonic();allocated=0;save(D/'STATUS.json',{'status':'running','completed_tasks':0,'accepted_tasks':None,'training_completed_before_evaluation':True})
try:
 for repeat in reg['repeats']:
  for case in cases:
   for arm in (reg['arms'] if repeat==1 else list(reversed(reg['arms']))):
    if time.monotonic()-start>=reg['wall_budget_seconds']:raise RuntimeError('Registered campaign wall budget exhausted')
    allocated+=case['max_calls'];assert allocated<=reg['max_generation_calls'];source=D/'tasks'/case['id'];assert all(digest(source/name)==h for name,h in case['files'].items());rid=f"{case['id']}--{arm}--r{repeat}";out=D/'runs'/rid;assert not out.exists();save(D/'STATUS.json',{'status':'running','current':rid,'completed_tasks':len(records),'accepted_tasks':None,'training_completed_before_evaluation':True})
    def factory(*,settings,audit_hook):
     wrapped=generation_snapshot_audit(workspace=out/'workspace',output=out/'execution',audit_hook=audit_hook)
     def audit(event):
      if event.get('type')=='model_session_generation_started':assert event['sampling']==expected_sampling
      wrapped(event)
     return create_model_session(settings=settings,audit_hook=audit)
    profile=reg['profiles'][arm];arm_config=replace(config,state_profile_id=profile['id'],state_profile_sha256=profile['sha256'])
    then=time.monotonic();result=run_coding_job(CodingJob(case['id'],case['request'],str(source),str(out),case['max_calls'],case['max_seconds']),settings=arm_config,session_factory=factory);item={'id':rid,'case':case['id'],'arm':arm,'repeat':repeat,'seconds':time.monotonic()-then,'result':result,'acceptance':'pending_external_review'};save(out/'COLLECTION_RESULT.json',item);records.append(item);save(D/'RESULTS.json',records)
    if result.get('termination_reason')=='model_transport_unavailable':raise RuntimeError('Transport failure: preserve evidence and stop, do not count unrun tasks as failures')
    seal_run(out/'execution',out/'sealed',reg['model_sha256'],expected_state_profile=profile);release_sealed_run(out/'execution',out/'sealed',client,expected_service=service);print(rid,result['termination'],result.get('generation_started'),flush=True)
 verify_manifest(D/'PROJECT_SOURCE.json',reg['source_manifest_sha256'],expected_schema=PROJECT_SCHEMA);save(D/'STATUS.json',{'status':'generation_finished_acceptance_pending','completed_tasks':len(records),'accepted_tasks':None,'seconds':time.monotonic()-start,'training_completed_before_evaluation':True})
except BaseException as exc:
 save(D/'STATUS.json',{'status':'stopped_error','completed_tasks':len(records),'accepted_tasks':None,'exception_type':type(exc).__name__,'message':str(exc),'training_completed_before_evaluation':True});raise
