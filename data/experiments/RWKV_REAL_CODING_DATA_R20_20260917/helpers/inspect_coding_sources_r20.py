from pathlib import Path
import sys,json
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.direct_trace_data import replay_run
D=R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917'
paths=[R/'data/experiments/RWKV_COLLECTION_DEPLOY_R9_20260915/boundaries/MANIFEST.json',*sorted((R/'data/experiments/RWKV_DUAL_COLLECTION_R10_20260916/tasks').glob('*/converted/boundaries/MANIFEST.json'))]
for i,p in enumerate(paths):
 m=json.loads(p.read_text());print(i,p,'keys',list(m)[:8]);root=Path(m['run_root']);model=m.get('model_sha256')
 if not model:
  state=json.loads((root/'state_snapshot.json').read_text());model=next(iter(state['model_states'].values()))['native_state_metadata']['model_sha256']
 try:replay=replay_run(root,model)
 except Exception as e:print('FAIL',e);continue
 folder=D/str(i);folder.mkdir(exist_ok=True);(folder/'SOURCE.json').write_text(json.dumps({'manifest':str(p),'model_sha256':model,'root':str(root)}))
 for j,(cp,a) in enumerate(replay.items()):
  (folder/f'input{j}.txt').write_text(a['input_text']);(folder/f'actual{j}.json').write_text(json.dumps({'checkpoint':cp,**a},ensure_ascii=False))
 print('boundaries',len(replay),'last raw',str(a['raw_generation']['raw_output'])[:180])
