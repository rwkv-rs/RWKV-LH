from pathlib import Path
import hashlib,json,sys
R=Path('/home/chase/GitHub/RWKV-LH'); E=R/'data/experiments';W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
sys.path.insert(0,str(W))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import SOURCE_CODE_PATHS
from rwkv_lh.role_trace_artifacts import _grams,_cosine_parts
O=E/'SELECTOR_500_SOURCE_INVENTORY_R1_20260911'
effective=[json.loads(x) for x in (E/'SELECTOR_500_EFFECTIVE_BATCH01_20260911/effective_candidates/candidates.jsonl').read_text().splitlines()]
grams=[(r['sample_id'],_grams(r['input_text'])) for r in effective]
records=[]
for name in ['ULTRADATA_COLLECTION_R4_20260910','ULTRADATA_OFFICIAL_COLLECTION_R5_20260910','REALPROJECT_HANDOFF_COLLECTION_R1_20260910']:
    B=E/name; m=json.loads((B/'selector_candidates/manifest.json').read_text())
    raw=[json.loads(x) for x in (B/'selector_candidates/candidates.jsonl').read_text().splitlines()]
    queue=B/'selector_candidates/review_queue.jsonl'
    pending=[json.loads(x) for x in queue.read_text().splitlines()] if queue.exists() else []
    manifest=json.loads((B/'all_zero/source_tree_manifest.json').read_text())
    frozen={r['path']:r['sha256'] for r in manifest}
    changed=[p for p in SOURCE_CODE_PATHS if frozen.get(p)!=hashlib.sha256((W/p).read_bytes()).hexdigest()]
    overlap=[]
    for row in raw+pending:
        g=_grams(row['input_text']);hit=None
        for sample_id,h in grams:
            dot,l,r=_cosine_parts(g,h)
            if l and r and dot*dot*10000>=9025*l*r:hit=sample_id;break
        overlap.append({'sample_id':row['sample_id'],'split':row.get('split'),'similar_to_effective_sample_id':hit})
    records.append({'collection':name,'automatic_rows':len(raw),'pending_rows':len(pending),
                    'candidate_source_changes_requiring_review':sorted(changed),'row_similarity_diagnostic':overlap})
out={'diagnostic_only':True,'admission_or_labels_granted':False,'new_effective_rows_claimed':0,'records':records,
     'notes':'Existing manifest and input rows only; no historical protocol replay, no model generation, no similarity policy changes. Pairwise overlap is not a substitute for full admitted-union transitive dedup.'}
with (O/'UNCONSUMED_YIELD_DIAGNOSTIC.json').open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
for r in records:print(r['collection'],r['automatic_rows'],r['pending_rows'],'source_changes',len(r['candidate_source_changes_requiring_review']),'similar',sum(x['similar_to_effective_sample_id'] is not None for x in r['row_similarity_diagnostic']))
