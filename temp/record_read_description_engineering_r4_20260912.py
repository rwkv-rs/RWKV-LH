from pathlib import Path
import json,hashlib,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pre=json.loads((D/'PREEXISTING_CHANGES.json').read_text());assert all(sha(R/p)==h for p,h in pre['files'].items())
record={'environment':'WSL UbuntuRecovered','regression_before':{'failed':5,'passed':1,'log_sha256':sha(D/'REGRESSION_RED.log')},'regression_after':{'failed':0,'passed':6,'log_sha256':sha(D/'REGRESSION_GREEN.log')},'full_tests':{'passed':1514,'skipped':0,'seconds':241.68,'log_sha256':sha(D/'PYTEST.log')},'production_change':'read_file descriptions only, original baseline compared with compact positive candidate; both frozen before sampling','preserved_preexisting_files':pre['files'],'server_source_verification_sha256':sha(D/'SERVER_SOURCE_VERIFICATION.json'),'local_vocab_sha256':sha(R/'rwkv_lh/data/rwkv_vocab_v20230424.txt'),'server_git_used':False,'training':False,'new_dataset_version':False,'github_updated':False,'project_ab_continued':False}
recoveries=[]
for arm in ['before','after']:
 for p in sorted((D/arm/'runs').glob('*/model_trace.jsonl')):
  events=list(map(json.loads,p.read_text().splitlines()));errors=[e for e in events if e['type'] in ['native_request_transport_error','native_request_resubmitted']]
  if errors:recoveries.append({'run':str(p.parent.relative_to(D)),'trace_sha256':sha(p),'events':errors,'generation_count':sum(e['type']=='model_session_generation_returned' for e in events)})
record['transport_recovery']=recoveries;record['transport_note']='Local 29613 listener disappeared during commit; remote service healthy. Same commit request ID and digest resubmitted once by existing Native recovery after forwarding restored. No extra generation or semantic retry. Cause of listener disappearance unknown.'
(D/'ENGINEERING_VALIDATION.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
(D/'DESCRIPTION_VS_R3.diff').write_bytes(subprocess.check_output(['git','diff','--','rwkv_lh/harness.py'],cwd=R));print('engineering records updated')
