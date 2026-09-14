"""Run independent direct RWKV tasks; raw submissions are not acceptance."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.agent_batch import run_agent_jobs
from rwkv_lh.coding_agent import CodingJob
from rwkv_lh.read_only_agent import ReadOnlyJob
from rwkv_lh.runtime.settings import get_runtime_settings, load_local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=Path, required=True,
                        help='JSON array: task_id, request, workspace, output_dir, tool_scope, budgets')
    parser.add_argument('--concurrency', type=int, default=1)
    args = parser.parse_args()
    jobs = []
    for row in json.loads(args.jobs.read_text()):
        row = dict(row)
        scope = row.pop('tool_scope', 'files')
        if scope == 'coding':
            row['source_workspace'] = row.pop('workspace')
            jobs.append(CodingJob(**row))
        elif scope in ('files', 'inspect'):
            jobs.append(ReadOnlyJob(**row, tool_scope=scope))
        else:
            parser.error('tool_scope must be files, inspect or coding')
    load_local_env(Path(__file__).resolve().parents[1] / '.env.local')
    settings = replace(get_runtime_settings(), return_token_ids=True,
                       state_transport='native_required', state_profile_id='zero',
                       state_profile_sha256='0'*64, tool_disclosure_mode='full')
    results = run_agent_jobs(jobs, settings=settings, concurrency=args.concurrency)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r['termination'] == 'submitted' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
