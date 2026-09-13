from pathlib import Path
import json,hashlib,shutil,tarfile,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
reg=json.loads((D/'RUN_REGISTRATION.json').read_text());preserved=json.loads((D/'PREEXISTING.json').read_text());assert all(sha(R/f)==h for f,h in preserved.items());assert all(sha(D/'source'/f)==h for f,h in reg['source_pins'].items());assert all(sha(R/f)==h for f,h in reg['source_pins'].items());assert '1530 passed' in (D/'PYTEST_FULL.log').read_text();save(D/'FINAL_IDENTITY.json',dict(preexisting_preserved=True,production_source_unchanged=True,source_files=len(reg['source_pins']),preexisting_sha256=preserved,local_head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),github_updated=False,training_started=False,new_dataset_version=False))
adir=D/'analysis_scripts';adir.mkdir(exist_ok=False)
for n in ['prepare_discovery_r1_20260913.py','freeze_discovery_r1_20260913.py','run_discovery_r1_20260913.py','audit_discovery_r1_20260913.py','audit_direct_candidate_tasks_r2_20260913.py','check_discovery_evidence_r1_20260913.py','score_discovery_r1_20260913.py','seal_discovery_r1_20260913.py','verify_discovery_server_r1_20260913.py','verify_discovery_complete_inventory_r1_20260913.py','verify_discovery_complete_inventory_r2_20260913.py']:
 shutil.copy2(R/'temp'/n,adir/n)
files=[p for p in D.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('-wal','-shm'))];save(D/'EVIDENCE_FILES.json',{str(p.relative_to(D)):sha(p) for p in files})
a=D/'EVIDENCE.tar.gz'
with tarfile.open(a,'w:gz') as t:
 for p in files:t.add(p,arcname=str(p.relative_to(D)),recursive=False)
with tarfile.open(a) as t:
 for m in t:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==sha(D/m.name)
save(D/'SEAL.json',dict(files=len(files),archive_sha256=sha(a),manifest_sha256=sha(D/'EVIDENCE_FILES.json'),bytes=a.stat().st_size));print('sealed',len(files),sha(a))
