from pathlib import Path
import json,shutil,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917'
# Preserve evidence of the diagnostic helper's false negatives before rerunning.
shutil.copytree(D/'boundary_audit',D/'boundary_audit_initial_newline_bug',dirs_exist_ok=False)
shutil.copyfile(D/'ALTERNATIVE_VISIBLE_BOUNDARIES.json',D/'ALTERNATIVE_VISIBLE_BOUNDARIES_INITIAL_NEWLINE_BUG.json')
for name in ['audit_codex_source_boundaries_r21.py','find_visible_boundaries_r21.py']:
 p=R/'temp'/name;s=p.read_text();s=s.replace("/'TASK.md').read_text()","/'TASK.md').read_bytes().decode('utf-8')");s=s.replace("destination=D/'boundary_audit'","destination=D/'boundary_audit_corrected'");s=s.replace("(D/'boundary_audit').glob", "(D/'boundary_audit_corrected').glob");p.write_text(s)
rows=json.loads((D/'INVENTORY.json').read_text())['tasks'];cases=[]
for row in rows:
 p=D/'tasks'/row['id']/'TASK.md';raw=p.read_bytes();normalized=p.read_text()
 if b'\r\n' in raw:
  cases.append({'id':row['id'],'sha256':hashlib.sha256(raw).hexdigest(),'raw_length':len(raw),'normalized_length':len(normalized.encode()),'read_text_changes_bytes':normalized.encode()!=raw,'byte_decode_roundtrip':raw.decode('utf-8').encode()==raw})
assert cases and all(c['read_text_changes_bytes'] and c['byte_decode_roundtrip'] for c in cases)
(D/'AUDIT_NEWLINE_REGRESSION.json').write_text(json.dumps({'scope':'Temporary diagnostic helper only; production stdio admission already decodes raw bytes','affected_source_files':len(cases),'red':'read_text universal-newline conversion changes source bytes','green':'read_bytes().decode preserves bytes','cases':cases},indent=2));print('CRLF sources',len(cases))
