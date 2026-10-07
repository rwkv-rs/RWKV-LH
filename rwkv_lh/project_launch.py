"""Explicit static/Vite launch lifecycle with isolated copies and real receipts.

Launch is a delivery operation. It neither edits the Agent workspace nor changes
its completion decision. Vite installation and scripts run in bubblewrap; only
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
from urllib.parse import urlsplit
import uuid

from .harness import ActionDefinition, ActionHarness, ActionResult, HarnessError
from .project_preview import preview_server


class LaunchError(RuntimeError):
    pass


PROJECT_CHECK = ActionDefinition(
    'check_project', (
        'Launch a disposable static or standard Vite project, run optional argv checks, then stop it. '
        'static serves cwd/index.html; vite installs dependencies and requires build -> dist/index.html. '
        'argv runs with Python/Playwright available against a read-only served copy; '
        'RWKV_LH_PROJECT_URL is its actual temporary URL. Logs and failures return as evidence. '
        'Omitting argv checks only HTTP readiness, not user behavior or project completion. '
        'The returned URL is no longer live after this call; use this for self-checks, not persistent preview. '
        'Dependency installs affect only the disposable copy, not the original workspace.'
    ), True, False, False, 120.0,
    {
        'kind': {'type': 'string', 'enum': ['static', 'vite']},
        'cwd': {'type': 'string', 'default': '.', 'description': 'project root relative to the workspace'},
        'argv': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'default': []},
        'timeout': {'type': 'number', 'exclusiveMinimum': 0, 'maximum': 120.0, 'default': 120.0},
    },
    ('action_succeeded',), required_arguments=('kind',), capability_class='local.project_check',
    network_access='public_web', data_boundary='workspace_copy_and_dependency_registry',
    side_effect_class='temporary_processes_and_dependency_downloads', cache_policy='never',
    recovery_policy='do_not_replay_unknown', evidence_output=True)


def register_project_check(harness):
    """The same registration serves Project execution, role schemas and replay.

    Legacy read-only/research Harness menus keep their frozen action vocabulary.
    """
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


def _public_proxy_environment():
    """Carry explicit public network routing, never proxy credentials or host env.

    Package managers need the same route as the caller on proxy-only networks.
    Loopback checks must still reach the actual disposable project directly.
    """
    result = {}
    for name in ('http_proxy', 'https_proxy'):
        values = {os.environ[key].strip() for key in (name, name.upper())
                  if os.environ.get(key, '').strip()}
        if len(values) > 1:
            raise LaunchError(f'{name}: conflicting public proxy URLs')
        if not values:
            continue
        value = values.pop()
        try:
            parsed = urlsplit(value)
            valid = (parsed.scheme in ('http', 'https') and bool(parsed.hostname)
                     and parsed.username is None and parsed.password is None
                     and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
                     and all(ord(char) > 32 for char in value))
            parsed.port  # Validate malformed/out-of-range ports without printing the URL.
        except ValueError:
            valid = False
        if not valid:
            raise LaunchError(f'{name}: public proxy URL required; no credentials, path, query or fragment')
        result[name] = result[name.upper()] = value
    if result:
        result['no_proxy'] = result['NO_PROXY'] = '127.0.0.1,localhost,::1'
    return result


class ProjectLaunch:
    def __init__(self, workspace, *, kind, output, port=8767, timeout=120):
        if kind not in ('static', 'vite'):
            raise ValueError('launch kind must be static or vite')
        if not 0 <= port <= 65535 or not 0 < timeout <= 3600:
            raise ValueError('invalid launch port or startup timeout')
        self.workspace = Path(workspace).resolve(strict=True)
        self.output = Path(output).resolve()
        if self.output.is_relative_to(self.workspace):
            raise ValueError('launch receipts must be outside the source workspace')
        self.kind, self.port, self.timeout = kind, port, timeout
        self.process = self.server = self.thread = self.log = None
        self.copy = self.output / 'workspace'
        self.receipt = dict(kind=kind, source=str(self.workspace), status='new', url=None,
                            reason=None, commands=[], health=None, source_files={},
                            workspace_modified=False, agent_completion_changed=False)

    def _save(self):
        self.receipt['updated_at'] = time.time()
        stage = self.output / 'RECEIPT.tmp'
        stage.write_text(json.dumps(self.receipt, ensure_ascii=False, indent=2) + '\n')
        stage.replace(self.output / 'RECEIPT.json')

    def _snapshot(self):
        self.copy.mkdir()
        # Installed dependencies are recreated in the copy from package/lock
        # files. Do not follow host links or copy repository administration.
        for folder, directories, files in os.walk(self.workspace, followlinks=False):
            directories[:] = sorted(name for name in directories if name not in ('.git', 'node_modules'))
            for name in [*directories, *sorted(files)]:
                source = Path(folder) / name
                relative = source.relative_to(self.workspace)
                if source.is_symlink() or not (source.is_dir() or source.is_file()):
                    raise LaunchError(f'unsupported source entry: {relative}')
                target = self.copy / relative
                if source.is_dir():
                    target.mkdir()
                else:
                    data = source.read_bytes()
                    target.write_bytes(data)
                    target.chmod(source.stat().st_mode & 0o777)
                    self.receipt['source_files'][str(relative)] = hashlib.sha256(data).hexdigest()

    def _preflight(self):
        if not (self.copy / 'index.html').is_file():
            raise LaunchError('工作区根目录缺少 index.html，未执行安装或启动')
        if self.kind == 'vite':
            path = self.copy / 'package.json'
            if not path.is_file():
                raise LaunchError('Vite 启动需要 package.json')
            package = json.loads(path.read_text())
            if not isinstance(package, dict):
                raise LaunchError('package.json must be an object')
            scripts = package.get('scripts', {})
            if not isinstance(scripts, dict) or not isinstance(scripts.get('build'), str) or not scripts['build'].strip():
                raise LaunchError('package.json 缺少 build 脚本')
            dependencies = [package.get(name, {}) for name in ('dependencies', 'devDependencies')]
            if not any(isinstance(d, dict) and isinstance(d.get('vite'), str) for d in dependencies):
                raise LaunchError('package.json 未声明 Vite 依赖')
        with socket.socket() as probe:
            # Match the actual HTTP/Vite listener's restart semantics. A closed
            # connection in TIME_WAIT is not an occupied listening service.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', self.port))
            self.port = probe.getsockname()[1]

    def _command(self, stage, argv, *, deadline, background=False,
                 include_project_venv=False, read_only=False, environment_additions=None):
        if time.monotonic() >= deadline:
            raise LaunchError('startup time budget exhausted before ' + stage)
        harness = ActionHarness()
        if not harness._bubblewrap:
            raise LaunchError('bubblewrap is required for project scripts')
        resolved = list(argv)
        if include_project_venv and resolved[0] == 'python':
            resolved[0] = str(Path(sys.executable).resolve(strict=True))
        command, path = harness._bubblewrap_command(SimpleNamespace(workspace_root=str(self.copy)),
            self.copy, resolved, workspace=self.copy, include_project_venv=include_project_venv)
        if read_only:
            index = command.index('--bind')
            if command[index + 1:index + 3] != [str(self.copy), '/workspace']:
                raise LaunchError('unexpected checker workspace mount')
            command[index] = '--ro-bind'
        # WSL's /etc/resolv.conf can point outside /etc. Mount that single
        # resolved file before making the namespace root read-only, keeping
        # the rest of /mnt and the host home absent.
        resolver = Path('/etc/resolv.conf').resolve(strict=True)
        if not resolver.is_relative_to('/etc'):
            index = command.index('--remount-ro')
            command[index:index] = ['--ro-bind', str(resolver), str(resolver)]
        # Serving on the requested loopback port and fetching dependencies are
        # explicit parts of this launch mode. Host files and credentials stay
        # outside the mount namespace; environment inheritance is allowlisted.
        command.insert(command.index('--chdir'), '--share-net')
        environment = dict(PATH=path, LANG='C.UTF-8', npm_config_cache='/tmp/npm-cache',
                           npm_config_userconfig='/dev/null', npm_config_update_notifier='false')
        proxies = _public_proxy_environment()
        environment.update(proxies)
        if include_project_venv:
            environment['PYTHONPATH'] = f'/opt/rwkv-lh-venv/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages'
        environment.update(environment_additions or {})
        log_path = self.output / (stage + '.log')
        row = dict(stage=stage, argv=argv, log=str(log_path), started_at=time.time(),
                   exit_code=None, timed_out=False, sandbox='bubblewrap', network='shared',
                   network_proxy=bool(proxies))
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
            if self.kind == 'vite':
                install = 'ci' if (self.copy / 'package-lock.json').is_file() else 'install'
                self._command('install', ['npm', install, '--ignore-scripts', '--no-audit', '--no-fund'], deadline=deadline)
                self._command('build', ['npm', 'run', 'build'], deadline=deadline)
                root = self.copy / 'dist'
                if not (root / 'index.html').is_file():
                    raise LaunchError('build did not produce dist/index.html')
                if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
                    raise LaunchError('built output must contain regular files, not symbolic links')
                expected = (root / 'index.html').read_bytes()
                self._command('serve', ['node', 'node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1',
                                       '--port', str(self.port), '--strictPort'], deadline=deadline, background=True)
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
                        body = response.read(len(expected) + 1)
                        if response.status == 200 and body == expected:
                            self.receipt['health'] = dict(status=200, body_sha256=hashlib.sha256(body).hexdigest(),
                                                          matches_built_entry=True, checked_at=time.time())
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
                           timeout=arguments['timeout'])
    deadline = time.monotonic() + arguments['timeout']
    checker = None
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
        success = True
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        try:
            if checker is not None:
                checker.stop()
        finally:
            launch.stop()
    receipt = {'launch': launch.status(), 'observed_url': observed_url, 'behavior_check': behavior,
               'check_commands': checker.status()['commands'] if checker is not None else [],
               'logs': [], 'source_modified': False, 'agent_completion_changed': False}
    summary = {'launch_status': receipt['launch']['status'], 'health': receipt['launch']['health'],
               'behavior_check': behavior, 'service_stopped': True,
               'observed_url': observed_url, 'url_is_currently_live': False, 'error': error}
    text = [json.dumps(summary, ensure_ascii=False)]
    for row in [*receipt['launch']['commands'], *receipt['check_commands']]:
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


def serve_project(workspace, *, kind, output, port=8767, timeout=120):
    launch = ProjectLaunch(workspace, kind=kind, output=output, port=port, timeout=timeout)
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
