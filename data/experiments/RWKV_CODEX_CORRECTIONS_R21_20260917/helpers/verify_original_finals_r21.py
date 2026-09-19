from pathlib import Path
import json,sys,hashlib,concurrent.futures
B=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916');sys.path.insert(0,str(B))
from rwkv_lh.collection_acceptance import load_contract
from rwkv_lh.stdio_verifier import verify_python_submission
D=Path('/home/chase/GitHub/RWKV-LH-codex-corrections-r21-20260917')
def run(p):
 id=p.parent.name;proof=json.loads(p.with_name('PROVENANCE.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==proof['sha256'];item=json.loads((B/'inputs'/id/'ITEM.json').read_text());result=verify_python_submission(p.parent,load_contract(item)['cases']);dest=D/'results'/id/'original_final_recheck';dest.mkdir(parents=True,exist_ok=True);(dest/'RESULT.json').write_text(json.dumps({'id':id,'attempt':'original_final_recheck','author':'original_RWKV','passed':result['passed'],'details':result,'provenance':proof,'training_admitted':False},indent=2));print(id,result['passed'],flush=True)
with concurrent.futures.ThreadPoolExecutor(4) as pool:list(pool.map(run,(D/'original_finals').glob('*/solution.py')))
