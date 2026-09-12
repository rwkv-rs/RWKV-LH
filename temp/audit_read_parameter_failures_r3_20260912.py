from pathlib import Path
import json,hashlib,shutil,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R3_20260912';D.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
old=R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912';records=[]
for p in sorted((old/'runs').glob('*/RESULT.json')):
 result=json.loads(p.read_text())
 if not result['protocol_error']:continue
 trace=p.parent/'model_trace.jsonl';events=[json.loads(l) for l in trace.read_text().splitlines()];g=next(e['raw_generation'] for e in events if e['type']=='model_session_generation_returned');state=json.loads((p.parent/'state_snapshot.json').read_text());root=next(c for c in state['model_states'].values() if c['parent_checkpoint_id'] is None)
 records.append({'source':str(p.parent.relative_to(R)),'trace_sha256':sha(trace),'state_snapshot_sha256':sha(p.parent/'state_snapshot.json'),'error':result['error'],'input_transcript':root['transcript'],'raw_generation':g})
save(D/'FAILURE_INPUT_OUTPUT_AUDIT.json',records)
print([(r['source'],r['raw_generation']['raw_output'],r['raw_generation']['finish_reason']) for r in records])
paths=subprocess.check_output(['git','diff','--name-only'],cwd=R,text=True).splitlines();save(D/'PREEXISTING_CHANGES.json',{'files':{p:sha(R/p) for p in paths},'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()})
source=D/'frozen_before';shutil.copytree(R/'rwkv_lh',source/'rwkv_lh',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
save(D/'SOURCE_BEFORE.json',{str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()})
fixture=R/'tests/fixtures/read_file_parameter_failures_r3.json';fixture.parent.mkdir(exist_ok=True);save(fixture,[{'source':r['source'],'trace_sha256':r['trace_sha256'],'raw_output':r['raw_generation']['raw_output']} for r in records])
