"""Explicit static/npm launch lifecycle with isolated copies and real receipts.

Launch is an external delivery operation, outside the RWKV tool catalog.
It neither edits the Agent workspace nor changes
its completion decision. npm installation and scripts run in bubblewrap; only
the launch copy, system toolchain and network are available to those processes.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import urllib.request
import uuid

from .harness import ActionDefinition, ActionHarness, ActionResult, HarnessError
from .project_preview import preview_server
from .project_browser import BROWSER_STEPS_SCHEMA
from .workspace_snapshot import copy_verified_workspace, tree_identity
from .process_network import command_network_environment


class LaunchError(RuntimeError):
    pass


PROJECT_CHECK = ActionDefinition(
    'check_project', (
        'Launch a disposable static or npm frontend, run optional argv checks, then stop it. '
        'static serves cwd/index.html. npm installs locked dependencies with ci when a lockfile exists; '
        'npm_script dev runs the declared dev script, while preview first runs build and requires dist/index.html. '
        'npm scripts receive HOST=127.0.0.1, PORT and --host/--port arguments; no framework dependency is required. '
        'argv runs with Python/Playwright available against a read-only served copy; '
        'RWKV_LH_PROJECT_URL is its actual temporary URL. Logs and failures return as evidence. '
        'Optional browser_steps execute real Chromium actions and assertions with retained screenshots, DOM, console and network records. '
        'Omitting both argv and browser_steps checks only HTTP readiness, not user behavior or project completion. '
        'The returned URL is no longer live after this call; this is an external check, not persistent preview. '
        'Dependency installs affect only the disposable copy, not the original workspace.'
    ), True, False, False, 120.0,
    {
        'kind': {'type': 'string', 'enum': ['static', 'npm']},
        'npm_script': {'type': 'string', 'enum': ['dev', 'preview'], 'default': 'preview',
                       'description': 'Requested npm server script; used only for kind npm.'},
        'cwd': {'type': 'string', 'default': '.', 'description': 'project root relative to the workspace'},
        'argv': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'default': []},
        'browser_steps': BROWSER_STEPS_SCHEMA,
        'timeout': {'type': 'number', 'exclusiveMinimum': 0, 'maximum': 120.0, 'default': 120.0},
    },
    ('action_succeeded',), required_arguments=('kind',), capability_class='local.project_check',
    network_access='public_web', data_boundary='workspace_copy_and_dependency_registry',
    side_effect_class='temporary_processes_and_dependency_downloads', cache_policy='never',
    recovery_policy='do_not_replay_unknown', evidence_output=True)


def register_project_check(harness):
    """Explicitly register the external checker; Project actors exclude it."""
    try:
        existing = harness.definition(PROJECT_CHECK.name)
    except HarnessError:
        existing = None
    if existing is not None:
        if existing != PROJECT_CHECK:
            raise ValueError('project check contract differs from the canonical definition')
        return
    harness.register_action(PROJECT_CHECK, lambda goal, arguments: check_project(harness, goal, arguments))


def new_launch_output():
    return Path(__file__).resolve().parents[1] / 'data/project_launches' / uuid.uuid4().hex


class ProjectLaunch:
    def __init__(self, workspace, *, kind, output, port=8767, timeout=120, npm_script='preview'):
        if kind not in ('static', 'npm'):
            raise ValueError('launch kind must be static or npm')
        if npm_script not in ('dev', 'preview'):
            raise ValueError('npm script must be dev or preview')
        if not 0 <= port <= 65535 or not 0 < timeout <= 3600:
            raise ValueError('invalid launch port or startup timeout')
        self.workspace = Path(workspace).resolve(strict=True)
        self.output = Path(output).resolve()
        if self.output.is_relative_to(self.workspace):
            raise ValueError('launch receipts must be outside the source workspace')
        self.kind, self.port, self.timeout, self.npm_script = kind, port, timeout, npm_script
        self.process = self.server = self.thread = self.log = None
        self.copy = self.output / 'workspace'
        self.receipt = dict(kind=kind, source=str(self.workspace), status='new', url=None,
                            reason=None, commands=[], health=None, source_files={},
                            workspace_modified=False, agent_completion_changed=False)
        if kind == 'npm':
            self.receipt['npm_script'] = npm_script

    def _save(self):
        self.receipt['updated_at'] = time.time()
        stage = self.output / 'RECEIPT.tmp'
        stage.write_text(json.dumps(self.receipt, ensure_ascii=False, indent=2) + '\n')
        stage.replace(self.output / 'RECEIPT.json')

    def _snapshot(self):
        # Share the same portable-link identity as Actor copies and snapshots.
        # npm ci recreates installed dependencies in this disposable copy when
        # a lockfile exists; the original workspace remains unchanged.
        tree = copy_verified_workspace(self.workspace, self.copy, audit_path=self.output / 'COPY.json')
        self.receipt['source_tree'] = tree
        self.receipt['source_files'] = {path: record['sha256'] for path, record in tree.items()
                                        if record['kind'] == 'file'}

    def _preflight(self):
        if self.kind == 'static' and not (self.copy / 'index.html').is_file():
            raise LaunchError('工作区根目录缺少 index.html，未执行安装或启动')
        if self.kind == 'npm':
            path = self.copy / 'package.json'
            if not path.is_file():
                raise LaunchError('npm 启动需要 package.json')
            package = json.loads(path.read_text())
            if not isinstance(package, dict):
                raise LaunchError('package.json must be an object')
            scripts = package.get('scripts', {})
            required = ['build', 'preview'] if self.npm_script == 'preview' else ['dev']
            for script in required:
                if not isinstance(scripts, dict) or not isinstance(scripts.get(script), str) or not scripts[script].strip():
                    raise LaunchError(f'package.json 缺少 {script} 脚本')
        with socket.socket() as probe:
            # Match the actual HTTP listener's restart semantics. A closed
            # connection in TIME_WAIT is not an occupied listening service.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', self.port))
            self.port = probe.getsockname()[1]

    def _command(self, stage, argv, *, deadline, background=False,
                 include_project_venv=False, read_only=False, environment_additions=None,
                 browser_spec=None, browser_artifacts=None):
        if time.monotonic() >= deadline:
            raise LaunchError('startup time budget exhausted before ' + stage)
        harness = ActionHarness()
        if not harness._bubblewrap:
            raise LaunchError('bubblewrap is required for project scripts')
        resolved = list(argv)
        if include_project_venv and resolved[0] == 'python':
            resolved[0] = str(Path(sys.executable).resolve(strict=True))
        command, path = harness._bubblewrap_command(SimpleNamespace(workspace_root=str(self.copy)),
            self.copy, resolved, workspace=self.copy, include_project_venv=include_project_venv,
            shared_network=True)
        if read_only:
            index = command.index('--bind')
            if command[index + 1:index + 3] != [str(self.copy), '/workspace']:
                raise LaunchError('unexpected checker workspace mount')
            command[index] = '--ro-bind'
        if browser_spec is not None:
            if browser_artifacts is None or not read_only:
                raise LaunchError('browser worker requires separate evidence and a read-only project')
            index = command.index('--remount-ro')
            command[index:index] = [
                '--ro-bind', str(Path(__file__).with_name('project_browser.py')), '/opt/project-browser/worker.py',
                '--ro-bind', str(browser_spec), '/opt/project-browser/spec.json',
                '--bind', str(browser_artifacts), '/opt/project-browser/evidence']
        environment = dict(PATH=path, LANG='C.UTF-8', **command_network_environment())
        if include_project_venv:
            environment['PYTHONPATH'] = f'/opt/rwkv-lh-venv/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages'
        environment.update(environment_additions or {})
        log_path = self.output / (stage + '.log')
        row = dict(stage=stage, argv=argv, log=str(log_path), started_at=time.time(),
                   exit_code=None, timed_out=False, sandbox='bubblewrap', network='shared',
                   network_proxy=any(name in environment for name in ('http_proxy', 'https_proxy')))
        self.receipt['commands'].append(row)
        self._save()
        self.log = log_path.open('xb')
        self.process = subprocess.Popen(command, env=environment, cwd=self.copy,
                                        stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
        row['pid'] = self.process.pid
        if background:
            self._save()
            return
        try:
            row['exit_code'] = self.process.wait(timeout=max(.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            row['timed_out'] = True
            self._stop_process()
            row['exit_code'] = self.process.returncode
            raise LaunchError(f'{stage} exceeded startup time budget; see {log_path}')
        finally:
            if self.log:
                self.log.close()
            self.log = None
            row['ended_at'] = time.time()
            self._save()
        if row['exit_code'] != 0:
            raise LaunchError(f'{stage} failed with exit {row["exit_code"]}; see {log_path}')
        self.process = None

    def _stop_process(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=3)
        if self.log:
            self.log.close()
            self.log = None

    def _owns_listener(self):
        """Bind readiness to this launch's process descendants, including npm/bwrap.

        A dev server can transform index.html, so byte equality is not an identity
        check for that mode. The listener must belong to the started process tree.
        """
        if self.process is None or self.process.poll() is not None:
            return False
        inodes = set()
        for name in ('tcp', 'tcp6'):
            for line in (Path('/proc/net') / name).read_text().splitlines()[1:]:
                fields = line.split()
                if fields[3] == '0A' and int(fields[1].rsplit(':', 1)[1], 16) == self.port:
                    inodes.add('socket:[' + fields[9] + ']')
        if not inodes:
            return False
        parents = {}
        for entry in Path('/proc').iterdir():
            if not entry.name.isdecimal():
                continue
            try:
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                parents[int(entry.name)] = int(fields[1])
            except (OSError, IndexError, ValueError):
                continue
        for pid in parents:
            current, visited = pid, set()
            while current in parents and current != self.process.pid and current not in visited:
                visited.add(current)
                current = parents[current]
            if current != self.process.pid:
                continue
            try:
                for descriptor in (Path('/proc') / str(pid) / 'fd').iterdir():
                    try:
                        if str(descriptor.readlink()) in inodes:
                            return True
                    except OSError:
                        continue
            except OSError:
                continue
        return False

    def start(self):
        if self.receipt['status'] != 'new':
            raise LaunchError('use a new launch directory for another start')
        self.output.mkdir(parents=True, exist_ok=False)
        self.receipt['status'] = 'starting'
        self._save()
        deadline = time.monotonic() + self.timeout
        try:
            self._snapshot()
            self._preflight()
            root = self.copy
            if self.kind == 'npm':
                install = 'ci' if (self.copy / 'package-lock.json').is_file() else 'install'
                self._command('install', ['npm', install, '--ignore-scripts', '--no-audit', '--no-fund'], deadline=deadline)
                expected = None
                if self.npm_script == 'preview':
                    self._command('build', ['npm', 'run', 'build'], deadline=deadline)
                    root = self.copy / 'dist'
                    # Validate links against the project, including output
                    # directories that are themselves aliases. Preserve the
                    # installed dependency tree and the actual build identity.
                    self.receipt['built_tree'] = tree_identity(self.copy)
                    if not (root / 'index.html').is_file():
                        raise LaunchError('build did not produce dist/index.html')
                    expected = (root / 'index.html').read_bytes()
                self._command('serve', ['npm', 'run', self.npm_script, '--', '--host', '127.0.0.1',
                                       '--port', str(self.port)], deadline=deadline, background=True,
                              environment_additions={'HOST': '127.0.0.1', 'PORT': str(self.port)})
            else:
                expected = (root / 'index.html').read_bytes()
                self.server = preview_server(root, port=self.port)
                self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.thread.start()
            url = f'http://127.0.0.1:{self.port}'
            # A process alone is not readiness, nor is another service's 200.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            while time.monotonic() < deadline:
                if self.process is not None and self.process.poll() is not None:
                    raise LaunchError(f'service exited before ready; see {self.output / "serve.log"}')
                try:
                    with opener.open(url, timeout=min(1, max(.01, deadline - time.monotonic()))) as response:
                        limit = len(expected) if expected is not None else 1024 * 1024
                        body = response.read(limit + 1)
                        owned = self.process is None or self._owns_listener()
                        matches = (body == expected if expected is not None else
                                   bool(body) and len(body) <= limit and response.headers.get_content_type() == 'text/html')
                        if response.status == 200 and owned and matches:
                            self.receipt['health'] = dict(status=200, body_sha256=hashlib.sha256(body).hexdigest(),
                                matches_built_entry=expected is not None, owned_listener=owned, checked_at=time.time())
                            break
                except OSError:
                    pass
                time.sleep(.05)
            else:
                raise LaunchError('service did not return the built page within the startup time budget')
            if self.process is not None and self.process.poll() is not None:
                raise LaunchError('service exited during readiness check')
            self.receipt.update(status='ready', url=url, port=self.port)
            self._save()
            return self.status()
        except BaseException as error:
            self.receipt.update(status='failed', reason=str(error) or type(error).__name__, url=None)
            self.stop()
            if not isinstance(error, Exception):
                raise
            raise LaunchError(str(error)) from error

    def status(self):
        if self.receipt['status'] == 'ready':
            dead = ((self.process is not None and self.process.poll() is not None)
                    or (self.thread is not None and not self.thread.is_alive()))
            if dead:
                self.receipt.update(status='failed', reason='service_exited', url=None)
                if self.process is not None:
                    self.receipt['commands'][-1]['exit_code'] = self.process.returncode
                self._save()
        return deepcopy(self.receipt)

    def stop(self):
        self._stop_process()
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=3)
            self.server = self.thread = None
        if self.receipt['status'] != 'failed':
            self.receipt.update(status='stopped', reason='stopped_by_caller')
        if self.process is not None and self.receipt['commands']:
            self.receipt['commands'][-1]['exit_code'] = self.process.returncode
        self.receipt['url'] = None
        if self.output.is_dir():
            self._save()


def check_project(harness, goal, arguments):
    """One ordinary Harness operation, with no persistent service or guessed repair.

    The project and behavioral command are isolated from the source workspace.
    The checker only reads the served copy so it cannot rewrite it into a pass.
    Cancellation is not a known failure: it propagates after process cleanup,
    leaving the existing ledger's pending operation unconfirmed.
    """
    source = harness.resolve_path(goal, arguments['cwd'], must_exist=True)
    if not source.is_dir():
        raise ValueError('project cwd must be a directory')
    output = new_launch_output()
    launch = ProjectLaunch(source, kind=arguments['kind'], output=output, port=0,
                           timeout=arguments['timeout'], npm_script=arguments['npm_script'])
    deadline = time.monotonic() + arguments['timeout']
    checker = browser_checker = None
    browser_record = {'status': 'not_run', 'steps': [], 'assertions_passed': 0, 'artifacts': []}
    behavior = {'status': 'not_run', 'argv': arguments['argv']}
    observed_url, error = None, None
    success = False
    try:
        ready = launch.start()
        observed_url = ready['url']
        if arguments['argv']:
            behavior['status'] = 'failed'
            checker = ProjectLaunch(source, kind='static', output=output / 'behavior', port=0)
            checker.output.mkdir()
            checker.copy = launch.copy
            checker._command('check', arguments['argv'], deadline=deadline, include_project_venv=True,
                read_only=True, environment_additions={'RWKV_LH_PROJECT_URL': observed_url})
            if launch.status()['status'] != 'ready':
                raise LaunchError('service exited during behavior check')
            behavior['status'] = 'passed'
        if arguments.get('browser_steps'):
            browser_checker = ProjectLaunch(source, kind='static', output=output / 'browser', port=0)
            browser_checker.output.mkdir()
            browser_checker.copy = launch.copy
            artifacts = browser_checker.output / 'artifacts'
            artifacts.mkdir()
            spec = browser_checker.output / 'SPEC.json'
            spec.write_text(json.dumps({'url': observed_url, 'steps': arguments['browser_steps'],
                                       'timeout': max(.01, deadline - time.monotonic())}) + '\n')
            browser_record.update(status='running', input_sha256=hashlib.sha256(spec.read_bytes()).hexdigest(),
                worker_sha256=hashlib.sha256(Path(__file__).with_name('project_browser.py').read_bytes()).hexdigest())
            browser_checker._command('browser', ['python', '-B', '/opt/project-browser/worker.py',
                '/opt/project-browser/spec.json', '/opt/project-browser/evidence'], deadline=deadline,
                include_project_venv=True, read_only=True, browser_spec=spec, browser_artifacts=artifacts)
            if launch.status()['status'] != 'ready':
                raise LaunchError('service exited during browser check')
        success = True
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        try:
            if checker is not None:
                checker.stop()
            if browser_checker is not None:
                browser_checker.stop()
        finally:
            launch.stop()
    if browser_checker is not None:
        artifacts = browser_checker.output / 'artifacts'
        journal = artifacts / 'JOURNAL.json'
        if journal.is_file():
            browser_record.update(json.loads(journal.read_text()))
        if browser_record['status'] == 'running':
            browser_record['status'] = 'interrupted'
        for path in sorted(artifacts.iterdir()):
            if path.is_symlink() or not path.is_file():
                raise LaunchError('browser evidence requires regular files')
            data = path.read_bytes()
            browser_record['artifacts'].append({'path': str(path), 'bytes': len(data),
                                                'sha256': hashlib.sha256(data).hexdigest()})
        success = success and browser_record['status'] == 'passed'
    receipt = {'launch': launch.status(), 'observed_url': observed_url, 'behavior_check': behavior,
               'check_commands': checker.status()['commands'] if checker is not None else [],
               'browser_commands': browser_checker.status()['commands'] if browser_checker is not None else [],
               'browser_check': browser_record,
               'logs': [], 'source_modified': False, 'agent_completion_changed': False}
    summary = {'launch_status': receipt['launch']['status'], 'health': receipt['launch']['health'],
               'behavior_check': behavior, 'service_stopped': True,
               'browser_check': browser_record,
               'observed_url': observed_url, 'url_is_currently_live': False, 'error': error}
    text = [json.dumps(summary, ensure_ascii=False)]
    for row in [*receipt['launch']['commands'], *receipt['check_commands'], *receipt['browser_commands']]:
        log = Path(row['log'])
        if log.is_file():
            data = log.read_bytes()
            receipt['logs'].append({'stage': row['stage'], 'path': str(log), 'bytes': len(data),
                                    'sha256': hashlib.sha256(data).hexdigest()})
            text.extend([f'\n{row["stage"]} log (actual process output):', data.decode('utf-8', errors='replace')])
    result = ActionResult('check_project', success, output='\n'.join(text),
        exit_code=(receipt['check_commands'][-1]['exit_code'] if receipt['check_commands'] else None),
        metadata={'project_check': receipt, 'workspace_ephemeral': True, 'writes_discarded': True}, error=error)
    (output / 'CHECK_RESULT.json').write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + '\n')
    return result


def serve_project(workspace, *, kind, output, port=8767, timeout=120, npm_script='preview'):
    launch = ProjectLaunch(workspace, kind=kind, output=output, port=port, timeout=timeout, npm_script=npm_script)
    try:
        result = launch.start()
        print(f'项目已就绪：{result["url"]}\n启动回执：{launch.output / "RECEIPT.json"}', flush=True)
        print('请检查实际功能；Ctrl+C 停止服务。', flush=True)
        while launch.status()['status'] == 'ready':
            time.sleep(.2)
        raise LaunchError(f'服务已退出：{launch.output / "RECEIPT.json"}')
    except KeyboardInterrupt:
        pass
    finally:
        launch.stop()
