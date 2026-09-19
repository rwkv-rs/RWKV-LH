from pathlib import Path
import json,hashlib,time,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.direct_trace_data import replay_run
from rwkv_lh.token_budget import tokenizer
from rwkv_lh import model_io
D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';B=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916/bulk_deployment';remote=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916');rows=json.loads((D/'INVENTORY.json').read_text())['tasks'];destination=D/'boundary_audit_corrected';destination.mkdir(exist_ok=True)
for row in rows:
 candidates=sorted((D/'tasks'/row['id']).glob('candidate_*/solution.py'))
 if not candidates:continue
 path=destination/(row['id']+'.json')
 if path.exists():continue
 binding=row['original_binding'];root=B/Path(binding['source_root']).relative_to(remote);record={'id':row['id'],'checkpoint':binding['checkpoint'],'training_admitted':False,'audit':'production replay and visibility only; not semantic approval'}
 try:
  manifest=json.loads((B/Path(binding['manifest']).relative_to(remote)).read_text())
  for name,digest in manifest['source_files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
  state=json.loads((root/'state_snapshot.json').read_text());states=state['model_states'];cp=next(iter(states.values())) if isinstance(states,dict) else states[0];model=cp['native_state_metadata']['model_sha256'];replayed=replay_run(root,model);actual=replayed[binding['checkpoint']];task=(D/'tasks'/row['id']/'TASK.md').read_bytes().decode('utf-8');visible=task in actual['input_text'] or json.dumps(task,ensure_ascii=False)[1:-1] in actual['input_text'];record.update(replayed=True,model_sha256=model,input_sha256=hashlib.sha256(actual['input_text'].encode()).hexdigest(),input_tokens=len(actual['input_token_ids']),task_visible=visible,original_parent=actual['input_checkpoint_id'],request_id=actual['request_id'],target_candidates=[])
  for candidate in candidates:
   # Same supported model command syntax; no manually constructed protocol state.
   target=json.dumps({'name':'write_file','arguments':{'path':'solution.py','content':candidate.read_text()}},ensure_ascii=False)+model_io.JSON_CALL_STOP_SUFFIXES[0]
   try:model_io.parse_model_command(target[:-len(model_io.JSON_CALL_STOP_SUFFIXES[0])]);legal=True
   except Exception:legal=False
   record['target_candidates'].append({'candidate':candidate.parent.name,'command_legal':legal,'target_tokens':len(tokenizer().encode(target)),'total_tokens':len(actual['input_token_ids'])+len(tokenizer().encode(target))-1})
 except Exception as exc:record.update(replayed=False,error_type=type(exc).__name__,error=str(exc))
 path.write_text(json.dumps(record,ensure_ascii=False,indent=2));print(row['ordinal'],row['id'],record.get('replayed'),record.get('task_visible'),record.get('error',''),flush=True)
