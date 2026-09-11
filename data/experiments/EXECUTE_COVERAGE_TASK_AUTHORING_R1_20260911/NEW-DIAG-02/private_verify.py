import hashlib, json, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1])
EXPECTED={'tests/test_stock_summary.py': '6fd6c965b0dd89e056af41a0dc193f63508bfd45689697ddbcf19e10e29bc812', 'run_tests.py': '4792778f9a13852e4addc5d5d013c7491d18521baf23b9bc88cd42fbe515074d'}
for path,digest in EXPECTED.items():
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest, "immutable test/runner changed"
assert not (root/'conftest.py').exists() and not (root/'pytest.py').exists() and not (root/'pytest').exists(), "pytest shadowing"
report=(root/'TEST_REPORT.md').read_text()
assert "Exit code: 0\n" in report and "4 passed" in report and "FAILED" not in report, "successful actual pytest report missing"
for path in sorted(root.glob('*.py')):
    assert path.name+": "+hashlib.sha256(path.read_bytes()).hexdigest() in report, "report does not bind current source"

BOUND_EVENTS = None  # trusted-event-binding-v1
assert BOUND_EVENTS is not None, "missing trusted runtime events"
ALLOWED = ['README.md', 'stock_summary.py', 'tests/test_stock_summary.py', 'run_tests.py', 'TEST_REPORT.md']
for path in root.rglob('*'):
    if not path.is_file(): continue
    rel=path.relative_to(root)
    if any(part in ('.pytest_cache','__pycache__') for part in rel.parts): continue
    assert rel.as_posix() in ALLOWED, "unexpected file/test/config: "+str(rel)
commands=[]
for event in BOUND_EVENTS:
    action=(event.get('data') or {}).get('action') or {}
    if action.get('action_type') not in ('check_command','run_command'): continue
    if action.get('arguments',{}).get('argv') != ['python','run_tests.py']: continue
    commands.append(action.get('result') or {})
source_name='stock_summary.py'
initial_sha='fda3c5e999a570a2541f24efbdd7b7b78a099f8df8366bc1c5da91d9279b08d6'
failure_seen=False
matched=False
for result in commands:
    output=result.get('output','')
    if result.get('exit_code')==1 and '1 failed, 3 passed' in output and source_name+': '+initial_sha in output:
        failure_seen=True
    if failure_seen and result.get('success') is True and result.get('exit_code')==0 and output==report:
        matched=True
assert matched, "report is not exact successful command stdout after the real seeded failure"

probe='from stock_summary import stock_totals\nfor entries in ([ ("a",2),("b",7),("a",3),("b",-2)],[("x",4),("x",-4)],[("z",1),("a",2),("z",8)],[]):\n    original=list(entries)\n    expected={}\n    for sku,n in entries: expected[sku]=expected.get(sku,0)+n\n    assert stock_totals(iter(entries)) == list(expected.items())\n    assert entries == original\n'
probe += '\nentries=[(\"b\",2),(\"a\",3),(\"b\",-2)]\noriginal=list(entries)\nassert stock_totals(entries)==[(\"b\",0),(\"a\",3)]\nassert entries==original\n'
r=subprocess.run([sys.executable,'-c',probe],cwd=root,text=True,capture_output=True,timeout=15)
assert r.returncode==0, r.stdout+r.stderr
print('behavior and immutable-report checks passed')
