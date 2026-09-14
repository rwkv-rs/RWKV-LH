"""Audit existing usage or a frozen atomic correction registration offline."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.usage_accounting import audit_run_usage
from rwkv_lh.coding_corrections import validate_coding_correction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    usage = modes.add_parser('usage')
    usage.add_argument('--run', type=Path, required=True)
    usage.add_argument('--rates', type=Path, help='JSON with currency and model rates; omit for unknown cost')
    correction = modes.add_parser('correction')
    correction.add_argument('--registration', type=Path, required=True,
                            help='Frozen source, candidate, external checks and review references; no dataset is created')
    args = parser.parse_args()
    if args.mode == 'usage':
        rates = json.loads(args.rates.read_text()) if args.rates else {}
        result = audit_run_usage(args.run, rates=rates.get('rates'), currency=rates.get('currency'))
    else:
        registration = json.loads(args.registration.read_text())
        result = validate_coding_correction(**registration)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if args.mode == 'usage' or result['status'] == 'validated_candidate' else 1


if __name__ == '__main__':
    raise SystemExit(main())
