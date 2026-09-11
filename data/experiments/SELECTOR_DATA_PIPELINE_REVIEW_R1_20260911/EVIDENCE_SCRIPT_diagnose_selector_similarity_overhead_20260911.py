from pathlib import Path
import json,hashlib,math,sys
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911');sys.path.insert(0,str(W))
from rwkv_lh.role_trace_artifacts import _grams,_cosine_parts
E=R/'data/experiments';D=E/'SELECTOR_BOUNDARY_SIMILARITY_BATCH01_20260911';O=E/'SELECTOR_DATA_LATENCY_DIAGNOSIS_R1_20260911';O.mkdir(exist_ok=False)
manifest=json.loads((D/'union/manifest.json').read_text());rows={}
for item in manifest['provenance']['inputs']:
    for line in (Path(item['path'])/'candidates.jsonl').read_text().splitlines():
        row=json.loads(line);rows[row['sample_id']]=row
ledger=json.loads((D/'union.EXCLUSIONS.json').read_text())
different=[edge for edge in ledger['edges'] if rows[edge['witness'][0]]['target_text']!=rows[edge['witness'][1]]['target_text']]
examples=[]
for edge in different[:5]:
    a,b=(rows[s] for s in edge['witness']);dot,l,r=_cosine_parts(_grams(a['input_text']),_grams(b['input_text']))
    record={'cosine_full_input':dot/math.sqrt(l*r),'same_target':False,'samples':[]}
    for row in (a,b):
        prompt=row['input_text'];parts=prompt.split('SelectorIntentPromptV6: ',1)
        record['samples'].append({'sample_id':row['sample_id'],'source_run_id':row['source_run_id'],'run_id':row['run_id'],
            'target_text':row['target_text'],'label_authority':row['label_authority'],'input_bytes':len(prompt.encode()),
            'menu_and_role_prefix_bytes':len(parts[0].encode()) if len(parts)==2 else None,
            'objective':row['protocol_source']['current_subtask']['objective'],
            'input_sha256':hashlib.sha256(prompt.encode()).hexdigest()})
    examples.append(record)
out={'diagnostic_only':True,'policy_changed':False,'rows_rescored_or_readmitted':False,'input_rows':len(rows),
     'similarity_edges':len(ledger['edges']),'edges_with_different_targets':len(different),'examples':examples,
     'interpretation_limit':'Different targets inside a similarity component warrant semantic review; this alone does not prove all exclusions wrong or justify relaxing the frozen policy.'}
(O/'SIMILARITY_DIAGNOSIS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
