from pathlib import Path
import json,hashlib,tarfile,shutil
R=Path('/home/chase/GitHub/RWKV-LH');P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
folders=['correction_r4','correction_r4b','correction_r5','collection','curation','curation_review_r2','dataset_freeze','dataset_freeze_r2','dataset_freeze_r3','artifact']
files=[p for d in folders for p in (P/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('-wal','-shm'))];pin={str(p.relative_to(P)):sha(p) for p in files}
(P/'PREPARATION_FILES.json').write_text(json.dumps(pin,indent=2)+'\n');archive=P/'PREPARATION_EVIDENCE.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(P)),recursive=False)
S=P/'analysis_scripts';S.mkdir(exist_ok=True)
for p in (R/'temp').glob('*20260913.py'):
 if p.stat().st_mtime >= (P/'AUTHORIZATION.zh-CN.md').stat().st_mtime:shutil.copyfile(p,S/p.name)
print('files',len(files),'archive',sha(archive))
