"""External Python stdio acceptance; private expected outputs never enter the sandbox."""
from pathlib import Path
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile

from .harness import ActionHarness
from .schema import GoalState


def validate_stdio_cases(cases):
    if not isinstance(cases, dict) or cases.get('call_type') != 'std' or cases.get('fn_name') is not None:
        raise ValueError('only standard input/output cases are supported')
    inputs, outputs = cases.get('inputs'), cases.get('outputs')
    if (not isinstance(inputs, list) or not isinstance(outputs, list) or not inputs
            or len(inputs) != len(outputs)
            or any(not isinstance(v, str) for v in inputs + outputs)):
        raise ValueError('nonempty equal-length string input/output arrays required')
    return tuple(zip(inputs, outputs))


def verify_python_submission(workspace, cases, *, timeout_seconds=3., max_output_bytes=1048576):
    pairs = validate_stdio_cases(cases)
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or type(max_output_bytes) is not int or max_output_bytes <= 0:
        raise ValueError('positive finite resource limits required')
    root = Path(workspace).resolve(strict=True)
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('submission symlinks are not accepted')
    if not (root / 'solution.py').is_file():
        return {'passed': False, 'termination': 'missing_submission', 'cases': []}
    harness = ActionHarness()
    if not harness._bubblewrap or not shutil.which('prlimit'):
        raise RuntimeError('isolated stdio verifier requires bubblewrap and prlimit')
    records = []
    for index, (stdin, expected) in enumerate(pairs):
        with tempfile.TemporaryDirectory(prefix='rwkv-stdio-') as temporary:
            base = Path(temporary)
            snapshot = base / 'workspace'
            shutil.copytree(root, snapshot)
            goal = GoalState.create(request='External stdio verification', workspace_root=str(snapshot), constraints=[])
            argv, sandbox_path = harness._bubblewrap_command(goal, snapshot, [sys.executable, '-B', 'solution.py'])
            # Limits apply through exec to the sandbox and its children. Expected output
            # remains in this parent; only this test's stdin crosses the boundary.
            argv = [shutil.which('prlimit'), '--fsize='+str(max_output_bytes), '--as=1073741824',
                    '--cpu='+str(max(1, math.ceil(timeout_seconds))), '--nofile=128', '--', *argv]
            with (base/'stdout').open('w+b') as stdout, (base/'stderr').open('w+b') as stderr:
                process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                    env={'PATH': sandbox_path, 'LANG': 'C.UTF-8', 'PYTHONHASHSEED': '0'}, start_new_session=True)
                reason = 'exited'
                try:
                    process.communicate(stdin.encode(), timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    reason = 'timeout'
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                finally:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                stdout.seek(0); stderr.seek(0)
                out = stdout.read(max_output_bytes).decode('utf-8', errors='replace')
                err = stderr.read(max_output_bytes).decode('utf-8', errors='replace')
            passed = reason == 'exited' and process.returncode == 0 and out.rstrip() == expected.rstrip()
            records.append({'index': index, 'passed': passed, 'termination': reason,
                            'exit_code': process.returncode, 'stdout': out, 'stderr': err})
    return {'passed': all(r['passed'] for r in records), 'termination': 'checked', 'cases': records}
