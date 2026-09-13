from pathlib import Path
import json,hashlib,tarfile,io
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
p=D/'advice_label_probe/runs/rag_overview-labelled-r1/execution'
items={name:p/name for name in ['RESULT.json','state_snapshot.json','model_trace.jsonl','PARENT_TRACE.jsonl']}
items['workspace/README.md']=D/'fixtures/rag_overview/README.md'
manifest={name:{'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()} for name,src in items.items()}
with tarfile.open(D/'CURRENT_REPLAY_FIXTURE.tar.gz','w:gz') as tar:
 for name,src in items.items():tar.add(src,arcname='current/'+name)
(D/'CURRENT_REPLAY_FIXTURE.json').write_text(json.dumps({'files':manifest,'purpose':'real production input replay regression only; answers are unqualified, not training labels or a dataset version'},indent=2)+'\n')
