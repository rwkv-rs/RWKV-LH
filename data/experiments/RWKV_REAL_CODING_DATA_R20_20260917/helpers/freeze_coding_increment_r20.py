from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.direct_trace_data import freeze_direct_dataset,audit_source_similarity,ROLE
from rwkv_lh.statetune_data import FREEZE_SCHEMA
D=R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');return {'path':str(p),'sha256':sha(p)}
old=json.loads((R/'data/datasets/rwkv_direct_unified_corrections_v3/manifest.json').read_text());oldreg=json.loads(Path(old['freeze_registration']['path']).read_text());ref=oldreg['regression_registration'];assert 'holdout' not in ref['path'].lower();regression=json.loads(Path(ref['path']).read_text());assert all('holdout' not in str(c).lower() for c in regression['cases'])
rows=[json.loads(l) for l in (D/'READY_ROWS.jsonl').read_text().splitlines()];cases=json.loads((D/'REGISTRATION.json').read_text())['cases'];sources=[]
for row,c in zip(rows,cases):
 source=c['source'];root=Path(source['root']);m=json.loads(Path(source['manifest']).read_text());state=json.loads((root/'state_snapshot.json').read_text());meta=[x['native_state_metadata'] for x in state['model_states'].values()];keys=('model_sha256','server_build','tokenizer_build','protocol_version','state_format_version');identity={k:meta[0].get(k) for k in keys};assert all(all(x.get(k)==identity[k] for k in keys) for x in meta)
 collector=save('sources/'+c['id']+'/COLLECTOR.json',{'original_boundary_manifest':source['manifest'],'original_manifest_sha256':sha(Path(source['manifest'])),'converter_sha256':m['converter_sha256'],'protocol_module_sha256':m['protocol_module_sha256']})
 server=save('sources/'+c['id']+'/SERVER_IDENTITY.json',identity)
 sm=save('sources/'+c['id']+'/SOURCE_MANIFEST.json',{'source_type':'native_production_trace','model_sha256':source['model_sha256'],'collector_source_manifest_sha256':collector['sha256'],'server_identity_sha256':server['sha256'],'files':m['source_files']})
 p=D/'sources'/c['id']/'SOURCE_GOAL.txt';p.write_text(state['goal']['request']);row['source_manifest_sha256']=sm['sha256'];assert row['source_content_sha256']==sha(p)
 sources.append({'id':c['id'],'source_id':c['id'],'family':row['family'],'split':'train','run_root':str(root),'path':'SOURCE_GOAL.txt','source_content_sha256':sha(p),'content_reference':{'path':str(p),'sha256':sha(p)},'manifest':sm})
audit=audit_source_similarity([*sources,*regression['cases']],threshold=oldreg['similarity_threshold']);assert audit['passed']
auth=D/'AUTHORIZATION.zh-CN.md';auth.write_text('Owner于2026-09-17授权“开始吧，直到产生真实可用的数据”。本轮仅冻结三条真实编程任务诊断下一步纠正，使用现有生产协议与不变回归，不新建data/datasets版本，不训练。增量包留在本轮experiments下，供后续统一数据合并；不把本包当独立能力充分训练集。\n')
reg={'schema_version':FREEZE_SCHEMA,'role':ROLE,'authorization':{'path':str(auth),'sha256':sha(auth)},'reviewed_rows':save('REVIEWED_ROWS.json',{'rows':rows}),'regression_registration':ref,'regression_fingerprint':ref['sha256'],'sources':sources,'similarity_threshold':oldreg['similarity_threshold'],'similarity_audit':save('SIMILARITY_AUDIT.json',audit),'model_sha256':old['model_sha256'],'context_tokens':16384,'vocab_size':oldreg['vocab_size'],'bos_token_id':oldreg['bos_token_id'],'minimum_counts':{'train':3,'dev':4,'confirmation':4},'minimum_coverage':{'source_files':3,'families':2,'read_boundaries':0,'summary_boundaries':0,'command_boundaries':3}}
r=save('FREEZE_REGISTRATION.json',reg);result=freeze_direct_dataset(reg,registration_reference=r,output=D/'frozen_increment');save('FREEZE_RESULT.json',{'counts':result['counts'],'manifest_sha256':sha(D/'frozen_increment/manifest.json'),'training_steps':0,'regression':'existing unchanged cases; never supplied to teacher or training model','holdout_read':False});print('FROZEN',result['counts'])
