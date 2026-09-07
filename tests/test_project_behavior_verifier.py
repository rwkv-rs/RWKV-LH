from __future__ import annotations

import hashlib
from pathlib import Path

from rwkv_lh.benchmark_verifier import run_isolated_verifier


def acceptance(program: str, *, browser: bool = False) -> dict:
    return {"checks": [{"kind": "project_behavior", "program": program, "program_sha256": hashlib.sha256(program.encode()).hexdigest(), "browser": browser, "timeout": 45}]}


def test_project_behavior_runs_candidate_cli_and_rejects_wrong_result(tmp_path: Path) -> None:
    workspace = tmp_path / "candidate"
    workspace.mkdir()
    script = workspace / "app.py"
    script.write_text("import sys\nprint(int(sys.argv[1]) * 3)\n")
    program = """import subprocess, sys
from pathlib import Path
candidate = Path(sys.argv[1])
for number in (2, 7, -3):
    actual = subprocess.check_output([sys.executable, str(candidate / 'app.py'), str(number)], text=True)
    assert int(actual) == number * 3
"""
    result = run_isolated_verifier(acceptance(program), workspace, [], {}, private_root=tmp_path / "private")
    assert result.passed, result.checks
    script.write_text("print(6)\n")
    result = run_isolated_verifier(acceptance(program), workspace, [], {}, private_root=tmp_path / "private")
    assert not result.passed


def test_project_behavior_supports_loopback_and_preserves_readonly_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "candidate"
    workspace.mkdir()
    program = """import socket, sys, tempfile, threading
from pathlib import Path
root = Path(sys.argv[1])
try:
    (root / 'forbidden.txt').write_text('no')
except OSError:
    pass
else:
    raise AssertionError('candidate snapshot is writable')
with tempfile.TemporaryDirectory() as folder:
    Path(folder, 'data.txt').write_text('allowed')
with socket.socket() as server:
    server.bind(('127.0.0.1', 0)); server.listen(1)
    def respond():
        connection, _ = server.accept()
        with connection:
            connection.sendall(b'isolated-loopback')
    thread = threading.Thread(target=respond); thread.start()
    with socket.create_connection(server.getsockname(), timeout=2) as client:
        assert client.recv(100) == b'isolated-loopback'
    thread.join(2)
"""
    result = run_isolated_verifier(acceptance(program), workspace, [], {}, private_root=tmp_path / "private")
    assert result.passed, result.checks
    assert not (workspace / "forbidden.txt").exists()


def test_project_behavior_rejects_unbound_private_program(tmp_path: Path) -> None:
    workspace = tmp_path / "candidate"
    workspace.mkdir()
    spec = acceptance("raise RuntimeError('must not execute')\n")
    spec["checks"][0]["program_sha256"] = "0" * 64
    result = run_isolated_verifier(spec, workspace, [], {}, private_root=tmp_path / "private")
    assert not result.passed
    assert "SHA-256" in result.checks[0].error


def test_project_behavior_browser_exercises_persistence_in_isolation(tmp_path: Path) -> None:
    workspace = tmp_path / "candidate"
    workspace.mkdir()
    (workspace / "index.html").write_text("""<!doctype html><input aria-label="Note"><button>Save</button><output></output>
<script>const input=document.querySelector('input'), output=document.querySelector('output');
output.textContent=localStorage.getItem('note')||'';
document.querySelector('button').onclick=()=>{localStorage.setItem('note',input.value);output.textContent=input.value;};</script>""")
    program = """import functools, sys, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
handler = functools.partial(SimpleHTTPRequestHandler, directory=sys.argv[1])
with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page()
            page.goto('http://127.0.0.1:' + str(server.server_port))
            page.get_by_label('Note').fill('saved across reload')
            page.get_by_role('button', name='Save').click()
            page.reload()
            expect(page.locator('output')).to_have_text('saved across reload')
            browser.close()
    finally:
        server.shutdown()
        thread.join(5)
"""
    result = run_isolated_verifier(acceptance(program, browser=True), workspace, [], {}, private_root=tmp_path / "private")
    assert result.passed, result.checks


def test_candidate_process_cannot_read_private_grader(tmp_path: Path) -> None:
    workspace = tmp_path / "candidate"
    workspace.mkdir()
    (workspace / "probe.py").write_text("""from pathlib import Path
visible = bool(list(Path('/opt/verifier').rglob('*.py')))
for command in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        value = command.read_bytes()
    except (OSError, ProcessLookupError):
        continue
    visible = visible or b'project_driver.py' in value or b'/opt/verifier/programs/' in value
print('visible' if visible else 'hidden')
""")
    program = """import subprocess, sys
from pathlib import Path
actual = subprocess.check_output([sys.executable, str(Path(sys.argv[1]) / 'probe.py')], text=True)
assert actual.strip() == 'hidden', 'candidate can read the private grader'
"""
    result = run_isolated_verifier(acceptance(program), workspace, [], {}, private_root=tmp_path / "private")
    assert result.passed, result.checks


def test_project_behavior_preserves_crlf_program_bytes(tmp_path: Path) -> None:
    workspace = tmp_path / "candidate"
    workspace.mkdir()
    result = run_isolated_verifier(acceptance("assert True\r\n"), workspace, [], {}, private_root=tmp_path / "private")
    assert result.passed, result.checks
