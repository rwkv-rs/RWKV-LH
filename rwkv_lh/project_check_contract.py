"""Public check execution semantics and conservative, non-executing syntax probes.

This does not prove assertions cover a requirement, that fixtures exist, or that
an arbitrary shell command is executable. Those remain explicit Planner review
and actual verification responsibilities. Never execute a candidate check here.
"""
from functools import lru_cache
import os
from pathlib import PurePath
import re
import shutil
import subprocess

CHECK_EXECUTION = {
    'independent_workspace_per_check': True,
    'writes_persist_between_checks': False,
    'fixtures': 'Each check creates its own temporary inputs in the same invocation.',
    'implementation': 'Checks run after implementation; promised project artifacts need not be created by the check.',
    'assertions': 'Assert observable behavior required by the user, including wrong-result failures; file existence, keywords, syntax and empty test suites alone do not establish behavior.',
    'web_behavior': 'Web and full-stack interaction checks use real Chromium through Playwright, with their own server lifecycle and temporary browser data; pseudo-DOM and keyword checks are not browser evidence.',
    'browser_runtime': 'The prepared benchmark-web environment supplies Python playwright.sync_api and a read-only Chromium runtime inside the public command sandbox. Use python with playwright.sync_api for browser checks. A global Node playwright module is not provided; do not assume require("playwright") works. No whole home or repository is mounted for browsers.',
    'limits': 'Syntax preflight covers recognized literal forms only, never general correctness or requirement coverage. Actual checks run in isolated copies and retain command, exit status and output.',
}


def validate_literal_syntax(argv, *, check_id):
    try:
        _literal_syntax(tuple(argv))
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f'checks[{check_id}].argv: literal syntax error: {exc}') from exc


def _parse_with(executable, arguments, source):
    binary = shutil.which(executable)
    if binary is None:
        # Missing target runtimes are not evidence that source syntax is wrong.
        # The registered execution environment and real verification must check them.
        return
    # In particular NODE_OPTIONS/BASH_ENV must not execute startup code during parsing.
    env = {'PATH': os.defpath, 'LANG': 'C', 'LC_ALL': 'C'}
    try:
        result = subprocess.run([binary, *arguments], input=source, text=True,
                                capture_output=True, timeout=5, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'{executable} syntax preflight unavailable: {exc}') from exc
    if result.returncode not in ((0, 1) if executable == 'grep' else (0,)):
        raise ValueError(result.stderr or result.stdout or f'{executable} parser exited {result.returncode}')


@lru_cache(maxsize=256)
def _literal_syntax(argv):
    name = PurePath(argv[0]).name
    if re.fullmatch(r'python(?:3(?:\.\d+)?)?', name):
        # Stop at the script, -m, or --: a later -c may be a program argument.
        for index, argument in enumerate(argv[1:], 1):
            if argument == '-c':
                if index + 1 < len(argv):
                    compile(argv[index + 1], '<public-check>', 'exec')
                return
            if argument in ('-m', '--') or not argument.startswith('-'):
                return
    elif name in ('node', 'nodejs'):
        flags, source = [], None
        index = 1
        while index < len(argv):
            argument = argv[index]
            if argument in ('--input-type=module', '--input-type=commonjs'):
                flags.append(argument)
            elif argument in ('-e', '--eval', '-p', '--print') and index + 1 < len(argv) and source is None:
                index += 1
                source = argv[index]
            else:
                # Unknown loaders/grammar flags cannot safely be approximated.
                return
            index += 1
        if source is not None:
            _parse_with('node', [*flags, '--check'], source)
    elif name == 'grep':
        # Only unambiguous simple grep forms. No file reads, no shell evaluation.
        flags, patterns = [], []
        index = 1
        while index < len(argv):
            arg = argv[index]
            if arg in ('-E', '-G', '-P', '-i'):
                flags.append(arg)
            elif arg in ('-e', '--regexp') and index + 1 < len(argv):
                index += 1
                patterns.append(argv[index])
            elif arg in ('-q', '-n', '-s', '-v', '-x', '-o', '-c', '-l', '-L', '-h', '-H'):
                pass
            elif not arg.startswith('-'):
                if not patterns:
                    patterns.append(arg)
                break
            else:
                return
            index += 1
        if patterns:
            _parse_with('grep', [*flags, *[v for pattern in patterns for v in ('-e', pattern)]], '')
    elif name in ('bash', 'sh') and len(argv) > 2 and argv[1] == '-c':
        _parse_with(name, ['-n'], argv[2])
