#!/usr/bin/env python3
"""Compare paired current-architecture RWKV Agent traces."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rwkv_lh.trace_comparator_v2 import compare_runs  # noqa: E402


def _run(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("--run must be NAME=/absolute/run/directory")
    path = Path(raw_path)
    if not path.is_absolute():
        raise argparse.ArgumentTypeError("trace run directory must be absolute")
    return name.strip(), path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, type=_run)
    parser.add_argument("--oracle", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"trace comparison output already exists: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    value = compare_runs(runs=args.run, oracle_path=args.oracle)
    pending = output.with_name(output.name + f".pending.{os.getpid()}")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, output)
    print(
        json.dumps(
            {
                "output": str(output),
                "run_count": value["run_count"],
                "paired_task_count": value["paired_task_count"],
                "semantic_attribution_enabled": value[
                    "semantic_attribution_enabled"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
