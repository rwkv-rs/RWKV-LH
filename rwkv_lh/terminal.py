"""Interactive terminal presentation around the unchanged Project Agent CLI."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid

from .project_preview import preview_server, preview_unavailable_reason, serve_preview

ROOT = Path(__file__).resolve().parents[1]


def _display_text(value, limit=180):
    """Bound untrusted terminal text without changing the recorded model output."""
    text = ''.join(char if char.isprintable() else ' ' for char in str(value))
    return text if len(text) <= limit else text[:limit] + '…'


def _request_summaries(value):
    """Describe raw model requests for display, without validating or executing them."""
    if not isinstance(value, dict):
        return []
    calls = value.get('tool_calls')
    if isinstance(calls, list):
        names = []
        for call in calls:
            function = call.get('function') if isinstance(call, dict) else None
            if isinstance(function, dict) and isinstance(function.get('name'), str):
                names.append(_display_text(function['name']))
        return names
    name = value.get('function')
    if not isinstance(name, str) or not name:
        return []
    params = value.get('params')
    params = params if isinstance(params, dict) else {}
    arguments = params
    step = ''
    if name == 'execute_tool':
        tool = params.get('tool')
        if isinstance(tool, str) and tool:
            name = tool
        arguments = params.get('arguments')
        arguments = arguments if isinstance(arguments, dict) else {}
        if isinstance(params.get('step_id'), str):
            step = '（步骤 ' + _display_text(params['step_id'], 40) + '）'
    details = [str(arguments[key]) for key in ('path', 'command', 'pattern', 'receipt_id', 'outcome')
               if isinstance(arguments.get(key), (str, int, float))]
    detail = (' ' + _display_text(' · '.join(details))) if details else ''
    return [_display_text(name, 60) + detail + step]


def _progress(trace, offset):
    if not trace.exists():
        return offset
    with trace.open() as stream:
        stream.seek(offset)
        while True:
            position = stream.tell()
            line = stream.readline()
            if not line or not line.endswith('\n'):
                return position
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            role = _display_text(event.get('project_role', ''), 40)
            if event.get('type') == 'model_session_generation_started':
                print(f'  [{role}] 正在生成…', flush=True)
            elif event.get('type') == 'model_session_generation_returned':
                if event.get('finish_reason') == 'length':
                    print(f'  [{role}] 输出被截断；本次不完整调用未执行，原文保留在 trace。', flush=True)
                    continue
                # Presentation only: this neither validates nor authorizes an action.
                try:
                    value = json.loads(event.get('raw_output', ''))
                    summaries = _request_summaries(value)
                except (ValueError, TypeError):
                    summaries = []
                if summaries:
                    for summary in summaries:
                        print(f'  [{role}] 模型请求 {summary}', flush=True)
                else:
                    print(f'  [{role}] 已返回，原文保留在 trace', flush=True)


def _run_child(argv, output):
    log_path = output.parent / (output.name + '.terminal.log')
    output.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('x') as log:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        offset = 0
        try:
            while process.poll() is None:
                offset = _progress(output / 'execution/model_trace.jsonl', offset)
                time.sleep(.2)
            _progress(output / 'execution/model_trace.jsonl', offset)
            if not (output / 'DELIVERY.json').exists():
                print('\n'.join(log_path.read_text(errors='replace').splitlines()[-12:]), flush=True)
            return process.returncode
        except KeyboardInterrupt:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            print('已停止本次执行；原始记录保留，未确认操作不会自动重试。', flush=True)
            return 130


class TerminalSession:
    def __init__(self, root, *, max_calls, max_seconds, source=None, output=None,
                 extra_args=(), runner=_run_child):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_calls, self.max_seconds = max_calls, max_seconds
        self.workspace = Path(source).resolve() if source else None
        self.explicit_output = Path(output).resolve() if output else None
        self.extra_args = list(extra_args)
        self.runner = runner
        self.requests = []
        self.turns = []
        self.exit_code = 0
        self.unconfirmed = False

    def execute(self, request):
        if self.unconfirmed:
            raise RuntimeError('上一轮有未确认操作或执行中断，请先检查记录；不会自动继续或重发。')
        request = request.strip()
        if not request:
            raise ValueError('任务不能为空')
        output = self.explicit_output if not self.turns and self.explicit_output else self.root / f'turn-{len(self.turns)+1:03d}'
        if output.exists():
            raise FileExistsError(f'输出目录已存在：{output}')
        self.requests.append(request)
        combined = request if len(self.requests) == 1 else (
            '用户最初目标：\n' + self.requests[0] + '\n\n用户后续要求（按顺序，保留原目标，按后续要求修订）：\n' +
            '\n\n'.join(f'{index}. {text}' for index, text in enumerate(self.requests[1:], 1)))
        argv = [sys.executable, '-m', 'scripts.run_rwkv_agent', '--request', combined,
                '--output-dir', str(output), '--max-calls', str(self.max_calls),
                '--max-seconds', str(self.max_seconds), *self.extra_args]
        argv += ['--source-workspace', str(self.workspace)] if self.workspace else ['--new-project']
        print(f'\n任务：{request}\n项目：{output}/workspace', flush=True)
        code = self.runner(argv, output)
        delivery = output / 'DELIVERY.json'
        result = json.loads(delivery.read_text()) if delivery.exists() else {
            'termination': 'interrupted', 'termination_reason': 'no_delivery_receipt', 'changed_files': []}
        result['process_exit_code'] = code
        self.exit_code = 0 if code == 0 and result.get('termination') in ('submitted', 'model_finished') else 1
        self.unconfirmed = (code == 130 or not delivery.exists() or
                            bool(result.get('diagnostics', {}).get('pending_operation')))
        if (output / 'workspace').is_dir():
            self.workspace = output / 'workspace'
        self.turns.append(dict(request=request, output=str(output), termination=result.get('termination'),
                               termination_reason=result.get('termination_reason'), process_exit_code=code,
                               unconfirmed=self.unconfirmed))
        (self.root / 'SESSION.json').write_text(json.dumps(dict(requests=self.requests, turns=self.turns,
            workspace=str(self.workspace) if self.workspace else None), ensure_ascii=False, indent=2)+'\n')
        print(f'\nAgent 状态：{result.get("termination_reason", result.get("termination"))}', flush=True)
        if result.get('termination_reason') == 'model_output_budget_exhausted':
            print('原因：模型达到单次输出上限，不是总调用次数耗尽。'
                  '本次不完整调用未执行，之前已确认的文件修改仍保留。', flush=True)
        print('修改文件：' + (', '.join(result.get('changed_files') or []) or '无'), flush=True)
        print(f'记录：{output}/execution\n回执：{delivery}', flush=True)
        return result


class _LivePreview:
    def __init__(self, port, *, kind='static', timeout=120, npm_script='preview'):
        self.port = port
        self.kind, self.timeout, self.npm_script = kind, timeout, npm_script
        self.launch = None
        self.server = None
        self.thread = None

    def close(self):
        if self.launch:
            self.launch.stop()
            self.launch = None
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=3)
            self.server = None

    def update(self, workspace):
        self.close()
        if self.kind == 'npm' and workspace is not None:
            from .project_launch import ProjectLaunch, LaunchError, new_launch_output
            self.launch = ProjectLaunch(workspace, kind='npm', output=new_launch_output(),
                                        port=self.port, timeout=self.timeout, npm_script=self.npm_script)
            try:
                result = self.launch.start()
                print(f'项目已就绪：{result["url"]}（启动不代表任务验收通过）', flush=True)
            except LaunchError as exc:
                print(f'未启动项目：{exc}', flush=True)
            print(f'启动回执：{self.launch.output / "RECEIPT.json"}', flush=True)
            return
        issue = preview_unavailable_reason(workspace)
        if issue:
            print(f'未启动网页预览：{issue}', flush=True)
            return
        self.server = preview_server(workspace, port=self.port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f'网页预览：http://localhost:{self.server.server_port}（预览不代表任务验收通过）', flush=True)


def run_terminal(args):
    root = ROOT / 'data/terminal_runs' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    extra = []
    for field in ('base_url', 'model', 'model_sha256'):
        value = getattr(args, field, None)
        if value is not None:
            extra.extend(['--'+field.replace('_', '-'), value])
    for flag in ('record_generation_snapshots',):
        if getattr(args, flag, False):
            extra.append('--'+flag.replace('_', '-'))
    for path in args.protected_paths:
        extra.extend(['--protected-paths', path])
    session = TerminalSession(root, max_calls=args.max_calls, max_seconds=args.max_seconds,
                              source=args.source_workspace, output=args.output_dir, extra_args=extra)
    print('RWKV-LH · 项目终端\n输入需求即可执行；/help 查看命令，/exit 退出。', flush=True)
    print('源项目：' + (str(session.workspace) if session.workspace else '新建空项目'), flush=True)
    preview = _LivePreview(args.port, kind=args.launch_kind, timeout=args.launch_timeout,
                           npm_script=args.launch_script)
    request = args.request_text or args.request
    try:
        while True:
            if request is None:
                try:
                    request = input('\n任务 > ').strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
            if not request:
                request = None
                continue
            if request in ('/exit', '/quit'):
                break
            if request == '/help':
                print('直接输入需求；后续要求基于上次产物的副本执行。\n/files 查看文件，/status 查看结果，/open 启动预览，/stop 停止服务，/exit 退出。')
            elif request == '/files':
                print(str(session.workspace) if session.workspace else '尚无项目')
                if session.workspace:
                    print('\n'.join(str(p.relative_to(session.workspace)) for p in sorted(session.workspace.rglob('*')) if p.is_file()))
            elif request == '/status':
                print(json.dumps(session.turns[-1] if session.turns else {'status':'尚未执行'}, ensure_ascii=False, indent=2))
                if preview.launch:
                    result = preview.launch.status()
                    print(json.dumps({key:result[key] for key in ('status','url','reason')}, ensure_ascii=False))
            elif request == '/open':
                preview.update(session.workspace)
            elif request == '/stop':
                preview.close()
                print('服务已停止。', flush=True)
            elif request.startswith('/'):
                print('未知命令；输入 /help 查看可用命令。')
            else:
                session.execute(request)
                if not args.no_preview:
                    if args.interactive:
                        preview.update(session.workspace)
                    else:
                        if args.launch_kind == 'npm' and session.workspace is not None:
                            from .project_launch import serve_project, new_launch_output
                            serve_project(session.workspace, kind='npm', output=new_launch_output(),
                                          port=args.port, timeout=args.launch_timeout, npm_script=args.launch_script)
                        else:
                            issue = preview_unavailable_reason(session.workspace)
                            if issue:
                                print(f'未启动网页预览：{issue}', flush=True)
                            else:
                                serve_preview(session.workspace, port=args.port)
                if not args.interactive:
                    break
            request = None
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'终端执行停止：{exc}', file=sys.stderr)
        return 1
    finally:
        preview.close()
    return session.exit_code
