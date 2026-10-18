"""Run one sealed StateTune registration; this command never grants training authorization."""
import argparse
from pathlib import Path

from rwkv_lh.statetune_training import run_training


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--registration-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run_training({'path': str(args.registration), 'sha256': args.registration_sha256},
                          args.output, source_root=Path(__file__).resolve().parents[1])
    return 0 if result['status'] == 'candidate' else 1


if __name__ == '__main__':
    raise SystemExit(main())
