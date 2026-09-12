from pathlib import Path
import sys,json,hashlib,copy
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.token_budget import tokenizer
D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R3_20260912'
reg=json.loads((D/'REGISTRATION.json').read_text());case_map={c['id']:c for c in reg['cases']}
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def normalized_prompt(text):
 prefix='System: Tools: ';assert text.startswith(prefix)
 first,rest=text[len(prefix):].split('\n',1);defs=json.loads(first)
 for d in defs:
  if d['name']=='read_file':
   d.pop('description',None)
   for p in d['parameters']['properties'].values():p.pop('description',None)
 return digest({'definitions':defs,'rest':rest})
summary={};details=[]
for arm in ['before','after']:
 rows=[]
 for p in sorted((D/arm/'runs').glob('*/RESULT.json')):
  r=json.loads(p.read_text());s=json.loads((p.parent/'state_snapshot.json').read_text());root=next(c for c in s['model_states'].values() if c['parent_checkpoint_id'] is None)
  trace=[json.loads(l) for l in (p.parent/'model_trace.jsonl').read_text().splitlines()];gs=[e['raw_generation'] for e in trace if e['type']=='model_session_generation_returned'];g=gs[0] if gs else {};ids=g.get('prompt_token_ids',[]);bos=g.get('input_bos_token_count');meta=root.get('native_state_metadata',{})
  row={'arm':arm,'case':r['case'],'suite':case_map[r['case']]['suite'],'repeat':r['repeat'],'pass':r['pass'],'tool_success':r['tool_success'],'protocol_error':r['protocol_error'],'infrastructure_error':r['infrastructure_error'],'error':r.get('error'),'raw_output':g.get('raw_output'),'input_tokens':len(ids),'output_tokens':len(g.get('raw_token_ids',[])),'finish_reason':g.get('finish_reason'),'full_input_scope':g.get('prompt_token_ids_scope'),'input_exact':isinstance(bos,int) and ids[bos:]==tokenizer().encode(root['transcript']),'input_sha256':digest(ids),'normalized_prompt_sha256':normalized_prompt(root['transcript']),'zero_root':root['state_profile_id']=='zero' and root['state_profile_sha256']=='0'*64,'model_sha256':meta.get('model_sha256'),'server_build':meta.get('server_build'),'tokenizer_build':meta.get('tokenizer_build'),'premature_final':(r.get('command') or {}).get('name')=='final_answer','handoff':r.get('observation_handoff'),'workspace_unchanged':r.get('workspace_unchanged',not bool(s['actions'])),'generations':len(gs)}
  rows.append(row)
 details.extend(rows);suites={}
 for suite in ['primary_r1_valid7','supplement_r2_missing1']:
  rr=[r for r in rows if r['suite']==suite];per=[]
  for n in range(1,4):
   nn=[r for r in rr if r['repeat']==n];per.append({'repeat':n,'pass':sum(r['pass'] for r in nn),'attempts':len(nn),'protocol_errors':sum(bool(r['protocol_error']) for r in nn),'premature_final':sum(r['premature_final'] for r in nn)})
  suites[suite]={'pass':sum(r['pass'] for r in rr),'attempts':len(rr),'repetitions':per}
 summary[arm]={'suites':suites,'protocol_errors':sum(bool(r['protocol_error']) for r in rows),'premature_final':sum(r['premature_final'] for r in rows),'input_exact':sum(r['input_exact'] for r in rows),'zero_root':sum(r['zero_root'] for r in rows),'attempts':len(rows),'cases':{c:{'pass':sum(r['pass'] for r in rows if r['case']==c),'attempts':sum(r['case']==c for r in rows),'identical_inputs':len(set(r['input_sha256'] for r in rows if r['case']==c))==1} for c in case_map}}
complete=all(summary[a]['attempts']==24 for a in ['before','after'])
paired={c:len(set(r['normalized_prompt_sha256'] for r in details if r['case']==c))==1 for c in case_map}
no_regression=all(not (summary['before']['cases'][c]['pass']==3 and summary['after']['cases'][c]['pass']!=3) for c in case_map)
last_two=all(x['pass']==x['attempts']==(7 if suite=='primary_r1_valid7' else 1) and x['protocol_errors']==0 and x['premature_final']==0 for suite,ss in summary['after']['suites'].items() for x in ss['repetitions'] if x['repeat'] in [2,3])
summary['gate']={'complete':complete,'last_two_full_passes':last_two,'no_baseline_3_of_3_regression':no_regression,'paired_inputs_only_read_descriptions_differ':all(paired.values()),'passed':complete and last_two and no_regression and all(paired.values()),'scope':'fixed single-read cases only; no autonomous-location run'}
(D/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(D/'CALL_AUDIT.json').write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
