from pathlib import Path
import sys,json,collections,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.token_budget import tokenizer
D=R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912'
def save(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
reg=json.loads((D/'REGISTRATION.json').read_text()); results=[]
for p in sorted((D/'runs').glob('*/RESULT.json')):
 r=json.loads(p.read_text());s=json.loads((p.parent/'state_snapshot.json').read_text());trace=[json.loads(l) for l in (p.parent/'model_trace.jsonl').read_text().splitlines()]
 gens=[e for e in trace if e['type']=='model_session_generation_returned'];root=[v for v in s['model_states'].values() if v['parent_checkpoint_id'] is None]
 g=gens[0]['raw_generation'] if gens else {};ids=g.get('prompt_token_ids',[]);bos=g.get('input_bos_token_count');cp=root[0] if root else {};expected=tokenizer().encode(cp.get('transcript',''))
 r['token_audit']={'generations':len(gens),'input_tokens':len(ids),'output_tokens':len(g.get('raw_token_ids',[])),'input_scope':g.get('prompt_token_ids_scope'),'input_bos_token_count':bos,'input_equals_bos_plus_root_transcript':bool(ids) and isinstance(bos,int) and ids[bos:]==expected,'root_parent_none':bool(root) and cp['parent_checkpoint_id'] is None,'zero_profile':cp.get('state_profile_id')=='zero' and cp.get('state_profile_sha256')=='0'*64,'finish_reason':g.get('finish_reason'),'raw_output':g.get('raw_output'),'output_token_decoding':tokenizer().decode(g.get('raw_token_ids',[]))}
 results.append(r)
summary={'attempted':len(results),'diagnostic_pass':sum(r['pass'] for r in results),'tool_success':sum(r['tool_success'] for r in results),'protocol_errors':sum(bool(r['protocol_error']) for r in results),'infrastructure_errors':sum(bool(r['infrastructure_error']) for r in results),'input_token_exact':sum(r['token_audit']['input_equals_bos_plus_root_transcript'] for r in results),'categories':{},'cases':{}}
for c in reg['cases']:
 rr=[r for r in results if r['case']==c['id']];summary['cases'][c['id']]={'passes':sum(r['pass'] for r in rr),'attempts':len(rr),'stable':len(rr)==3 and all(r['pass'] for r in rr)}
for cat in sorted(set(c['category'] for c in reg['cases'])):
 names=[c['id'] for c in reg['cases'] if c['category']==cat];rr=[r for r in results if r['case'] in names];summary['categories'][cat]={'passes':sum(r['pass'] for r in rr),'attempts':len(rr),'stable':all(summary['cases'][n]['stable'] for n in names)}
save('TOKEN_AND_RESULT_AUDIT.json',results);save('SUMMARY.json',summary);print(json.dumps(summary,ensure_ascii=False))
