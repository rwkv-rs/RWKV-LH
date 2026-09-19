"""Freeze existing reviewed R21 labels; never author targets or run a model."""
from pathlib import Path
import sys, json, hashlib, concurrent.futures, traceback, shutil, subprocess
R=Path('/home/chase/GitHub/RWKV-LH'); sys.path.insert(0,str(R))
from rwkv_lh.direct_trace_data import freeze_direct_dataset, audit_source_similarity, protocol_identity, ROW_SCHEMA, ROLE
from rwkv_lh.statetune_data import FREEZE_SCHEMA, admit_dataset
from rwkv_lh.stdio_corrections import validate_stdio_correction
from rwkv_lh.role_trace_artifacts import byte_5gram_cosine
from rwkv_lh.token_budget import tokenizer, VOCAB_PATH
D=R/'data/experiments/RWKV_CODEX_FREEZE_R22_20260919'
P=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917'
B=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916/bulk_deployment'
REMOTE='/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916/'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path':str(p),'sha256':sha(p)}
def read(p): return json.loads(Path(p).read_text())
def save(p,x):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); data=(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
 if p.exists(): assert p.read_bytes()==data, f'Immutable output differs: {p}'
 else: p.write_bytes(data)
 return ref(p)
def local(p):
 assert str(p).startswith(REMOTE); return B/str(p)[len(REMOTE):]
def main():
 D.mkdir(exist_ok=True)
 targets=read(P/'REVIEWED_TARGETS.json')['targets']; early=read(P/'REVIEWED_EARLY_PRIME_TARGET_R3.json')['targets'][0]
 targets=[early if t['id']==early['id'] else t for t in targets]
 inventory={x['id']:x for x in read(P/'INVENTORY.json')['tasks']}
 packages=[R/'data/datasets/rwkv_direct_unified_corrections_v6',R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917/frozen_increment']
 old=read(packages[0]/'manifest.json'); oldreg=read(old['freeze_registration']['path']); regression_ref=oldreg['regression_registration']
 sources_identity={str(p.relative_to(R)):sha(p) for folder in ('rwkv_lh','scripts','tests') for p in sorted((R/folder).rglob('*.py'))}
 auth=D/'AUTHORIZATION.zh-CN.md'
 authtext='Owner连续授权Codex直接纠正1024题，并在303条正式数据、30条待冻结候选状态后指示“很好，继续吧”。本轮使用既有30条审核目标与真实生产边界，完成隔离、重放、fresh红绿、冻结及训练加载准入；仅写experiments增量，不创建data/datasets版本，不启动训练、不push。不把单动作纠正或工具提交算项目完成。\n'
 if not auth.exists(): auth.write_text(authtext)
 assert auth.read_text()==authtext
 registration={'round':'R22','scope':'freeze existing 30 R21 source-reviewed write_file boundaries','authorization':ref(auth),'selected':targets,'input_proofs':ref(P/'REVIEWED_TARGETS.json'),'early_override':ref(P/'EARLY_BOUNDARY_SELECTION.json'),'early_review':ref(P/'REVIEWED_EARLY_PRIME_TARGET_R3.json'),'prior_packages':[ref(p/'manifest.json') for p in packages],'regression_registration':regression_ref,'source_identity':sources_identity,'helper_sha256':sha(Path(__file__)),'local_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'limits':{'context_tokens':24576,'vocab_size':65536,'bos_token_id':0,'verification_workers':4,'per_case_timeout_seconds':3,'similarity_threshold':0.9},'rejection_policy':'Any source, context, similarity, replay or fresh execution failure prevents this fixed 30-row freeze. Preserve failures; no truncation, no score changes.','review_contract':'one source/algorithm review by same Codex author plus fresh isolated execution; not two independent semantic reviews','training_steps':0,'model_calls':0}
 save(D/'REGISTRATION.json',registration)
 oldrows=[]; oldsources={}
 for p in packages:
  m=read(p/'manifest.json'); admit_dataset(ref(p/'manifest.json'),role=ROLE,expected_regression=regression_ref['sha256'],model_sha256=old['model_sha256'],context_tokens=24576,vocab_size=65536,bos_token_id=0)
  oldrows += [json.loads(l) for l in (p/'train.jsonl').read_text().splitlines()]
  for s in m['sources']: oldsources[s['source_content_sha256']]=s
 # Existing production similarity function, unchanged threshold; compare train-train too.
 selected_text=[]
 for t in targets:
  task=P/'tasks'/t['id']/'TASK.md'; assert sha(task)==t['task_sha256']; selected_text.append((t,task.read_bytes().decode()))
 comparisons=[]; violations=[]
 for i,(t,text) in enumerate(selected_text):
  candidates=[(s['source_id'],Path(s['content_reference']['path']),s['content_reference']['sha256']) for s in oldsources.values()]
  candidates += [(other['id'],P/'tasks'/other['id']/'TASK.md',other['task_sha256']) for other,_ in selected_text[:i]]
  best={'cosine':-1}
  for ident,path,digest in candidates:
   assert sha(path)==digest
   cosine=byte_5gram_cosine(text,path.read_bytes().decode())
   pair={'left':t['id'],'right':ident,'cosine':cosine}
   if cosine>best['cosine']: best=pair
   if cosine>=0.9: violations.append(pair)
  comparisons.append({'id':t['id'],'compared_sources':len(candidates),'nearest':best})
 exclusion_paths=[R/f'data/experiments/{name}/evaluation/TRAINING_EXCLUSION.json' for name in ('RWKV_UNIFIED_CORRECTION_TRAIN_R5_300_20260915','RWKV_UNIFIED_CORRECTION_TRAIN_R6_ONE_EPOCH_20260915')]
 excluded=set()
 for p in exclusion_paths:
  for task in read(p)['tasks']: excluded.update(task['files'].values())
 overlaps=[t['id'] for t in targets if t['task_sha256'] in excluded]
 duplicate_boundaries=[]
 known={(r['request_id'],r['input_checkpoint_id']) for r in oldrows}
 for t in targets:
  proofpath=P/'source_bound_validation'/t['id']/'VALIDATION.json'
  if t['id']==early['id']: proofpath=Path(read(P/'EARLY_BOUNDARY_SELECTION.json')['proof_path'])
  proof=read(proofpath)
  if (proof['request_id'],proof['input_checkpoint_id']) in known: duplicate_boundaries.append(t['id'])
 audit={'algorithm':'production utf8_byte_5gram_count_cosine; bytes decoded without universal newline translation','threshold':0.9,'prior_rows':len(oldrows),'prior_distinct_content_hashes':len(oldsources),'selected':len(targets),'comparisons':comparisons,'violations':violations,'duplicate_boundaries':duplicate_boundaries,'exclusion_references':[ref(p) for p in exclusion_paths],'exclusion_hash_overlaps':overlaps,'limits':'Post-training exclusion checked by registered hashes only; no hidden answers or holdout read. Byte similarity is not a semantic-uniqueness proof.','passed':not violations and not overlaps and not duplicate_boundaries}
 save(D/'TRAIN_DUPLICATE_AUDIT.json',audit); print('DUPLICATE_AUDIT',audit['passed'],len(violations),flush=True); assert audit['passed']
 def validate(t):
  ident=t['id']; binding=inventory[ident]['original_binding']; manifest=read(local(binding['manifest'])); root=local(binding['source_root']); candidate=P/'tasks'/ident/t['candidate']/'solution.py'
  assert sha(candidate)==t['solution_sha256']
  oldproofpath=P/'source_bound_validation'/ident/'VALIDATION.json'
  if ident==early['id']: oldproofpath=Path(read(P/'EARLY_BOUNDARY_SELECTION.json')['proof_path'])
  oldproof=read(oldproofpath); assert oldproof['checkpoint_id']==t['checkpoint']
  target_text=oldproof['target_text'] # Preserve already-reviewed target bytes; no target generation.
  review=oldproof['review']; assert review['input_sha256']==t['input_sha256'] and review['task_sha256']==t['task_sha256']
  item=read(local(binding['conversion'])); ap=local(item['acceptance_path']); assert sha(ap)==item['acceptance_sha256']; contract=read(ap)
  private=R/'data/test_runs/codex_freeze_r22_private'/f'{ident}.json'; casesref=save(private,contract['cases'])
  output=D/'validation'/ident
  if (output/'VALIDATION.json').exists():
   v=read(output/'VALIDATION.json'); assert v['status']=='validated_candidate'
  else:
   v=validate_stdio_correction(run_root=root,checkpoint_id=t['checkpoint'],target_text=target_text,model_sha256=t['model_sha256'],source_files=manifest['source_files'],cases_reference=casesref,review=review,output=output)
  assert v['status']=='validated_candidate',ident
  state=read(root/'state_snapshot.json'); metas=[x['native_state_metadata'] for x in state['model_states'].values()]; keys=('model_sha256','server_build','tokenizer_build','protocol_version','state_format_version'); identity={k:metas[0].get(k) for k in keys}; assert all(all(m.get(k)==identity[k] for k in keys) for m in metas)
  collector=save(D/'sources'/ident/'COLLECTOR.json',{'original_boundary_manifest':ref(local(binding['manifest'])),'converter_sha256':manifest['converter_sha256'],'protocol_module_sha256':manifest['protocol_module_sha256'],'source_binding':binding,'r21_proof':ref(oldproofpath)})
  server=save(D/'sources'/ident/'SERVER_IDENTITY.json',identity)
  sm=save(D/'sources'/ident/'SOURCE_MANIFEST.json',{'source_type':'native_production_trace','model_sha256':t['model_sha256'],'collector_source_manifest_sha256':collector['sha256'],'collector_source_reference':collector,'server_identity_sha256':server['sha256'],'server_identity_reference':server,'files':manifest['source_files']})
  task=P/'tasks'/ident/'TASK.md'; source={'id':ident,'source_id':ident,'family':'ULTRADATA_RL_CODE','split':'train','run_root':str(root),'path':'TASK.md','source_content_sha256':sha(task),'content_reference':ref(task),'manifest':sm}
  version,protocol_sha=protocol_identity()
  row={'schema_version':ROW_SCHEMA,'role':ROLE,'split':'train','sample_id':'r22-'+ident,'source_id':ident,'family':source['family'],'source_manifest_sha256':sm['sha256'],'source_content_sha256':sha(task),'input_protocol':version,'protocol_sha256':protocol_sha,'model_sha256':t['model_sha256'],'tokenizer_sha256':sha(VOCAB_PATH),'recomputed':True,'input_token_source':'server_returned_full','candidate_checkpoint_id':t['checkpoint'],'input_checkpoint_id':v['input_checkpoint_id'],'request_id':v['request_id'],'input_text':v['input_text'],'input_token_ids':v['input_token_ids'],'target_text':target_text,'target_token_ids':tokenizer().encode(target_text),'label_authority':'verified_stdio','stdio_review':review,'stdio_validation':ref(output/'VALIDATION.json')}
  print('VALIDATED',ident,len(row['input_token_ids'])+len(row['target_token_ids'])-1,flush=True); return source,row
 with concurrent.futures.ThreadPoolExecutor(4) as pool: results=list(pool.map(validate,targets))
 sources=[s for s,r in results]; rows=[r for s,r in results]
 regression=read(regression_ref['path']); similarity=audit_source_similarity([*sources,*regression['cases']],threshold=0.9)
 assert similarity['passed']
 reg={'schema_version':FREEZE_SCHEMA,'role':ROLE,'authorization':ref(auth),'reviewed_rows':save(D/'REVIEWED_ROWS.json',{'rows':rows}),'regression_registration':regression_ref,'regression_fingerprint':regression_ref['sha256'],'sources':sources,'similarity_threshold':0.9,'similarity_audit':save(D/'SIMILARITY_AUDIT.json',similarity),'model_sha256':old['model_sha256'],'context_tokens':24576,'vocab_size':65536,'bos_token_id':0,'minimum_counts':{'train':30,'dev':4,'confirmation':4},'minimum_coverage':{'source_files':30,'families':1,'read_boundaries':0,'summary_boundaries':0,'stdio_boundaries':30}}
 regref=save(D/'FREEZE_REGISTRATION.json',reg)
 if not (D/'frozen_increment').exists(): freeze_direct_dataset(reg,registration_reference=regref,output=D/'frozen_increment')
 m,admitted=admit_dataset(ref(D/'frozen_increment/manifest.json'),role=ROLE,expected_regression=regression_ref['sha256'],model_sha256=old['model_sha256'],context_tokens=24576,vocab_size=65536,bos_token_id=0)
 assert sources_identity=={str(p.relative_to(R)):sha(p) for folder in ('rwkv_lh','scripts','tests') for p in sorted((R/folder).rglob('*.py'))}
 save(D/'RESULT.json',{'status':'frozen_loader_accepted','frozen_manifest':ref(D/'frozen_increment/manifest.json'),'new_rows':len(admitted),'previous_rows':len(oldrows),'aggregate_rows':len(oldrows)+len(admitted),'merged_dataset_created':False,'input_tokens':sum(len(r['input_token_ids']) for r in admitted),'target_tokens':sum(len(r['target_token_ids']) for r in admitted),'max_sequence_tokens':max(len(r['input_token_ids'])+len(r['target_token_ids'])-1 for r in admitted),'source_replay_and_fresh_red_green':len(rows),'training_steps':0,'agent_runs':0,'project_strict':None,'review_limitations':registration['review_contract'],'holdout_read':False,'source_identity_unchanged':True})
 print('FROZEN',len(admitted),flush=True)
if __name__=='__main__':
 try: main()
 except BaseException as e:
  D.mkdir(exist_ok=True); p=D/'failures'; p.mkdir(exist_ok=True); (p/f'{len(list(p.glob("*.json")))+1:03}.json').write_text(json.dumps({'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()},indent=2)); raise
