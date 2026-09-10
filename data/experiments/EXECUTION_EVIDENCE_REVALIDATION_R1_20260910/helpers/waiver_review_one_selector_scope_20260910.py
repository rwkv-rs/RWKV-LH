from pathlib import Path
import sys,json,hashlib,sqlite3,collections
ROOT=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(ROOT))
from rwkv_lh.schema import RunState
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.role_trace_inputs import rebuild_role_input
reg=ROOT/'data/experiments/REALPROJECT_OFFICIAL_COLLECTION_R3_20260910/COMBINED_SOURCE_REGISTRATION.json'
records=json.loads(reg.read_text())['source_runs'];out=[]
for record in records:
 p=Path(record['artifacts']['sqlite']['path']); assert hashlib.sha256(p.read_bytes()).hexdigest()==record['artifacts']['sqlite']['sha256']
 with sqlite3.connect(p.as_uri()+'?mode=ro&immutable=1',uri=True) as c:
  c.row_factory=sqlite3.Row
  final=RunState.from_dict(LongHorizonStore._deserialize(c.execute('SELECT state_json FROM runs WHERE run_id=?',(record['run_id'],)).fetchone()[0]))
  actions=[]
  for a in final.actions.values():
   actions.append({'action_id':a.action_id,'action_type':a.action_type,'status':str(a.status),'result':a.result})
  boundaries=[]
  for row in c.execute('SELECT revision,state_json FROM checkpoints WHERE run_id=? ORDER BY revision',(record['run_id'],)):
   raw=LongHorizonStore._deserialize(row['state_json']);order=raw.get('causal_order',[])
   if not order:continue
   e=final.causal_records[order[-1]]
   if e.event_type!='goal_role_input_boundary':continue
   snapshot=RunState.from_dict(raw)
   record_out={'boundary_event_id':e.event_id,'revision':row['revision'],'prior_actions':[a.action_id for a in snapshot.actions.values()]}
   matches=[]
   for selected in final.causal_records.values():
    if selected.event_type!='exact_tool_selection_staged' or selected.sequence<=e.sequence:continue
    intervening=any(x.event_type=='goal_role_input_boundary' and e.sequence<x.sequence<selected.sequence for x in final.causal_records.values())
    if not intervening:matches.extend(selected.payload.get('selection',{}).get('raw_selection',{}).get('lane_selections',{}).items())
   lanes=[]
   for menu,lane in matches:
    try:
     rebuilt=rebuild_role_input('selector_intent',snapshot,{'boundary_event_id':e.event_id,'menu_order_id':menu})
     text=rebuilt.get('expected_checkpoint_transcript') or rebuilt.get('full_input_text')
     checkpoint=final.model_states[lane['selector_checkpoint_id']]
     lanes.append({'request_id':lane['trace_id'],'menu':menu,'selected_operation':lane.get('selected_operation'),'byte_equal':checkpoint.transcript==text,'input_sha256':hashlib.sha256(text.encode()).hexdigest()})
    except Exception as ex:lanes.append({'request_id':lane.get('trace_id'),'menu':menu,'error':type(ex).__name__+': '+str(ex)})
   record_out['lanes']=lanes;boundaries.append(record_out)
 result={'run_id':record['run_id'],'source_run_id':record['source_run_id'],'sqlite_sha256':record['artifacts']['sqlite']['sha256'],'action_types':dict(collections.Counter(a['action_type'] for a in actions)),'actions':actions,'boundaries':boundaries}
 out.append(result);print(record['run_id'],result['action_types'],sum(len(b['lanes']) for b in boundaries),flush=True)
output=ROOT/'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/WAIVER_REVIEW_ONE_SELECTOR_SCOPE.json'
output.write_text(json.dumps({'mode':'read-only boundary diagnosis; no source admission or waiver approval','registration_sha256':hashlib.sha256(reg.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sources':out},ensure_ascii=False,indent=2)+'\n')
