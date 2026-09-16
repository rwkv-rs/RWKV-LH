"""Seal a completed campaign's original traces before explicit State retirement.

Run with --apply only when original native-handle resumption is no longer needed.
No model calls, grading changes, training rows, or raw blob deletion are performed.
"""
import argparse
import fcntl
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rwkv_lh.collection_retirement import seal_run, release_sealed_runs, tree, digest
from rwkv_lh.collection_queue import _json
from rwkv_lh.runtime.settings import load_local_env, get_runtime_settings
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--expected-tasks',type=int,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    lock=(args.campaign/'campaign.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
    status=json.loads((args.campaign/'STATUS.json').read_text())
    if status['phase'] not in {'waiting_for_bound_tasks','collection_recorded','campaign_deadline'}:
        raise ValueError('campaign must have finished dispatch before retirement')
    rows=[]
    for path in sorted((args.campaign/'batches').glob('*/queue.sqlite3')):
        with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            if db.execute("select count(*) from tasks where status!='recorded'").fetchone()[0]:
                raise ValueError('unfinished task prevents retirement')
            rows.extend(dict(row) for row in db.execute('select * from tasks'))
    if len(rows)!=args.expected_tasks:
        raise ValueError('task inventory count differs')
    # Prepared receipts bind the actual execution endpoint, never current defaults.
    args.evidence.mkdir(parents=True,exist_ok=True)
    prepared=[]
    for row in rows:
        item=json.loads(row['payload'])
        result=json.loads(row['result'])
        output=Path(item['job']['output_dir'])
        receipt=json.loads((output/'COLLECTION_RECEIPT.json').read_text())
        if (receipt['result']!=result or receipt['source_id']!=item['source_id']
                or receipt['payload_sha256']!=hashlib.sha256(_json(item).encode()).hexdigest()
                or receipt['result_sha256']!=hashlib.sha256(_json(result).encode()).hexdigest()
                or result.get('trace_complete') is not True):
            raise ValueError('incomplete or changed receipt')
        root=output/'execution' if item['job']['tool_scope']=='coding' else output
        state=json.loads((root/'state_snapshot.json').read_text())
        models={cp['native_state_metadata']['model_sha256'] for cp in state['model_states'].values() if cp.get('native_state_ref')}
        if len(models)!=1:
            raise ValueError('missing or mixed State model identity')
        sealed=args.evidence/result['id']
        if not sealed.exists():
            seal_run(root,sealed,models.pop())
        else:
            manifest=json.loads((sealed/'MANIFEST.json').read_text())
            if manifest['source_files']!=tree(root) or manifest['boundaries_sha256']!=digest(sealed/'boundaries.jsonl'):
                raise ValueError('sealed evidence changed')
        prepared.append((root,sealed,result['collection_service']))
        print(json.dumps({'sealed':len(prepared),'total':len(rows)}),flush=True)
    (args.evidence/'AUDIT.json').write_text(json.dumps({'tasks':len(rows),'all_sealed':True,'apply':args.apply},indent=2)+'\n')
    if not args.apply:return
    load_local_env(args.env_file)
    settings=get_runtime_settings()
    groups={}
    for root,sealed,service in prepared:
        key=json.dumps(service,sort_keys=True)
        groups.setdefault(key,[]).append((root,sealed))
    for key,runs in groups.items():
        service=json.loads(key)
        client=OpenAICompatibleRWKVClient(replace(settings,base_url=service['base_url']))
        try:release_sealed_runs(runs,client,expected_service=service['identity'])
        finally:client.close()
        print(json.dumps({'retired_tasks':len(runs),'service':service['base_url']}),flush=True)


if __name__=='__main__':main()
