"""Local static artifact preview; it never generates files or accepts a project."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import uuid


def new_project_paths(output=None):
    if output is None:
        root = Path(__file__).resolve().parents[1] / 'data' / 'project_runs'
        output = root / ('project-' + uuid.uuid4().hex[:12]) / 'run'
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    source = Path(tempfile.mkdtemp(prefix=output.name + '-source-', dir=output.parent))
    return source, output


def preview_unavailable_reason(workspace):
    if workspace is None:
        return '尚无项目文件。'
    workspace = Path(workspace)
    entry = workspace / 'index.html'
    if not entry.is_file() or entry.is_symlink():
        reason = f'工作区根目录没有可直接预览的 index.html：{workspace}'
        if (workspace / 'package.json').is_file():
            reason += '。检测到 package.json；当前预览仅支持静态文件，未执行 npm 安装、构建或启动脚本'
        return reason + '。项目中的运行说明不代表服务已启动。'
    return None


class _ArtifactHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        root = Path(self.directory).resolve()
        path = Path(self.translate_path(self.path))
        try:
            relative = path.resolve().relative_to(root)
        except (ValueError, OSError, RuntimeError):
            self.send_error(404)
            return None
        if any(part.startswith('.') for part in relative.parts):
            self.send_error(404)
            return None
        if path.is_dir():
            for name in ('index.html', 'index.htm'):
                candidate = path / name
                if candidate.is_symlink():
                    try:
                        candidate.resolve().relative_to(root)
                    except (ValueError, OSError, RuntimeError):
                        self.send_error(404)
                        return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404, 'No page at this path')
        return None

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def preview_server(workspace, *, port=8767):
    issue = preview_unavailable_reason(workspace)
    if issue:
        raise FileNotFoundError(issue)
    workspace = Path(workspace).resolve(strict=True)
    return ThreadingHTTPServer(('127.0.0.1', port), partial(_ArtifactHandler, directory=str(workspace)))


def serve_preview(workspace, *, port=8767):
    with preview_server(workspace, port=port) as server:
        print(f'Preview: http://localhost:{server.server_port}', flush=True)
        print(f'Files: {Path(workspace).resolve()}', flush=True)
        print('Static preview only; inspect actual page behavior. Ctrl+C stops the preview.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
