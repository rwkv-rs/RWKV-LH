"""External task review CLI; never sends rubric or evidence to an executor."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh import task_review as review


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['freeze', 'capture', 'packet', 'assess', 'aggregate', 'gate'])
    parser.add_argument('--input', type=Path, required=True, help='JSON contract or operation arguments; paths relative to this file')
    parser.add_argument('--output', type=Path, required=True, help='new immutable JSON result')
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.input.read_text())
        root = args.input.resolve().parent
        def path(key):
            return root / value[key]
        def read(key):
            return json.loads(path(key).read_text())
        if args.operation == 'freeze':
            review.freeze_contract(value, args.output)
            return 0
        if args.operation == 'capture':
            options = dict(value)
            options['directory'] = path('directory')
            result = review.capture_diagnostic_run(**options)
        elif args.operation in ('packet', 'assess'):
            contract = review.load_contract(path('contract'))
            run = read('run')
            options = {'evidence_root': path('evidence_root')}
            result = review.assess(contract, run, read('judgment'), **options) if args.operation == 'assess' else review.review_packet(contract, run, **options)
        else:
            # Revalidate source bindings, including original evidence, on every aggregation.
            assessments = []
            for job in value['reviews']:
                c = review.load_contract(root / job['contract'])
                r = json.loads((root / job['run']).read_text())
                j = json.loads((root / job['judgment']).read_text())
                assessments.append(review.assess(c, r, j, evidence_root=root / job['evidence_root']))
            result = review.aggregate(assessments) if args.operation == 'aggregate' else review.quality_gate(
                assessments, task_ids=value['task_ids'], repeats=value['repeats'], arm=value['arm'])
        review.write_once(args.output, result)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f'review rejected: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
