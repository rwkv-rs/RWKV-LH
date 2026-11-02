"""Freeze pytest acceptance for task definitions, using our private verifier.

No foreign harness or log parser is imported. Collection/setup errors, skipped
targets, missing cases and dependency failures cannot reproduce a known defect.
"""
import base64
import hashlib
from pathlib import Path

from rwkv_lh.project_contracts import scope_path


def pytest_acceptance(*, test_files, deleted_files=(), fail_to_pass, pass_to_pass,
                      python_paths=('.', 'src', '.project-deps'), base=False,
                      timeout=300):
    targets = [*fail_to_pass, *pass_to_pass]
    if not fail_to_pass or len(set(targets)) != len(targets):
        raise ValueError('nonempty distinct target test identifiers required')
    for target in targets:
        if not isinstance(target, str) or not target or target.startswith('-'):
            raise ValueError('invalid pytest target')
        scope_path(target.split('::', 1)[0])
    for name in [*test_files, *deleted_files, *python_paths]:
        scope_path(name)
    if set(test_files) & set(deleted_files):
        raise ValueError('test overlay cannot both write and delete a file')
    if type(timeout) is not int or timeout <= 0:
        raise ValueError('positive test timeout required')
    config = {'files': {p: base64.b64encode(raw).decode() for p, raw in test_files.items()},
              'deleted': list(deleted_files), 'fail_to_pass': list(fail_to_pass),
              'pass_to_pass': list(pass_to_pass), 'python_paths': list(python_paths),
              'base': bool(base), 'timeout': timeout}
    template = Path(__file__).with_name('_pytest_program.py').read_text()
    program = 'CONFIG = '+repr(config)+'\n'+template
    return {'checks': [{'kind': 'project_behavior', 'program': program,
                        'program_sha256': hashlib.sha256(program.encode()).hexdigest(),
                        'timeout': timeout + 15}]}
