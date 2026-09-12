from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'dataset_freeze_r2';D.mkdir(exist_ok=False)
from rwkv_lh.direct_trace_data import replay_run,protocol_identity,ROW_SCHEMA,ROLE,audit_source_similarity,executed_arguments
from rwkv_lh.model_io import JSON_CALL_STOP_SUFFIXES,parse_model_command
from rwkv_lh.statetune_data import FREEZE_SCHEMA,freeze_dataset
from rwkv_lh.token_budget import VOCAB_PATH,tokenizer
from rwkv_lh.schema import RunState

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
reg=json.loads((P/'collection/REGISTRATION.json').read_text());protocol,ph=protocol_identity();rows=[];sources=[]
for case in reg['cases']:
 if case['split']!='train':continue
 name=case['id'];root=P/'collection/runs'/name;source={**case,'source_id':name,'run_root':str(root),'manifest':ref(root/'FINALIZED_SOURCE_MANIFEST.json')};sources.append(source);replayed=replay_run(root,reg['model_sha256']);state=RunState.from_dict(json.loads((root/'state_snapshot.json').read_text()));cur=P/'curation'/name;proposal=json.loads((cur/'RESULT.json').read_text());codex=json.loads((cur/'CODEX_REVIEW.json').read_text())
 def row(e,text,kind,extra):
  return {'schema_version':ROW_SCHEMA,'role':ROLE,'input_protocol':protocol,'protocol_sha256':ph,'model_sha256':reg['model_sha256'],'tokenizer_sha256':sha(VOCAB_PATH),'split':'train','recomputed':True,'input_token_source':'server_returned_full',**{k:e[k] for k in ['input_token_ids','input_text','input_checkpoint_id','candidate_checkpoint_id','request_id']},'source_manifest_sha256':source['manifest']['sha256'],'source_content_sha256':source['source_content_sha256'],'family':source['family'],'source_id':name,'sample_id':name+'-'+kind,'target_text':text,'target_token_ids':tokenizer().encode(text),'target_token_source':'local_tokenizer_of_exact_admitted_label_with_production_stop','label_authority':kind,**extra}
 for e in replayed.values():
  command=parse_model_command(e['raw_generation']['raw_output'])
  if command.name!='read_file' or command.arguments.get('path')!=case['path']:continue
  actions=[a for a in state.actions.values() if a.action_type==command.name and dict(a.arguments)==executed_arguments(command) and a.result.get('success') is True and hashlib.sha256(a.result.get('output','').encode()).hexdigest()==case['source_content_sha256']]
  if not actions:continue
  # Only serialize the already generated real command and production stop, not selected parameters.
  text=json.dumps(command.to_wire_dict(),ensure_ascii=False)+JSON_CALL_STOP_SUFFIXES[0]
  rows.append(row(e,text,'executed_read',{'executed_action_id':actions[0].action_id,'real_tool_success':True,'original_raw_generation':e['raw_generation']}));break
 if proposal['accepted_by_api'] and codex['accepted']:
  e=json.loads((cur/'SOURCE_BOUNDARY.json').read_text());api={'reviewer':'deepseek-flash independent API factual review','accepted':True,'target_sha256':proposal['target_sha256'],'input_sha256':proposal['input_sha256'],'visible_evidence_only':True,'evidence':ref(cur/'REVIEW_RESPONSE.json')}
  rows.append(row(e,proposal['target_text'],'independent_review',{'reviews':[api,codex],'proposal_evidence':ref(cur/'TARGET_RESPONSE.json'),'original_raw_generation':e['raw_generation']}))
save(D/'REVIEWED_ROWS.json',{'rows':rows});evaluation=P/'evaluation/REGRESSION_REGISTRATION.json';er=json.loads(evaluation.read_text());audit=audit_source_similarity([*sources,*er['cases']],threshold=.90);save(D/'SIMILARITY_AUDIT.json',audit)
frozen={'schema_version':FREEZE_SCHEMA,'role':ROLE,'authorization':ref(P/'AUTHORIZATION.zh-CN.md'),'reviewed_rows':ref(D/'REVIEWED_ROWS.json'),'regression_registration':ref(evaluation),'regression_fingerprint':sha(evaluation),'sources':sources,'model_sha256':reg['model_sha256'],'context_tokens':8192,'vocab_size':65536,'bos_token_id':0,'similarity_threshold':.90,'similarity_audit':ref(D/'SIMILARITY_AUDIT.json'),'minimum_counts':{'train':16,'dev':4,'confirmation':4},'minimum_coverage':{'source_files':8,'families':3,'read_boundaries':8,'summary_boundaries':8},'generator_sha256':sha(Path(__file__))};save(D/'REGISTRATION.json',frozen)
print('rows',len(rows),'lengths',[(r['sample_id'],len(r['input_token_ids'])+len(r['target_token_ids'])-1) for r in rows],flush=True)
result=freeze_dataset(frozen,registration_reference=ref(D/'REGISTRATION.json'),output=R/'data/datasets/rwkv_direct_read_summary_v1');save(D/'RESULT.json',result)
