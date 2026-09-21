"""Prepare, generate/validate, or report offline DeepSeek correction jobs."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh import trace_correction_pipeline as pipeline
from rwkv_lh.offline_teacher_api import DeepSeekTeacher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'run', 'batch', 'export', 'freeze', 'report'])
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--packet-sha256')
    parser.add_argument('--api-config', type=Path)
    args = parser.parse_args()
    if args.operation == 'prepare':
        if args.output is None:
            parser.error('prepare requires --output')
        result = pipeline.prepare(json.loads(args.input.read_text()), args.output)
    elif args.operation == 'batch':
        if not args.api_config:
            parser.error('batch requires --api-config')
        result = pipeline.run_batch(json.loads(args.input.read_text()),
            teacher=DeepSeekTeacher(**json.loads(args.api_config.read_text())))
    elif args.operation == 'export':
        if not args.output:
            parser.error('export requires --output')
        result = pipeline.export_candidates(json.loads(args.input.read_text()), args.output)
    elif args.operation == 'freeze':
        if not args.output:
            parser.error('freeze requires --output')
        from rwkv_lh.direct_trace_data import freeze_direct_dataset
        result = freeze_direct_dataset(json.loads(args.input.read_text()),
            registration_reference={'path': str(args.input.resolve()), 'sha256': pipeline.file_sha(args.input)},
            output=args.output)
    elif args.operation == 'run':
        if not args.packet_sha256 or not args.api_config:
            parser.error('run requires --packet-sha256 and --api-config')
        config = json.loads(args.api_config.read_text())
        result = pipeline.run(args.input, expected_packet_sha256=args.packet_sha256,
                              teacher=DeepSeekTeacher(**config))
    else:
        result = pipeline.summarize(json.loads(args.input.read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
