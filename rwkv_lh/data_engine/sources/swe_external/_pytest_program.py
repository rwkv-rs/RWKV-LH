"""Standalone private verifier body; CONFIG is prepended by pytest_acceptance.

Executed only inside benchmark_verifier, never imported by the model runtime.
The candidate Python wrapper hides private graders and evidence from test code.
"""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


PYTEST_RUNNER = '''import json,sys,pytest
class Results:
    def __init__(self):
        self.reports=[]
        self.collection_errors=[]
    def pytest_runtest_logreport(self,report):
        self.reports.append(dict(nodeid=report.nodeid,when=report.when,outcome=report.outcome))
    def pytest_collectreport(self,report):
        if report.failed:self.collection_errors.append(report.nodeid)
results=Results()
code=pytest.main(sys.argv[2:],plugins=[results])
with open(sys.argv[1],'w') as stream:
    json.dump(dict(reports=results.reports,collection_errors=results.collection_errors,exit_code=int(code)),stream)
sys.exit(int(code))
'''


def main():
    workspace = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        copy = temporary/'project'
        shutil.copytree(workspace, copy, symlinks=True)
        for relative, encoded in CONFIG['files'].items():
            path = copy/relative
            if not path.resolve().is_relative_to(copy):
                raise ValueError('test overlay escapes candidate tree')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(encoded, validate=True))
        for relative in CONFIG['deleted']:
            path = copy/relative
            if not path.resolve().is_relative_to(copy):
                raise ValueError('test deletion escapes candidate tree')
            path.unlink(missing_ok=True)
        report_path = temporary/'pytest-results.json'
        env = dict(os.environ, PYTHONPATH=':'.join(str(copy/p) for p in CONFIG['python_paths']),
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        targets = CONFIG['fail_to_pass'] + CONFIG['pass_to_pass']
        process = subprocess.run([sys.executable, '-c', PYTEST_RUNNER, str(report_path),
            '--override-ini', 'addopts=', '--color=no', '--tb=short', '-rA', '-p', 'no:cacheprovider',
            *targets], cwd=copy, env=env, timeout=CONFIG['timeout'])
        result = json.loads(report_path.read_text()) if report_path.is_file() else {}
        calls = {}
        invalid = bool(result.get('collection_errors')) or not result
        for report in result.get('reports', []):
            if report['when'] == 'call':
                if report['nodeid'] in calls:
                    invalid = True
                calls[report['nodeid']] = report['outcome']
            elif report['outcome'] != 'passed':
                invalid = True
        invalid = invalid or set(calls) != set(targets)
        stable_passes = all(calls.get(t) == 'passed' for t in CONFIG['pass_to_pass'])
        outcomes = [calls.get(t) for t in CONFIG['fail_to_pass']]
        if CONFIG['base']:
            expected = (process.returncode == 1 and 'failed' in outcomes
                        and all(v in ('passed', 'failed') for v in outcomes))
        else:
            expected = process.returncode == 0 and all(v == 'passed' for v in outcomes)
        passed = not invalid and stable_passes and expected
        result.update(passed=passed, invalid_execution=invalid, base_reproduction=CONFIG['base'],
                      actual_returncode=process.returncode)
        evidence = os.environ.get('RWKV_LH_VERIFIER_EVIDENCE')
        if evidence:
            (Path(evidence)/'pytest-results.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({'passed': passed, 'tests_observed': len(calls),
                          'invalid_execution': invalid, 'base_reproduction': CONFIG['base']}))
        return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
