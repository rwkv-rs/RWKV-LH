from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
manifest=json.loads((R/'data/experiments/FULL_TRACE_DEPLOYMENT_R2_20260911/PROJECT_SOURCE.json').read_text());pins={x['path']:x['sha256'] for x in manifest['files']};records=[]
for path in ['rwkv_lh/inference/native_state_service.py','rwkv_lh/runtime/native_request_recovery.py']:
    sha=hashlib.sha256((R/path).read_bytes()).hexdigest();assert sha==pins[path];records.append({'path':path,'sha256':sha,'matches_verified_uploaded_service':True})
(D/'SERVICE_SERIALIZATION.json').write_text(json.dumps({'sources':records,'observed':'native service dispatch holds request_lock through journal invocation; generate also holds service.lock around generation and published State materialization','meaning':'independent client jobs currently queue at shared native service; client concurrency alone does not expose engine batch throughput','not_measured':'no attribution of all latency to locks; no lock-removal experiment','future_validation':'isolate per-request identities, sampler/state capture ownership, recovery and release races before changing lock scope; then compare same-quality fixed jobs'},ensure_ascii=False,indent=2)+'\n')
