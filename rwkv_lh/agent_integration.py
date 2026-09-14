"""Explicit dependency scheduling and conflict-rejecting artifact integration.

The caller declares dependencies. No business planning, semantic merge, model
answer editing, or acceptance decisions occur in this module.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil

from .coding_agent import CodingJob, _inventory, run_coding_job
from .job_budget import task_deadline
from .read_only_agent import _save


def _load_delivery(root):
    root = Path(root).resolve(strict=True)
    delivery = json.loads((root / 'DELIVERY.json').read_text())
    if delivery.get('termination') != 'submitted' or not delivery.get('trace_complete'):
        raise ValueError('dependency has no reviewable submission')
    workspace = Path(delivery['workspace']).resolve(strict=True)
    actual = _inventory(workspace)
    if actual != delivery.get('final_files'):
        raise ValueError('dependency workspace changed')
    if any(value.startswith('symlink:') for value in actual.values()):
        raise ValueError('integration requires regular files')
    return delivery, workspace, actual


def integrate_deliveries(base, parents, output):
    """Merge exact file changes from the same frozen base; reject conflicts."""
    base, output = Path(base).resolve(strict=True), Path(output).resolve()
    parents = list(parents)
    if not parents:
        raise ValueError('integration needs explicit dependencies')
    original = {p: value for p, value in _inventory(base).items() if '.git' not in Path(p).parts}
    if any(value.startswith('symlink:') for value in original.values()):
        raise ValueError('integration requires regular files')
    edits, contents, modes, provenance = {}, {}, {}, []
    protected = [base]
    for parent in parents:
        parent = Path(parent).resolve(strict=True)
        delivery, workspace, actual = _load_delivery(parent)
        initial = json.loads((parent / 'INITIAL_FILES.json').read_text())
        if initial != original:
            raise ValueError('integration base mismatch')
        protected.extend((parent, workspace))
        for path in original.keys() | actual.keys():
            value = actual.get(path)
            if value == original.get(path):
                continue
            if path in edits and edits[path] != value:
                raise ValueError('integration conflict: ' + path)
            edits[path] = value
            if value is not None:
                content = (workspace / path).read_bytes()
                if hashlib.sha256(content).hexdigest() != value:
                    raise ValueError('dependency workspace changed while reading')
                mode = (workspace / path).stat().st_mode & 0o777
                if path in modes and modes[path] != mode:
                    raise ValueError('integration conflict: file mode ' + path)
                contents[path] = content
                modes[path] = mode
        provenance.append({'directory': str(parent), 'assistance': delivery.get('assistance'),
                           'delivery_sha256': hashlib.sha256((parent / 'DELIVERY.json').read_bytes()).hexdigest()})
    expected = {**original, **edits}
    expected = {p: value for p, value in expected.items() if value is not None}
    for path in expected:
        if any(str(parent) in expected for parent in Path(path).parents if str(parent) != '.'):
            raise ValueError('integration conflict: file/directory ' + path)
    if any(output == p or output in p.parents or p in output.parents for p in protected):
        raise ValueError('integration output overlaps inputs')
    if output.exists():
        raise FileExistsError(output)
    shutil.copytree(base, output, ignore=shutil.ignore_patterns('.git'))
    # Delete old file leaves first so directory/file replacements can proceed.
    for path in sorted(edits, key=lambda p: len(Path(p).parts), reverse=True):
        target = output / path
        if target.is_file():
            target.unlink()
    for path, content in contents.items():
        target = output / path
        if target.is_dir():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(modes[path])
    if _inventory(output) != expected:
        raise ValueError('integrated artifact differs from frozen inputs')
    return {'workspace': str(output), 'final_files': expected, 'parents': provenance,
            'acceptance': 'not_evaluated'}


@dataclass(frozen=True)
class DependentJob(CodingJob):
    parent_outputs: tuple[str, ...] = ()


@task_deadline
def run_dependent_job(job, *, settings):
    root = Path(job.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=False)
    try:
        if len(job.parent_outputs) == 1:
            parent, previous_source, expected = _load_delivery(job.parent_outputs[0])
            source = root / 'integrated'
            shutil.copytree(previous_source, source)
            if _inventory(source) != expected:
                raise ValueError('dependency changed while copying')
            integration = {'parents': list(job.parent_outputs), 'acceptance': 'not_evaluated'}
        else:
            integration = integrate_deliveries(job.source_workspace, job.parent_outputs, root / 'integrated')
            source = Path(integration['workspace'])
    except (ValueError, OSError) as exc:
        return {'id': job.task_id, 'final': None, 'termination': 'blocked',
            'termination_reason': 'integration_rejected', 'acceptance': 'not_evaluated',
            'generation_started': 0, 'trace_complete': False, 'assistance': 'rwkv_independent',
            'dependencies': list(job.parent_outputs),
            'error': {'type': type(exc).__name__, 'message': str(exc)}}
    _save(root / 'INTEGRATION.json', integration)
    child = CodingJob(job.task_id, job.request, str(source), str(root / 'execution'),
                      job.max_calls, job.max_seconds)
    result = run_coding_job(child, settings=settings)
    initial = root / 'execution/INITIAL_FILES.json'
    if initial.exists():
        shutil.copy2(initial, root / 'INITIAL_FILES.json')
    return {**result, 'dependencies': list(job.parent_outputs), 'integration': integration}


def run_agent_workflow(jobs, dependencies, *, settings, concurrency=1):
    """Run a caller-declared DAG; submissions unblock work, not acceptance.

    Multi-parent joins require a shared frozen base. Divergent bases or file
    conflicts are returned as failures rather than automatically resolved.
    """
    from .agent_batch import validate_agent_jobs, run_agent_jobs
    jobs = validate_agent_jobs(jobs, concurrency=concurrency)
    by_id = {job.task_id: job for job in jobs}
    if not isinstance(dependencies, dict) or set(dependencies) - set(by_id):
        raise ValueError('unknown dependency task')
    graph = {}
    for key in by_id:
        parents = dependencies.get(key, [])
        if not isinstance(parents, (list, tuple)) or any(not isinstance(p, str) or p not in by_id for p in parents):
            raise ValueError('unknown dependency')
        if len(set(parents)) != len(parents):
            raise ValueError('duplicate dependency')
        if parents and (type(by_id[key]) is not CodingJob or any(type(by_id[p]) is not CodingJob for p in parents)):
            raise ValueError('dependent integration currently requires explicit coding jobs')
        graph[key] = set(parents)
    visited = set()
    while len(visited) < len(jobs):
        ready = {key for key, parents in graph.items() if key not in visited and parents <= visited}
        if not ready:
            raise ValueError('dependency cycle')
        visited.update(ready)
    results = {}
    while len(results) < len(jobs):
        wave = []
        for job in jobs:
            key, parents = job.task_id, graph[job.task_id]
            if key in results or not parents <= results.keys():
                continue
            if any(results[p]['termination'] != 'submitted' for p in parents):
                results[key] = {'id': key, 'termination': 'blocked', 'termination_reason': 'dependency_failed',
                    'final': None, 'acceptance': 'not_evaluated', 'generation_started': 0,
                    'dependencies': sorted(parents), 'assistance': 'rwkv_independent'}
                from .agent_batch import _save_failure
                _save_failure(job, results[key])
            elif parents:
                wave.append(DependentJob(job.task_id, job.request, job.source_workspace, job.output_dir,
                    job.max_calls, job.max_seconds, tuple(by_id[p].output_dir for p in sorted(parents))))
            else:
                wave.append(job)
        if wave:
            for job, result in zip(wave, run_agent_jobs(wave, settings=settings, concurrency=concurrency)):
                results[job.task_id] = result
    return [results[job.task_id] for job in jobs]
