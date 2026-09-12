from pathlib import Path
import shutil,json,hashlib,time,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/collection';S=D/'source';S.mkdir()
for folder in ['rwkv_lh','scripts']:shutil.copytree(R/folder,S/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['pyproject.toml','uv.lock']:shutil.copyfile(R/name,S/name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pins={str(p.relative_to(S)):sha(p) for p in sorted(S.rglob('*')) if p.is_file()};(D/'SOURCE_MANIFEST.json').write_text(json.dumps(pins,indent=2)+'\n');reg=json.loads((D/'TASK_REGISTRATION.json').read_text());reg.update(frozen_at=time.time(),source_pins=pins,source_manifest_sha256=sha(D/'SOURCE_MANIFEST.json'),task_registration_sha256=sha(D/'TASK_REGISTRATION.json'),runner_sha256=sha(R/'temp/run_direct_collection_r1_20260913.py'),server_identity_sha256=sha(R/'data/experiments/RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913/SERVER_IDENTITY.json'));(D/'REGISTRATION.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n')
from rwkv_lh.direct_trace_data import audit_source_similarity,validate_split_isolation
validate_split_isolation(reg['cases']);a=audit_source_similarity(reg['cases'],threshold=reg['similarity_threshold']);assert a['passed'];(D/'SIMILARITY_AUDIT.json').write_text(json.dumps(a,indent=2)+'\n');print('frozen',len(pins),'sources; max cross-split cosine',max(x['cosine'] for x in a['pairs']))
