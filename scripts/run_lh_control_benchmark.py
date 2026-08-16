"""Run the architecture-level unified lane regression suite."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TESTS = (
    "tests/test_model_session.py",
    "tests/test_chunks.py",
    "tests/test_unified_controller.py",
    "tests/test_long_horizon_state.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the one-G1i, ModelSession, chunk and evidence architecture"
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    command = [sys.executable, "-m", "pytest", "-s", "-q", *DEFAULT_TESTS]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    report = {
        "schema_version": "rwkv-lh.unified-control-regression.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "tests": list(DEFAULT_TESTS),
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.output is not None:
        output = arguments.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
