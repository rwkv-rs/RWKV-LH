"""Execute a coding task in a copied workspace; submission is not acceptance."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.coding_agent import CodingJob, run_coding_job
from rwkv_lh.runtime.settings import get_runtime_settings, load_local_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--request', required=True)
    parser.add_argument('--task-id', default='coding-task')
    parser.add_argument('--max-calls', type=int, default=12)
    parser.add_argument('--max-seconds', type=float, default=600)
    parser.add_argument('--base-url')
    parser.add_argument('--model')
    parser.add_argument('--model-sha256')
    args = parser.parse_args()
    load_local_env(Path(__file__).resolve().parents[1] / '.env.local')
    settings = get_runtime_settings()
    overrides = {name: getattr(args, name) for name in ('base_url', 'model', 'model_sha256') if getattr(args, name)}
    settings = replace(settings, **overrides, return_token_ids=True, state_transport='native_required',
                       state_profile_id='zero', state_profile_sha256='0'*64, tool_disclosure_mode='full')
    job = CodingJob(**{name: getattr(args, name) for name in CodingJob.__dataclass_fields__})
    result = run_coding_job(job, settings=settings)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['termination'] == 'submitted' else 1


if __name__ == '__main__':
    raise SystemExit(main())
