"""Run document QA or code inspection with isolated RWKV State and raw evidence."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.read_only_agent import ReadOnlyJob, run_read_only_jobs
from rwkv_lh.runtime.settings import get_runtime_settings, load_local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=Path, required=True, help='JSON list of independent ReadOnlyJob objects')
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--base-url')
    parser.add_argument('--model')
    parser.add_argument('--model-sha256')
    args = parser.parse_args()
    load_local_env(Path(__file__).resolve().parents[1] / '.env.local')
    settings = get_runtime_settings()
    overrides = {name: getattr(args, name) for name in ('base_url', 'model', 'model_sha256') if getattr(args, name)}
    settings = replace(settings, **overrides, return_token_ids=True, state_transport='native_required',
                       state_profile_id='zero', state_profile_sha256='0'*64, tool_disclosure_mode='full')
    jobs = [ReadOnlyJob(**row) for row in json.loads(args.jobs.read_text())]
    results = run_read_only_jobs(jobs, settings=settings, concurrency=args.concurrency)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(row['termination'] == 'submitted' for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
