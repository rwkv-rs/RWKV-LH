"""Run a sealed trace-to-dataset workflow, with resumable stages and no training."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.data_pipeline import execute, consume_inbox
from rwkv_lh.offline_teacher_api import DeepSeekTeacher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--registration', type=Path)
    mode.add_argument('--inbox', type=Path)
    parser.add_argument('--max-batches', type=int)
    parser.add_argument('--max-jobs', type=int)
    parser.add_argument('--max-seconds', type=float)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--api-config', type=Path)
    args = parser.parse_args()
    if args.inbox:
        if not args.api_config or any(v is None for v in (args.max_batches, args.max_jobs, args.max_seconds)):
            parser.error('inbox requires API config and explicit batch/job/time budgets')
        result = consume_inbox(args.inbox, args.output,
            teacher=DeepSeekTeacher(**json.loads(args.api_config.read_text())),
            max_batches=args.max_batches, max_jobs=args.max_jobs, max_seconds=args.max_seconds)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['phase'] == 'registered_batches_completed' else 2
    # Complete source/contract validation before loading the paid provider.
    result = execute(args.registration, args.output)
    if args.api_config:
        teacher = DeepSeekTeacher(**json.loads(args.api_config.read_text()))
        result = execute(args.registration, args.output, teacher=teacher)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['phase'] in {'prepared_no_api_calls', 'dataset_admitted',
                                   'exported_pending_freeze_registration'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
