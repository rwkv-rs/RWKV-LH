"""Audit existing usage or a frozen atomic correction registration offline."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.usage_accounting import audit_run_usage
from rwkv_lh.coding_corrections import validate_coding_correction
from rwkv_lh.correction_review import build_review_packet, validate_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    usage = modes.add_parser('usage')
    usage.add_argument('--run', type=Path, required=True)
    usage.add_argument('--rates', type=Path, help='JSON with currency and model rates; omit for unknown cost')
    correction = modes.add_parser('correction')
    correction.add_argument('--registration', type=Path, required=True,
                            help='Frozen source, candidate, external checks and review references; no dataset is created')
    packet = modes.add_parser('review-packet', help='Package unchanged original input and candidate for offline review')
    packet.add_argument('--input', type=Path, required=True)
    packet.add_argument('--candidate', type=Path, required=True)
    review = modes.add_parser('review-check', help='Check review anchors and consistency, not semantic truth or admission')
    review.add_argument('--packet', type=Path, required=True)
    review.add_argument('--judgment', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'usage':
        rates = json.loads(args.rates.read_text()) if args.rates else {}
        result = audit_run_usage(args.run, rates=rates.get('rates'), currency=rates.get('currency'))
    elif args.mode == 'correction':
        registration = json.loads(args.registration.read_text())
        result = validate_coding_correction(**registration)
    elif args.mode == 'review-packet':
        result = build_review_packet(actual_rwkv_input=args.input.read_text(), candidate=args.candidate.read_text())
    else:
        result = validate_review(json.loads(args.packet.read_text()), json.loads(args.judgment.read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.mode == 'correction':
        return 0 if result['status'] == 'validated_candidate' else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
