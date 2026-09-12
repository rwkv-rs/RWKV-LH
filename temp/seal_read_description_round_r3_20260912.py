from pathlib import Path
import sys,json,hashlib,tarfile
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments'/sys.argv[1]
paths=[p for p in sorted(D.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name not in ['SHA256SUMS.json','RAW_EVIDENCE.tar.gz']]
with tarfile.open(D/'RAW_EVIDENCE.tar.gz','w:gz') as tar:
 for p in paths:
  if p.relative_to(D).parts[0] in ['before','after'] or p.suffix=='.log':tar.add(p,arcname=str(p.relative_to(D)))
checks={str(p.relative_to(D)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
checks['RAW_EVIDENCE.tar.gz']=hashlib.sha256((D/'RAW_EVIDENCE.tar.gz').read_bytes()).hexdigest()
(D/'SHA256SUMS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(hashlib.sha256((D/'SHA256SUMS.json').read_bytes()).hexdigest())
