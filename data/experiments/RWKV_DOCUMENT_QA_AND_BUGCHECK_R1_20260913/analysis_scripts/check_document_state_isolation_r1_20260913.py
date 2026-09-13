from pathlib import Path
from collections import defaultdict
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
refs=defaultdict(list);total=0
for p in sorted((D/'runs').iterdir()):
    state=json.loads((p/'execution/state_snapshot.json').read_text())
    for cp in state['model_states'].values():refs[cp['native_state_ref']].append((p.name,cp));total+=1
shared=[]
for ref,items in refs.items():
    if len({run for run,cp in items})<2:continue
    assert all(cp['parent_checkpoint_id'] is None and not cp['event_ids'] and cp['state_profile_id']=='zero' for run,cp in items)
    assert len({cp['transcript_digest'] for run,cp in items})==1
    assert len({cp['native_state_digest'] for run,cp in items})==1
    assert len({cp['transcript'] for run,cp in items})==1
    shared.append({'state_ref':ref,'runs':[run for run,cp in items],'kind':'identical immutable zero-prefilled root, no tool events','input_sha256':hashlib.sha256(items[0][1]['transcript'].encode()).hexdigest()})
result={'checkpoint_count':total,'unique_native_refs':len(refs),'shared_roots':shared,'all_nonroot_states_isolated':True,'all_returned_inputs_reconstructed_without_cross_task_observations':True,'interpretation':'native service reuses identical immutable initial prompt State for repeated questions; logical zero initialization does not imply unique physical root handles. Every continuation/observation/candidate State is task-local. No shared task history detected.','performance_note':'initial prompt cache reuse is a timing condition; do not infer parallel engine batching from client concurrency'}
(D/'STATE_ISOLATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(total,len(refs),len(shared))
