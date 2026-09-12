from pathlib import Path
import tarfile,hashlib,json
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912'
with tarfile.open(D/'FROZEN_SOURCE_SNAPSHOTS.tar.gz','w:gz') as t:
 for arm in ['before','after']:
  root=D/('frozen_'+arm);manifest=json.loads((D/('SOURCE_'+arm.upper()+'.json')).read_text())
  for path,h in manifest.items():
   p=root/path;assert hashlib.sha256(p.read_bytes()).hexdigest()==h
   t.add(p,arcname=str(p.relative_to(D)))
print('source archive',hashlib.sha256((D/'FROZEN_SOURCE_SNAPSHOTS.tar.gz').read_bytes()).hexdigest())
