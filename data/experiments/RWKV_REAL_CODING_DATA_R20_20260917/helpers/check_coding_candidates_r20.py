from pathlib import Path
import sys,json
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import GoalState,TaskAction
from rwkv_lh import model_io
D=R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917'
for c in json.loads((D/'REGISTRATION.json').read_text())['cases']:
 f=D/c['id'];a=json.loads(Path(c['actual']).read_text());s=c['source'];snapshot=Path(s['root'])/'generation_snapshots'/a['request_id']/'before';cmd=model_io.parse_model_command(json.loads((f/'PACKET.json').read_text())['candidate']);goal=GoalState.create(request='External candidate verification',constraints=(),workspace_root=str(snapshot))
 obs=ActionHarness().execute(TaskAction(cmd.name,cmd.arguments),goal).to_dict();(f/'PREFLIGHT.json').write_text(json.dumps(obs,ensure_ascii=False,indent=2));print(c['id'],obs.get('exit_code'),obs.get('output','')[-900:],flush=True)
