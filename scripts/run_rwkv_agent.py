"""Run coding projects with RWKV-directed planning or explicit read-only utilities."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.agent_batch import run_agent_jobs
from rwkv_lh.agent_jobs import CodingJob
from rwkv_lh.read_only_agent import ReadOnlyJob
from rwkv_lh.runtime.settings import direct_agent_settings, RuntimeSettings, load_local_env


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--jobs', type=Path,
                        help='JSON array: task_id, request, workspace, output_dir, tool_scope, budgets')
    source.add_argument('--source-workspace')
    source.add_argument('--new-project', action='store_true',
                        help='Start from an empty workspace; --output-dir is optional')
    source.add_argument('--preview', type=Path,
                        help='Serve an existing static workspace without calling a model')
    source.add_argument('--launch', type=Path,
                        help='Launch an existing project copy with install/build/health receipts; no model call')
    source.add_argument('--resume', type=Path, help='Resume a project output directory with its original budgets')
    parser.add_argument('--request')
    parser.add_argument('request_text', nargs='?', help='Natural-language task; start an empty project by default')
    parser.add_argument('-i', '--interactive', action='store_true', help='Interactive terminal with follow-up requests')
    parser.add_argument('--no-preview', action='store_true', help='Do not start a static preview in terminal mode')
    parser.add_argument('--output-dir')
    parser.add_argument('--task-id', default='coding-task')
    parser.add_argument('--record-generation-snapshots', action='store_true')
    parser.add_argument('--require-initial-plan', action='store_true',
                        help='Explicitly require strong planning before the first RWKV decision')
    parser.add_argument('--protected-paths', action='append', default=[],
                        help="Read-only coding workspace path, '.' or './path'; repeat as needed")
    parser.add_argument('--max-calls', type=int, default=None)
    parser.add_argument('--max-seconds', type=float, default=None)
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--serve', action='store_true',
                        help='Preview generated index.html after a single task, preserving its outcome')
    parser.add_argument('--port', type=int, default=8767, help='Local static preview port (default: 8767)')
    parser.add_argument('--launch-kind', choices=('static', 'vite'), default='static',
                        help='Explicit delivery launcher; vite installs and builds in an isolated copy')
    parser.add_argument('--launch-timeout', type=float, default=120,
                        help='Total installation/build/readiness budget in seconds (default: 120)')
    for name in ('base-url', 'model', 'model-sha256'):
        parser.add_argument('--' + name)
    args = parser.parse_args(argv)
    terminal_mode = bool(args.request_text or args.interactive or not argv)
    args.interactive = args.interactive or not argv
    if args.max_calls is None:
        args.max_calls = 64 if terminal_mode else 12
    if args.max_seconds is None:
        args.max_seconds = 900 if terminal_mode else 600
    if args.concurrency < 1:
        parser.error('concurrency must be positive')
    if not 1 <= args.port <= 65535:
        parser.error('port must be in 1..65535')
    if not 0 < args.launch_timeout <= 3600:
        parser.error('launch-timeout must be in (0, 3600]')
    if terminal_mode:
        if args.jobs or args.resume or args.preview or args.launch or (args.request_text and args.request):
            parser.error('terminal requests cannot be combined with jobs, resume, preview or a second request')
        from rwkv_lh.terminal import run_terminal
        return run_terminal(args)
    if args.no_preview:
        parser.error('--no-preview belongs to terminal mode')
    if not any((args.jobs, args.source_workspace, args.new_project, args.preview, args.launch, args.resume)):
        parser.error('enter a task, or select --new-project, --source-workspace, --jobs, --preview or --resume')
    if args.launch:
        if args.request or args.serve or args.protected_paths or args.require_initial_plan:
            parser.error('--launch only runs the existing project')
        from rwkv_lh.project_launch import serve_project, new_launch_output, LaunchError
        try:
            serve_project(args.launch, kind=args.launch_kind, output=args.output_dir or new_launch_output(),
                          port=args.port, timeout=args.launch_timeout)
        except (OSError, ValueError, LaunchError) as exc:
            parser.error(str(exc))
        return 0
    if args.preview:
        if args.launch_kind != 'static':
            parser.error('use --launch with --launch-kind vite')
        if args.request or args.output_dir or args.serve or args.protected_paths or args.require_initial_plan:
            parser.error('--preview only serves the existing workspace')
        from rwkv_lh.project_preview import serve_preview
        try:
            serve_preview(args.preview, port=args.port)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        return 0
    if args.serve and (args.jobs or args.resume):
        parser.error('--serve requires --new-project or --source-workspace; use --preview for existing runs')
    if args.launch_kind != 'static' and not args.serve:
        parser.error('--launch-kind requires --launch, --serve or terminal mode')
    if args.new_project:
        if not args.request or not args.request.strip():
            parser.error('--new-project requires --request')
        from rwkv_lh.project_preview import new_project_paths
        try:
            source_path, output_path = new_project_paths(args.output_dir)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        args.source_workspace, args.output_dir = str(source_path), str(output_path)
        print(f'Project output: {output_path}', flush=True)
    if args.resume:
        if args.request or args.output_dir or args.protected_paths or args.require_initial_plan:
            parser.error('--resume uses the recorded request and workspace')
        from rwkv_lh.project_agent import resume_project
        load_local_env(Path(__file__).resolve().parents[1] / '.env.local')
        overrides = {name: getattr(args, name) for name in ('base_url', 'model', 'model_sha256') if getattr(args, name) is not None}
        result = resume_project(args.resume, settings=RuntimeSettings.from_env(overrides=overrides))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['termination'] == 'submitted' else 1
    jobs = []
    if args.source_workspace:
        if not args.request or not args.output_dir:
            parser.error('single coding task requires --request and --output-dir')
        rows = [dict(task_id=args.task_id, request=args.request, workspace=args.source_workspace,
                     output_dir=args.output_dir, tool_scope='coding', max_calls=args.max_calls,
                     max_seconds=args.max_seconds, record_generation_snapshots=args.record_generation_snapshots,
                     protected_paths=args.protected_paths, require_initial_plan=args.require_initial_plan)]
    else:
        if args.request or args.output_dir or args.protected_paths or args.require_initial_plan:
            parser.error('--request and --output-dir belong to single coding tasks')
        rows = json.loads(args.jobs.read_text())
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        parser.error('jobs must be a nonempty array of objects')
    for row in rows:
        row = dict(row)
        parents = row.pop('depends_on', [])
        if not isinstance(parents, list):
            parser.error('depends_on must be an array of task IDs')
        if parents:
            parser.error('project dependencies belong in the project plan; depends_on is retired from this entry')
        if 'assistance' in row:
            parser.error('project assistance is requested by the decision role; legacy assistance jobs are retired')
        scope = row.pop('tool_scope', 'files')
        recovery = row.pop('on_stall', None)
        if recovery is not None:
            parser.error('on_stall is retired; project decisions request help or replanning explicitly')
        if scope == 'coding':
            row['source_workspace'] = row.pop('workspace')
            jobs.append(CodingJob(**row))
        elif scope in ('files', 'inspect'):
            jobs.append(ReadOnlyJob(**row, tool_scope=scope))
        else:
            parser.error('tool_scope must be files, inspect or coding')
    load_local_env(Path(__file__).resolve().parents[1] / '.env.local')
    overrides = {name: getattr(args, name) for name in ('base_url', 'model', 'model_sha256')
                 if getattr(args, name) is not None}
    settings = direct_agent_settings(RuntimeSettings.from_env(overrides=overrides))
    results = run_agent_jobs(jobs, settings=settings, concurrency=args.concurrency)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    exit_code = 0 if all(r['termination'] == 'submitted' for r in results) else 1
    if args.serve:
        from rwkv_lh.project_preview import serve_preview
        print(f'Agent termination: {results[0]["termination"]}; preview does not change task completion.', flush=True)
        try:
            if args.launch_kind == 'vite':
                from rwkv_lh.project_launch import serve_project, new_launch_output
                serve_project(Path(args.output_dir) / 'workspace', kind='vite', output=new_launch_output(),
                              port=args.port, timeout=args.launch_timeout)
            else:
                serve_preview(Path(args.output_dir) / 'workspace', port=args.port)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f'Preview unavailable: {exc}', file=sys.stderr)
            return 1
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
