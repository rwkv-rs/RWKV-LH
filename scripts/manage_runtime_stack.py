"""One-command deployment and lifecycle entry point for the RWKV-LH stack."""

from __future__ import annotations

import argparse
import json
from typing import Any

from rwkv_lh.runtime.stack import RuntimeStackManager


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare", help="build the pinned reduced Router engine")
    deploy = subparsers.add_parser("deploy", help="prepare and start the stack")
    deploy.add_argument("--web", action="store_true")
    deploy.add_argument("--worker", action="store_true")
    deploy.add_argument("--timeout", type=float, default=180.0)
    up = subparsers.add_parser("up", help="start and attest the stack")
    up.add_argument("--web", action="store_true")
    up.add_argument("--worker", action="store_true")
    up.add_argument("--timeout", type=float, default=180.0)
    subparsers.add_parser("down", help="stop only manager-owned processes")
    status = subparsers.add_parser("status", help="show owned processes and health")
    status.add_argument("--no-probe", action="store_true")
    args = parser.parse_args()
    manager = RuntimeStackManager()
    if args.command == "prepare":
        _print(manager.prepare())
    elif args.command == "deploy":
        prepared = manager.prepare()
        started = manager.up(
            web=args.web,
            proactive_worker=args.worker,
            timeout_seconds=args.timeout,
        )
        _print({"prepared": prepared, "started": started})
    elif args.command == "up":
        _print(
            manager.up(
                web=args.web,
                proactive_worker=args.worker,
                timeout_seconds=args.timeout,
            )
        )
    elif args.command == "down":
        _print(manager.down())
    elif args.command == "status":
        _print(manager.status(probe=not args.no_probe))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
