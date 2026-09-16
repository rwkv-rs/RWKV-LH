"""Run a frozen, admitted inventory through the direct production Agent.

Only direct jobs are accepted. Interrupted in-flight rows require reconciliation;
this entry point never retries them automatically or assigns acceptance labels.
"""
import argparse
from dataclasses import asdict, replace
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.workspace_snapshot import tree_identity
from rwkv_lh.collection_queue import CollectionQueue
from rwkv_lh.agent_batch import validate_agent_jobs
from rwkv_lh.collection_execution import dispatch, service_fingerprint
from rwkv_lh.inference.uploaded_sources import source_inventory
from rwkv_lh.collection_acceptance import load_contract
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


def verify_item(item, *, require_conversion=False):
    """Check bytes, not just the spelling of the registered digests."""
    if require_conversion:
        from rwkv_lh.collection_conversion import verify_conversion
        verify_conversion(item)
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
    load_contract(item)
    tree = tree_identity(workspace, allow_links=False)
    actual = hashlib.sha256(json.dumps(tree, sort_keys=True, ensure_ascii=False,
                                      allow_nan=False).encode()).hexdigest()
    if actual != item['environment_sha256']:
        raise ValueError('workspace changed after freeze')
    validate_agent_jobs([job])
    return job


def validate_inventory(queue):
    """Linear ancestor checks cover cross-batch workspace/output collisions."""
    rows = list(queue.items())
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
    private_paths = {Path(item[field]).resolve() for item in rows
                     for field in ('source_path', 'acceptance_path', 'conversion_path') if field in item}
    for private in private_paths:
        if private in sources or any(parent in sources for parent in private.parents):
            raise ValueError('private evidence is visible in another task workspace')
        if private in output_set or any(parent in output_set for parent in private.parents):
            raise ValueError('task output overlaps private evidence')


def collection_replicas(settings, path, concurrency):
    """Bind independent identical-model endpoints, never route individual steps."""
    if path is None:
        return [(settings, service_fingerprint(settings))]
    rows = json.loads(path.read_text())
    if not isinstance(rows, list) or not rows or len(rows) > concurrency:
        raise ValueError('replica list requires at least one worker per endpoint')
    services, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'base_url'}:
            raise ValueError('replicas specify base_url only; model and sampling stay identical')
        url = row['base_url']
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('invalid replica URL')
        url = url.rstrip('/')
        if url in seen:
            raise ValueError('duplicate replica endpoint')
        seen.add(url)
        replica = replace(settings, base_url=url)
        identity = service_fingerprint(replica)
        if services and identity != services[0][1]:
            raise ValueError('replica model/source identity differs')
        services.append((replica, identity))
    return services


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue', type=Path, required=True)
    parser.add_argument('--engineering-inventory', action='store_true', help='explicit legacy engineering smoke only; never count as formal collection')
    parser.add_argument('--inventory', type=Path, help='admit frozen JSONL; does not execute')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--acknowledge-recovery', action='store_true', help='explicitly reset the persisted service failure circuit before resuming')
    parser.add_argument('--status', action='store_true', help='read-only progress, does not acquire the runner lock')
    parser.add_argument('--max-hours', type=float, default=36)
    parser.add_argument('--failure-limit', type=int, default=3)
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--replicas', type=Path, help='JSON list of independent base_url endpoints for the same frozen model')
    parser.add_argument('--min-free-gib', type=int, default=20)
    args = parser.parse_args()
    import math
    if (args.concurrency < 1 or args.min_free_gib < 1 or args.failure_limit < 1
            or not math.isfinite(args.max_hours) or args.max_hours <= 0
            or sum(bool(x) for x in (args.run, args.inventory, args.status)) > 1):
        parser.error('positive limits required; admission and execution are separate')
    if args.acknowledge_recovery and not args.run:
        parser.error('--acknowledge-recovery requires --run')
    if args.status:
        import sqlite3
        with sqlite3.connect(args.queue.resolve().as_uri() + '?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status'))
            results = [json.loads(row[0]) for row in db.execute('SELECT result FROM tasks WHERE result IS NOT NULL')]
            operations = dict(db.execute('SELECT name, value FROM operational')) if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operational'").fetchone() else {}
            print(json.dumps({'counts': counts, 'operation_state': operations,
                'model_started_tasks': sum(isinstance(r.get('generation_started'), int) and r['generation_started'] > 0 for r in results),
                'submitted': sum(r.get('termination') == 'submitted' for r in results),
                'trace_complete': sum(r.get('trace_complete') is True for r in results),
                'acceptance_passed': sum(r.get('acceptance') == 'passed' for r in results)}, ensure_ascii=False))
        return 0
    def verified(item):
        return verify_item(item, require_conversion=not args.engineering_inventory)
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
                            verified(item)
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
                root = Path(__file__).resolve().parents[1]
                source_identity = {'rwkv_lh/' + name: value
                                   for name, value in source_inventory(root/'rwkv_lh').items()}
                for path in (Path(__file__).resolve(), Path(__file__).with_name('audit_collection_sources.py'),
                             root/'pyproject.toml', root/'uv.lock'):
                    source_identity[str(path.relative_to(root))] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
                replicas = collection_replicas(settings, args.replicas, args.concurrency)
                serving = replicas[0][1]
                inventory_identity = hashlib.sha256(json.dumps(list(queue.items()), sort_keys=True,
                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()
                identity.update(source_files=source_identity, inventory_sha256=inventory_identity,
                    concurrency=args.concurrency, max_hours=args.max_hours, failure_limit=args.failure_limit, service_identity=serving, engineering_inventory=args.engineering_inventory)
                if args.replicas:
                    identity['replicas'] = [{'base_url': s.base_url, 'service_identity': i} for s, i in replicas]
                queue.seal(identity)
                queue.db.execute("INSERT OR IGNORE INTO freeze VALUES ('deadline', ?)",
                                 (str(time.time() + args.max_hours * 3600),))
                deadline = float(queue.db.execute("SELECT value FROM freeze WHERE name='deadline'").fetchone()[0])
                def capacity():
                    if shutil.disk_usage(args.queue.parent).free < args.min_free_gib * 1024**3:
                        raise RuntimeError('disk reserve reached')
                if args.acknowledge_recovery:
                    queue.db.execute('CREATE TABLE IF NOT EXISTS operational (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
                    queue.db.execute("INSERT OR REPLACE INTO operational VALUES ('failure_streak', '0')")
                    queue.db.execute("INSERT OR REPLACE INTO operational VALUES ('recovery_acknowledged', ?)", (str(time.time()),))
                result = dispatch(queue, settings=settings, verify=verified,
                    concurrency=args.concurrency, deadline=deadline,
                    failure_limit=args.failure_limit, capacity_check=capacity, service_identity=serving,
                    replicas=replicas)
                print(json.dumps(result), flush=True)
                return 0 if result['reason'] == 'exhausted' and not any(
                    result['counts'].get(key, 0) for key in ('running', 'pending')) else 2

            print(json.dumps(queue.counts()), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
