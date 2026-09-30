"""Run coding projects with RWKV-directed planning or explicit read-only utilities."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.agent_batch import run_agent_jobs
from rwkv_lh.agent_integration import run_agent_workflow
from rwkv_lh.assisted_agent import AssistedJob
from rwkv_lh.coding_agent import CodingJob
from rwkv_lh.goal_delivery import GoalJob
from rwkv_lh.read_only_agent import ReadOnlyJob
from rwkv_lh.runtime.settings import direct_agent_settings, RuntimeSettings, load_local_env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--jobs', type=Path,
                        help='JSON array: task_id, request, workspace, output_dir, tool_scope, budgets')
    source.add_argument('--source-workspace')
    source.add_argument('--resume', type=Path, help='Resume a project output directory with its original budgets')
    parser.add_argument('--request')
    parser.add_argument('--output-dir')
    parser.add_argument('--task-id', default='coding-task')
    parser.add_argument('--record-generation-snapshots', action='store_true')
    parser.add_argument('--require-initial-plan', action='store_true',
                        help='Explicitly require strong planning before the first RWKV decision')
    parser.add_argument('--protected-paths', action='append', default=[],
                        help="Read-only coding workspace path, '.' or './path'; repeat as needed")
    parser.add_argument('--max-calls', type=int, default=12)
    parser.add_argument('--max-seconds', type=float, default=600)
    parser.add_argument('--concurrency', type=int, default=1)
    for name in ('base-url', 'model', 'model-sha256'):
        parser.add_argument('--' + name)
    args = parser.parse_args(argv)
    if args.concurrency < 1:
        parser.error('concurrency must be positive')
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
    dependencies = {}
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
    results = (run_agent_workflow(jobs, dependencies, settings=settings, concurrency=args.concurrency)
               if dependencies else run_agent_jobs(jobs, settings=settings, concurrency=args.concurrency))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r['termination'] == 'submitted' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
