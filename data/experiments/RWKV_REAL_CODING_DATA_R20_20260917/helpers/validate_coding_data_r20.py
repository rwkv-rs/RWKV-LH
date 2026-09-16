from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.command_corrections import validate_command_correction,revalidate_training_command
from rwkv_lh.direct_trace_data import ROW_SCHEMA,ROLE,protocol_identity,normalize_direct_row
from rwkv_lh.token_budget import tokenizer,VOCAB_PATH
D=R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
rows=[];outcomes=[]
for c in json.loads((D/'REGISTRATION.json').read_text())['cases']:
 f=D/c['id'];a=json.loads(Path(c['actual']).read_text());source=c['source'];m=json.loads(Path(source['manifest']).read_text());target=(f/'TARGET.txt').read_text();reviews=[]
 for index,name in enumerate(['reviews_v2','reviews_v2_second']):
  p=D/name/c['id']/'QWEN_REVIEW.json';review=json.loads(p.read_text());assert review['accepted'],(c['id'],name,review)
  assert review['input_sha256']==digest(a['input_text']);assert review['candidate_sha256']==digest(json.loads((f/'PACKET.json').read_text())['candidate'])
  reviews.append({'reviewer':f'Qwen3.8-27B/independent-context-{index+1}','accepted':True,'visible_evidence_only':True,'input_sha256':digest(a['input_text']),'target_sha256':digest(target),'review_path':str(p),'review_sha256':sha(p)})
 v=validate_command_correction(run_root=source['root'],checkpoint_id=a['checkpoint'],target_text=target,model_sha256=source['model_sha256'],source_files=m['source_files'],reviews=reviews,expected_exit_code=c['expected_exit_code'],expected_output=c['expected_output'],output=f/'validation')
 assert v['status']=='validated_candidate',(c['id'],v['status'])
 protocol,protocolsha=protocol_identity();row={'schema_version':ROW_SCHEMA,'role':ROLE,'split':'train','recomputed':True,'sample_id':'R20-'+c['id'],'source_id':c['id'],'family':'LOGURU' if c['id'].startswith('loguru') else 'ANYIO','input_protocol':protocol,'protocol_sha256':protocolsha,'model_sha256':source['model_sha256'],'tokenizer_sha256':sha(VOCAB_PATH),'source_manifest_sha256':sha(Path(source['manifest'])),'source_content_sha256':digest(json.loads((Path(source['root'])/'state_snapshot.json').read_text())['goal']['request']),'candidate_checkpoint_id':a['checkpoint'],'input_checkpoint_id':a['input_checkpoint_id'],'request_id':a['request_id'],'input_text':a['input_text'],'input_token_ids':a['input_token_ids'],'input_token_source':'server_returned_full','target_text':target,'target_token_ids':tokenizer().encode(target),'label_authority':'verified_command','reviews':reviews,'command_validation':{'path':str(f/'validation/VALIDATION.json'),'sha256':sha(f/'validation/VALIDATION.json')}}
 normalize_direct_row(row,model_sha256=source['model_sha256'],context_tokens=16384,vocab_size=65536,bos_token_id=0)
 revalidate_training_command(row,run_root=source['root'],source_files=m['source_files'],model_sha256=source['model_sha256'],output=f/'fresh_validation')
 rows.append(row);outcomes.append({'id':row['sample_id'],'status':'validated_twice','input_tokens':len(row['input_token_ids']),'target_tokens':len(row['target_token_ids']),'expected_failure_is_diagnostic':True,'task_completed':False});print(outcomes[-1],flush=True)
(D/'READY_ROWS.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows));(D/'RESULTS.json').write_text(json.dumps({'rows':outcomes,'new_training_ready_boundaries':len(rows),'independent_tasks':3,'repository_families':2,'dataset_version_published':False,'training_steps':0,'complete_coding_tasks':0},indent=2))
