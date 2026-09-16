"""Consume reviewed frozen batches continuously; idle means awaiting tasks, not inference.

Each ready/*.json binds an inventory and reviewed source families. This process
does not reconstruct repositories, relabel failures, invoke a teacher, or train.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.collection_campaign import Campaign, digest
from rwkv_lh.runtime.settings import load_local_env
from scripts.run_collection_queue import validate_inventory, verify_item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--replicas', type=Path, required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--target-tasks', type=int, required=True)
    parser.add_argument('--concurrency', type=int, default=4)
    parser.add_argument('--max-hours', type=float, default=36)
    args = parser.parse_args()
    if args.target_tasks < 1 or args.concurrency < 1 or not 0 < args.max_hours <= 72:
        parser.error('positive task/concurrency limits and finite duration <=72 hours required')
    root = args.root.resolve();root.mkdir(parents=True, exist_ok=True)
    (root/'ready').mkdir(exist_ok=True)
    load_local_env(args.env_file)
    runner = Path(__file__).with_name('run_collection_queue.py')
    code_root = runner.parent.parent
    identity = {'target_tasks':args.target_tasks, 'concurrency':args.concurrency,
                'max_hours':args.max_hours, 'replicas_sha256':digest(args.replicas),
                'source': {str(p.relative_to(code_root)):digest(p)
                    for folder in ['rwkv_lh','scripts'] for p in (code_root/folder).rglob('*.py')}}
    def status(phase, **fields):
        temp = root/'STATUS.pending'
        temp.write_text(json.dumps({'phase':phase, 'time':time.time(), 'target_tasks':args.target_tasks,
            'teacher_calls':0, 'training_rows':0, **fields},ensure_ascii=False,indent=2))
        os.replace(temp, root/'STATUS.json')
    with (root/'campaign.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with Campaign(root/'campaign.sqlite3', identity) as campaign:
            campaign.db.execute('CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY,value TEXT)')
            campaign.db.execute("INSERT OR IGNORE INTO operations VALUES ('deadline',?)",(str(time.time()+args.max_hours*3600),))
            deadline = float(campaign.db.execute("SELECT value FROM operations WHERE key='deadline'").fetchone()[0])
            try:
                while time.time() < deadline:
                    for manifest in sorted((root/'ready').glob('*.json')):
                        data = json.loads(manifest.read_text())
                        if digest(data['inventory']) != data['inventory_sha256']:
                            raise ValueError('unfrozen batch inventory')
                        items = [json.loads(line) for line in Path(data['inventory']).read_text().splitlines()]
                        known = campaign.db.execute('SELECT 1 FROM batches WHERE id=?',(data['batch_id'],)).fetchone()
                        if not known:
                            count = campaign.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
                            if count + len(items) > args.target_tasks:
                                raise ValueError('new batch exceeds registered task budget')
                            for item in items:verify_item(item,require_conversion=True)
                            old_items = []
                            for raw, in campaign.db.execute('SELECT payload FROM batches'):
                                previous = json.loads(raw)
                                if digest(previous['inventory']) != previous['inventory_sha256']:
                                    raise ValueError('previous inventory changed')
                                old_items.extend(json.loads(l) for l in Path(previous['inventory']).read_text().splitlines())
                            class Inventory:
                                def items(self):return iter(old_items+items)
                            validate_inventory(Inventory())
                        campaign.admit(manifest)
                    count = campaign.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
                    batch = campaign.next_batch()
                    if batch is None:
                        if count == args.target_tasks:
                            status('collection_recorded', recorded_tasks=count, batch_counts=campaign.counts())
                            return 0
                        status('waiting_for_bound_tasks', admitted_tasks=count, batch_counts=campaign.counts())
                        time.sleep(min(10, max(0,deadline-time.time())))
                        continue
                    name = batch['batch_id']; work = root/'batches'/name;work.mkdir(parents=True,exist_ok=True)
                    queue = work/'queue.sqlite3'
                    cmd = [sys.executable,str(runner),'--queue',str(queue)]
                    if not queue.exists():
                        subprocess.run(cmd+['--inventory',batch['inventory']],check=True)
                    key = 'hours-'+name
                    campaign.db.execute('INSERT OR IGNORE INTO operations VALUES (?,?)', (key,str(max(.001,(deadline-time.time())/3600))))
                    hours = campaign.db.execute('SELECT value FROM operations WHERE key=?',(key,)).fetchone()[0]
                    status('collecting', active_batch=name, admitted_tasks=count, batch_counts=campaign.counts())
                    with (work/'run.log').open('a') as log:
                        process = subprocess.run(cmd+['--run','--replicas',str(args.replicas),
                            '--concurrency',str(args.concurrency),'--max-hours',hours],stdout=log,stderr=subprocess.STDOUT)
                    if process.returncode:
                        raise RuntimeError(f'batch {name} stopped with exit {process.returncode}; inspect its queue and log')
                    with sqlite3.connect(queue) as db:
                        counts = dict(db.execute('SELECT status,COUNT(*) FROM tasks GROUP BY status'))
                        results = [json.loads(row[0]) for row in db.execute('SELECT result FROM tasks WHERE result IS NOT NULL')]
                    if any(r.get('trace_complete') is not True for r in results):
                        raise RuntimeError('incomplete execution trace; campaign halted before next batch')
                    campaign.finish(name, {'reason':'exhausted','counts':counts})
                status('campaign_deadline', batch_counts=campaign.counts())
                return 2
            except Exception as exc:
                status('stopped_review_required', error={'type':type(exc).__name__,'message':str(exc)}, batch_counts=campaign.counts())
                raise


if __name__ == '__main__':
    raise SystemExit(main())
