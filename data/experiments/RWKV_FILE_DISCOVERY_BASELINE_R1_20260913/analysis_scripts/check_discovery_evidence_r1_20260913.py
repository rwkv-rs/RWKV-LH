from pathlib import Path
import json,hashlib,sys
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';sys.path.insert(0,str(D/'source'))
from rwkv_lh.observation_funnel import project_action_result
from rwkv_lh.model_io import render_bootstrap
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.harness import ActionHarness
reg=json.loads((D/'RUN_REGISTRATION.json').read_text());rows=[]
for p in sorted((D/'dev').iterdir()):
 r=json.loads((p/'RESULT.json').read_text());s=json.loads((p/'state_snapshot.json').read_text());root=next(v for v in s['model_states'].values() if not v['parent_checkpoint_id']);tools=LongHorizonModel(ModelSession(client=object(),settings=RuntimeSettings(base_url='http://unused.invalid',api_key='',model='audit',tool_disclosure_mode='full')),harness=ActionHarness()).direct_definitions()
 row=dict(run=p.name,tool_observations=[],illegal_call_errors=[r['error']] if r['termination']=='ModelProtocolError' else [],root_contains_undefined_parameter_names={k:k in root['transcript'] for k in ['max_lines','max_text_bytes','"max_text"']})
 for n,a in enumerate(r['actions'],1):
  ev=json.loads((p/f'observation_{n}.json').read_text());obs=ev['payload']['result']['observation'];item=dict(operation=a['action_type'],success=a['result']['success'],projection_complete=obs['projection_complete'],source_bytes_verified=True,matching_paths=[])
  if a['result']['success'] and a['action_type']=='search_text':
   out=json.loads(a['result']['output']);projected=ev['payload']['result']['structured_output'];observed=projected['matches'];assert projected['match_count']==out['match_count'];assert len(observed)==len(out['matches']) if obs['projection_complete'] else True
   for m in out['matches']:
    b=(p/'workspace'/m['path']).read_bytes();raw=b[m['line_text_start_byte']:m['line_text_end_byte']];assert raw.decode()==m['line_text'] and hashlib.sha256(raw).hexdigest()==m['line_text_sha256'];assert hashlib.sha256(b).hexdigest()==out['source_snapshots'][m['path']]
   for m in observed:
    assert any(m['path']==z['path'] and m['line_text']==z['line_text'] for z in out['matches'])
   item['matching_paths']=sorted({m['path'] for m in observed})
  if a['result']['success'] and a['action_type']=='read_file':
   b=(p/'workspace'/a['arguments']['path']).read_bytes();ch=a['result']['metadata']['chunk'];assert a['result']['output'].encode()==b[ch['byte_start']:ch['byte_end']];assert ''.join(v['content'] for v in obs['exact_spans'])==a['result']['output'];item['matching_paths']=[a['arguments']['path']]
  row['tool_observations'].append(item)
 rows.append(row)
(D/'OBSERVATION_AUDIT.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print('observations verified',sum(len(r['tool_observations']) for r in rows))
