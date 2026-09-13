from pathlib import Path
import json,sys,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913';P=D/'advice_label_probe';P.mkdir();(P/'contracts').mkdir()
reg=json.loads((D/'requested_advice_probe/REGISTRATION.json').read_text());reg['round']='RWKV_DOCUMENT_ADVICE_LABEL_PROBE_R1_20260913'
source={str(p.relative_to(R)):v.file_digest(p) for p in sorted((R/'rwkv_lh').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
for name in ['scripts/run_rwkv_read_only_agent.py','scripts/request_rwkv_read_only_advice.py','pyproject.toml','uv.lock']:source[name]=v.file_digest(R/name)
reg['source_pins']=source;reg['execution_identity']['source']=v.digest(source)
reg['budget']['strong_calls']=0;reg['budget']['reused_advice_receipts']=6;reg['execution_identity']['budget']=v.digest(reg['budget']);reg['order']=[['labelled',1],['labelled',2]]
reg['question']='Validate requested review advice as an owner-requested review turn, not Function output labelled as untrusted tool data. Keep original advice text and exact original file-scope parent State. No new strong calls.'
reg['comparison_limit']='New frozen candidate, not a causal A/B gain claim. Older source results are retained; opaque per-run IDs differ. Required advice payload stays byte-equivalent in its advice text. Outcome and false work claims still externally checked.'
for e in reg['schedule']:
    old=e['id'];e['id']=old.replace('-mixed-','-labelled-')
    if e['assistance']=='strong_advised':
        src=D/'requested_advice_probe/runs'/old/'advice';e['advice_source']=str(src);e['advice_sha256']=v.file_digest(src/'ADVICE.json')
    else:
        dest=P/'runs'/e['id']/'workspace';dest.parent.mkdir(parents=True);shutil.copytree(D/'fixtures'/e['case_id'],dest)
for c in reg['cases']:
    contract=v.load_contract(D/'requested_advice_probe/contracts'/f'{c["id"]}.json');contract['execution_identity']=reg['execution_identity'];v.freeze_contract(contract,P/'contracts'/f'{c["id"]}.json')
v.write_once(P/'REGISTRATION.json',reg)
for rel,sha in source.items():
    dest=P/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,dest)
print(v.file_digest(P/'REGISTRATION.json'))
