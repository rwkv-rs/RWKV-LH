from pathlib import Path
import json,hashlib,tarfile,shutil
R=Path('/home/chase/GitHub/RWKV-LH');P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';folders=['training_runtime','training','evaluation','evaluation_service','artifact_index_r2'];files=[p for d in folders for p in (P/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('-wal','-shm'))]
files += [P/'TRAINING_R1.log',P/'EVAL_SERVICE_R1.log',P/'EVAL_SERVICE_R2.log'];pin={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(P/'TRAINING_R1_FILES.json').write_text(json.dumps(pin,indent=2)+'\n')
archive=P/'TRAINING_R1_EVIDENCE.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as t:
 for p in files:t.add(p,arcname=str(p.relative_to(P)),recursive=False)
print('files',len(files),'archive',hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes',archive.stat().st_size)
