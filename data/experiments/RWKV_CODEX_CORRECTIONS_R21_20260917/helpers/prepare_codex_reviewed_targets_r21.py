from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
# Explicit author/reviewer selection after reading these public tasks and implementations.
# This is one Codex source review, not a claimed independent second model opinion.
selected=[7,8,11,16,17,32,43,44,50,56,65,70,71,73,74,82,86,87,88,90,93,99,103,104,105,107,114,115,119,122]
records=[]
for i in selected:
 row=rows[i];folder=D/'tasks'/row['id'];candidate=sorted(folder.glob('candidate_*/solution.py'))[-1];author=json.loads(candidate.with_name('AUTHOR.json').read_text());audit=json.loads((D/'boundary_audit'/(row['id']+'.json')).read_text());assert audit['replayed'] and audit['task_visible'];result=json.loads((D/'results'/row['id']/candidate.parent.name/'RESULT.json').read_text());assert result['passed'];records.append({'id':row['id'],'ordinal':i,'candidate':candidate.parent.name,'solution_sha256':author['solution_sha256'],'task_sha256':row['task_sha256'],'checkpoint':row['original_binding']['checkpoint'],'input_sha256':audit['input_sha256'],'model_sha256':audit['model_sha256'],'source_review':{'reviewer':'current Codex assistant, same author; explicit public specification and algorithm review','algorithm_assessment':author['reasoning'],'accepted':True,'visible_evidence_only':True,'source_consistent':True,'output_contract':'exact_unique','private_answers_read':False,'execution_claims_in_target':False,'limitations':'Single reviewer plus isolated execution; not two independent semantic reviews, not proof of universal correctness.'},'training_admitted':False})
(D/'REVIEWED_TARGETS.json').write_text(json.dumps({'count':len(records),'stage':'source-reviewed targets for fresh production admission validation, not frozen training rows','targets':records},ensure_ascii=False,indent=2));(D/'upload/REVIEWED_TARGETS.json').write_bytes((D/'REVIEWED_TARGETS.json').read_bytes())
