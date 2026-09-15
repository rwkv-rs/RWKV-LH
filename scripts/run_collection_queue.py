"""Run a frozen, admitted inventory through the direct production Agent.

Only direct jobs are accepted. Interrupted in-flight rows require reconciliation;
this entry point never retries them automatically or assigns acceptance labels.
"""
import argparse
from dataclasses import asdict
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.workspace_snapshot import tree_identity
from rwkv_lh.collection_queue import CollectionQueue
from rwkv_lh.agent_batch import run_agent_jobs, validate_agent_jobs
from rwkv_lh.coding_agent import CodingJob
from rwkv_lh.read_only_agent import ReadOnlyJob
from rwkv_lh.runtime.settings import direct_agent_settings, get_runtime_settings


def make_job(row):
    row = dict(row)
    scope = row.pop('tool_scope')
    allowed = {'task_id', 'request', 'workspace', 'output_dir', 'max_calls', 'max_seconds'}
    if set(row) != allowed:
        raise ValueError('explicit direct job fields and budgets required; assistance is not supported')
    if scope == 'coding':
        row['source_workspace'] = row.pop('workspace')
        return CodingJob(**row)
    if scope not in ('files', 'inspect'):
        raise ValueError('unsupported tool scope')
    return ReadOnlyJob(**row, tool_scope=scope)


def verify_item(item):
    """Check bytes, not just the spelling of the registered digests."""
    job = make_job(item['job'])
    workspace = Path(item['job']['workspace']).resolve(strict=True)
    for field, digest in (('source_path', 'source_sha256'),
                          ('acceptance_path', 'acceptance_sha256')):
        path = Path(item[field]).resolve(strict=True)
        if path == workspace or workspace in path.parents:
            raise ValueError('private source/reference must stay outside Agent workspace')
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != item[digest]:
            raise ValueError(f'{field} changed after freeze')
    tree = tree_identity(workspace, allow_links=False)
    actual = hashlib.sha256(json.dumps(tree, sort_keys=True, ensure_ascii=False,
                                      allow_nan=False).encode()).hexdigest()
    if actual != item['environment_sha256']:
        raise ValueError('workspace changed after freeze')
    validate_agent_jobs([job])
    return job


def validate_inventory(queue):
    """Linear ancestor checks cover cross-batch workspace/output collisions."""
    rows = [json.loads(row[0]) for row in queue.db.execute('SELECT payload FROM tasks')]
    ids = [item['job']['task_id'] for item in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate task IDs across inventory')
    sources = {Path(item['job']['workspace']).resolve() for item in rows}
    outputs = [Path(item['job']['output_dir']).resolve() for item in rows]
    output_set = set(outputs)
    if len(outputs) != len(output_set):
        raise ValueError('duplicate output directories')
    for output in outputs:
        if output in sources or any(p in output_set or p in sources for p in output.parents):
            raise ValueError('overlapping inventory paths')
    if any(any(p in output_set for p in source.parents) for source in sources):
        raise ValueError('output contains source workspace')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, help='admit frozen JSONL; does not execute')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--min-free-gib', type=int, default=20)
    args = parser.parse_args()
    if args.concurrency < 1 or args.min_free_gib < 1 or (args.run and args.inventory):
        parser.error('positive limits required; admission and execution are separate')
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    with args.queue.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with CollectionQueue(args.queue) as queue:
            if args.inventory:
                queue.db.execute('BEGIN IMMEDIATE')
                try:
                    with args.inventory.open() as inventory:
                        for line in inventory:
                            item = json.loads(line)
                            verify_item(item)
                            queue.admit(item)
                    validate_inventory(queue)
                    queue.db.execute('COMMIT')
                except BaseException:
                    queue.db.execute('ROLLBACK')
                    raise
            if args.run:
                validate_inventory(queue)
                settings = direct_agent_settings(get_runtime_settings())
                if settings.state_profile_id != 'zero' or settings.state_profile_sha256 != '0' * 64:
                    raise ValueError('this collection campaign requires zero State')
                identity = asdict(settings)
                for field in ('api_key', 'cf_access_client_id', 'cf_access_client_secret'):
                    identity.pop(field, None)
                frozen = args.queue.with_suffix('.runtime.json')
                value = json.dumps(identity, sort_keys=True, indent=2)
                if frozen.exists():
                    if frozen.read_text() != value:
                        raise ValueError('runtime settings changed; refusing mixed campaign')
                else:
                    with frozen.open('x') as output:
                        output.write(value)
                while True:
                    if shutil.disk_usage(args.queue.parent).free < args.min_free_gib * 1024**3:
                        raise RuntimeError('disk reserve reached; pending tasks preserved')
                    batch = []
                    for _ in range(args.concurrency):
                        item = queue.claim()
                        if item is None:
                            break
                        batch.append(item)
                    if not batch:
                        break
                    jobs = [verify_item(item) for item in batch]
                    results = run_agent_jobs(jobs, settings=settings, concurrency=args.concurrency)
                    for item, result in zip(batch, results, strict=True):
                        queue.finish(item['source_id'], result)
                    print(json.dumps(queue.counts()), flush=True)
            print(json.dumps(queue.counts()), flush=True)


if __name__ == '__main__':
    main()
