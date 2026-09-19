from pathlib import Path
import json,hashlib,sys,concurrent.futures
B=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916');sys.path.insert(0,str(B))
from rwkv_lh.stdio_corrections import validate_stdio_correction
from rwkv_lh.collection_acceptance import load_contract
from rwkv_lh import model_io
D=Path('/home/chase/GitHub/RWKV-LH-codex-corrections-r21-20260917');rows={r['id']:r for r in json.loads((D/'INVENTORY.json').read_text())['tasks']}
def run(target):
 ident=target['id'];output=D/'source_bound_validation'/ident
 if (output/'VALIDATION.json').exists():return
 binding=rows[ident]['original_binding'];candidate=D/'tasks'/ident/target['candidate']/'solution.py';assert hashlib.sha256(candidate.read_bytes()).hexdigest()==target['solution_sha256'];manifest=json.loads(Path(binding['manifest']).read_text());item=json.loads(Path(binding['conversion']).read_text());contract=load_contract(item)
 private=D/'private_cases'/f'{ident}.json';private.parent.mkdir(exist_ok=True);private.write_text(json.dumps(contract['cases'],ensure_ascii=False));reference={'path':str(private),'sha256':hashlib.sha256(private.read_bytes()).hexdigest()}
 text=json.dumps({'name':'write_file','arguments':{'path':'solution.py','content':candidate.read_text()}},ensure_ascii=False)+model_io.JSON_CALL_STOP_SUFFIXES[0];review=dict(target['source_review'],input_sha256=target['input_sha256'],target_sha256=hashlib.sha256(text.encode()).hexdigest(),task_sha256=target['task_sha256'])
 try:
  proof=validate_stdio_correction(run_root=Path(binding['source_root']),checkpoint_id=target['checkpoint'],target_text=text,model_sha256=target['model_sha256'],source_files=manifest['source_files'],cases_reference=reference,review=review,output=output);print(ident,proof['status'],flush=True)
 except Exception as exc:
  error=D/'source_bound_errors'/f'{ident}.json';error.parent.mkdir(exist_ok=True);error.write_text(json.dumps({'id':ident,'error_type':type(exc).__name__,'error':str(exc),'training_admitted':False}));print(ident,type(exc).__name__,str(exc),flush=True)
targets=json.loads((D/'REVIEWED_TARGETS.json').read_text())['targets']
with concurrent.futures.ThreadPoolExecutor(4) as pool:list(pool.map(run,targets))
