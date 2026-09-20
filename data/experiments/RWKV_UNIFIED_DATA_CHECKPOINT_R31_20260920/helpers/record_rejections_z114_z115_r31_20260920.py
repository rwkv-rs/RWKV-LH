from pathlib import Path
import json,hashlib,collections
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_UNIFIED_DATA_EXPANSION_R23_20260919';records=[]
for tag in ('z114','z115'):
 paths=list((D/'batches'/tag/'validation').glob('*/VALIDATION.json'));assert len(paths)==1;p=paths[0];v=json.loads(p.read_text());cases=v['after']['cases'];records.append({'batch':tag,'validation_path':str(p),'validation_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':v['status'],'passed_cases':sum(c['passed'] for c in cases),'total_cases':len(cases),'exit_codes':dict(collections.Counter(str(c.get('exit_code')) for c in cases)),'admitted':False,'root_cause':'not established; public crosscheck passed but fixed gate failed','private_inputs_or_expected_read_by_assistant':False,'rescore':False})
(D/'CANDIDATE_REJECTIONS_z114_z115.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
