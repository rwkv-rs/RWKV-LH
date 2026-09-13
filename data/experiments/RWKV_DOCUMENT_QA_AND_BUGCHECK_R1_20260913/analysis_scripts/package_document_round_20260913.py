from pathlib import Path
import json,tarfile,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
A=D/'analysis_scripts';A.mkdir(exist_ok=True)
for p in (R/'temp').glob('*document*20260913.py'):
 s=p.read_text()
 if 'RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913' not in s:continue
 if p.name.startswith('audit_document_'):
  # Replay must use the frozen renderer of that phase, never today's renderer.
  folder={'audit_document_agent_r1_20260913.py':'source','audit_document_budget_probe_r1_20260913.py':'../source'}.get(p.name,'source')
  s=s.replace('sys.path.insert(0,str(R))',f'sys.path.insert(0,str(D/"{folder}"))')
 (A/p.name).write_text(s)
for name in ['build_current_replay_fixture_r1_20260913.py','reproduce_reconsideration_r1_20260913.py']:
 shutil.copyfile(R/'temp'/name,A/name)
# Preserve all raw evidence and phase source snapshots, excluding bytecode caches.
roots=['runs','source','offline_reconsideration','budget_probe/runs','file_scope_probe/runs','file_scope_probe/source','requested_advice_probe/runs','requested_advice_probe/source','advice_label_probe/runs','advice_label_probe/source']
with tarfile.open(D/'EVIDENCE.tar.gz','w:gz') as out:
 for root in roots:
  for p in sorted((D/root).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:out.add(p,arcname=str(p.relative_to(D)),recursive=False)
files=[]
for p in sorted(D.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts:continue
 rel=str(p.relative_to(D))
 if rel=='FINAL_MANIFEST.json' or any(rel==x or rel.startswith(x+'/') for x in roots):continue
 files.append(dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
(D/'FINAL_MANIFEST.json').write_text(json.dumps(dict(files=files,raw_roots_in_evidence=roots),ensure_ascii=False,indent=2)+'\n')
print('archive',hashlib.sha256((D/'EVIDENCE.tar.gz').read_bytes()).hexdigest(),'files',len(files))
