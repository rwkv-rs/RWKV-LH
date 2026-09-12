from pathlib import Path
import sys,json,hashlib,tarfile
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments'/sys.argv[1]
# Raw evidence remains inspectable locally; bundle freezes the same artifacts for Git.
paths=[p for p in sorted(D.rglob('*')) if p.is_file() and p.name not in ['SHA256SUMS.json','RAW_EVIDENCE.tar.gz']]
with tarfile.open(D/'RAW_EVIDENCE.tar.gz','w:gz') as tar:
 for p in paths:
  if 'runs' in p.relative_to(D).parts or p.suffix=='.log' or 'initial_workspace' in p.relative_to(D).parts:tar.add(p,arcname=str(p.relative_to(D)))
checks={str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
checks['RAW_EVIDENCE.tar.gz']=hashlib.sha256((D/'RAW_EVIDENCE.tar.gz').read_bytes()).hexdigest()
(D/'SHA256SUMS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(D.name,hashlib.sha256((D/'SHA256SUMS.json').read_bytes()).hexdigest())
