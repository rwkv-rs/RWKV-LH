from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
for p in sorted((D/'runs').iterdir()):
    if (p/'execution/RESULT.json').exists():
        r=json.loads((p/'execution/RESULT.json').read_text());print(p.name,r['termination'],r['generation_started'],round(r['elapsed_seconds'],1))
    elif (p/'execution/model_trace.jsonl').exists():
        es=[json.loads(x) for x in (p/'execution/model_trace.jsonl').read_text().splitlines()]
        print(p.name,'running',sum(e['type']=='model_session_generation_started' for e in es))
