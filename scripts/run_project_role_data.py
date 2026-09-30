"""Generate current role evidence packets, never automatically train on them."""
import argparse
import json
from rwkv_lh.project_role_data import generate_packets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Production execution ledger directory')
    parser.add_argument('--registration', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(generate_packets(args.source, args.registration, args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
