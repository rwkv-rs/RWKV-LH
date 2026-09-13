"""Freeze current production role data or execute an explicitly registered Native StateTune run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal

from rwkv_lh.statetune_data import freeze_dataset, sealed
from rwkv_lh.statetune_training import run_training
from rwkv_lh.statetune_evaluation import run_evaluation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "train", "evaluate"))
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = {"path": str(args.registration.resolve()), "sha256": args.registration_sha256}
    if args.command == "freeze":
        result = freeze_dataset(sealed(reference), registration_reference=reference, output=args.output)
    else:
        def interrupted(signum, frame):
            raise KeyboardInterrupt(f"received signal {signum}")
        signal.signal(signal.SIGTERM, interrupted)
        run = run_training if args.command == "train" else run_evaluation
        result = run(reference, args.output, source_root=Path(__file__).resolve().parents[1])
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result.get("status") in (None, "candidate", "evaluated") else 2


if __name__ == "__main__":
    raise SystemExit(main())
