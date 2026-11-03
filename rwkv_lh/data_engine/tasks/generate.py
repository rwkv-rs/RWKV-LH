"""Author independent executable projects; never generate purported tool receipts.

The author sees private test specifications. The rollout policy receives only
the admitted seed workspace and the original user requests. Author responses
are candidates, not training data: execution admission is a separate gate.
"""
import asyncio
import json
from pathlib import Path, PurePosixPath

from . import checksum, dump
from ...project_contracts import scope_path
from ..qwen import TeacherPool


DOMAINS = (
    'parcel dispatch', 'library circulation', 'equipment maintenance', 'lab sample tracking',
    'conference scheduling', 'photo cataloguing', 'local archive search', 'warehouse reservations',
    'static documentation publishing', 'incident log analysis', 'backup restoration', 'sensor ingestion',
    'subscription reconciliation', 'release packaging', 'dataset validation', 'job queue monitoring',
    'volunteer scheduling', 'travel expense processing', 'artifact provenance', 'translation management',
    'recipe planning', 'course registration', 'community event booking', 'media playlist management',
    'fleet maintenance', 'retail stock reconciliation', 'access policy auditing', 'test report aggregation',
    'build dependency analysis', 'offline document search', 'batch image metadata', 'device configuration',
)
WORKFLOWS = (
    'Deliver a new feature across an existing CLI, domain layer and persistence format while preserving old behavior.',
    'Reproduce an integration failure from user reports, trace its cross-module cause, repair it and add a regression test.',
    'Migrate stored data and its readers/writers together, retain backwards input compatibility and prove reruns are safe.',
    'Repair and extend an HTTP service, exercise actual HTTP behavior, inspect a background process and shut it down cleanly.',
    'Complete a multi-stage import/validate/transform/report pipeline with partial failure handling and reproducible artifacts.',
    'Refactor a tangled application behind stable public interfaces; preserve behavior and correct a documented edge case.',
    'Implement a usable static web interface together with its data export and run end-to-end checks using Playwright.',
    'Diagnose a packaging or configuration integration problem, implement a reusable repair and document working commands.',
)

AUTHOR = '''Create one ORIGINAL realistic project task for a coding agent running in a persistent sandbox.
Return only the native submit_project tool call. You are the offline task author, not the executing agent.
Do not imitate a transcript, fabricate tool receipts, copy a benchmark, or solve a one-function puzzle.
The project must contain connected modules and realistic existing behavior. Avoid repeated cosmetic
renaming of one template. Give this project its own interfaces, data model, directory layout and failure modes.
Require exploration, implementation, running real commands and checking deliverables. A competent solution
should need work across multiple components, but never require pointless edits or pad the number of calls.

Runtime: Python 3.12+ standard library, SQLite, Bash, system Node, HTML/CSS/JS; pytest and Python Playwright
are installed. No pip/npm downloads or external APIs required. Use ephemeral ports (port 0) for services.
All files are UTF-8. No symlinks, secrets, binary files or absolute workspace paths. Every process must stop.
Include README.md with exact visible specifications and runnable public checks, realistic input fixtures,
and enough working code to form a coherent project. Do not put private tests or answers in the seed.
Public checks are honest examples, never a misleading test that always passes.

Provide seed_files (relative path -> complete content), reference_files (only changed/new files for a full
correct solution), and three semantic mutants (path -> complete replacement content applied AFTER reference).
Mutants should represent distinct plausible incomplete solutions (e.g. edge case, migration, error handling),
not syntax errors, null outputs or deleted files. They must each fail at least one PRIVATE check.
The reference must actually pass every private check and the seed must fail at least one.
Provide a standalone PRIVATE Python checker, invoked as python checker.py WORKSPACE. It must launch the
real program through subprocess or HTTP, test at least three independent visible requirements with asserted
expected results, and exit nonzero on failure. Derive expectations independently; do not import reference
solutions. Do not accept just a file name, source-text matching or an agent's assertion. Tests may work on
temporary copies of the workspace to create databases or artifacts. The supplied workspace is read-only.
Use sys.executable for Python subprocesses, cwd=workspace, bounded timeouts, and finally cleanup for servers.
No private values or requirements that are absent from the visible contract.

Optionally include one genuine follow-up user request that builds on the completed first request in the
same workspace. Supply a separate first-stage private checker if you do this; the final checker verifies
both stages. The reference_files represent the final solution; first_reference_files represent the first
stage. Do not invent a follow-up just to increase trajectory length.
The user request must read like real work assigned by a maintainer. It may refer to README or docs, but
must not prescribe a tool-call script or reveal the answer. Include English or Chinese as instructed.
'''

FILE_MAP = {'type': 'object', 'additionalProperties': {'type': 'string'}}
SUBMIT = [{'type': 'function', 'function': {'name': 'submit_project',
    'description': 'Submit a complete executable project candidate for independent execution admission.',
    'parameters': {'type': 'object', 'additionalProperties': False,
        'properties': {'title': {'type': 'string'}, 'request': {'type': 'string'},
            'seed_files': FILE_MAP, 'reference_files': FILE_MAP,
            'mutants': {'type': 'array', 'items': FILE_MAP, 'minItems': 3},
            'private_checker': {'type': 'string'},
            'protected_paths': {'type': 'array', 'items': {'type': 'string'}},
            'followup': {'type': 'string'}, 'first_checker': {'type': 'string'},
            'first_reference_files': FILE_MAP},
        'required': ['title', 'request', 'seed_files', 'reference_files', 'mutants',
                     'private_checker', 'protected_paths']}}}]


def assignment(index):
    domain = DOMAINS[index % len(DOMAINS)]
    workflow = (index // len(DOMAINS)) % len(WORKFLOWS)
    return {'index': index, 'domain': domain, 'workflow': workflow,
            'brief': WORKFLOWS[workflow], 'variant': index // (len(DOMAINS) * len(WORKFLOWS)),
            'language': 'Chinese' if index % 2 else 'English'}


def _checker(program):
    compile(program, '<private checker>', 'exec')
    import hashlib
    return {'checks': [{'kind': 'project_behavior', 'program': program,
                        'program_sha256': hashlib.sha256(program.encode()).hexdigest(), 'timeout': 60}]}


def make_candidate(candidate, spec, response, provider):
    """Validate structure only; functional approval always requires real execution."""
    for field in ('seed_files', 'reference_files'):
        if not isinstance(candidate[field], dict) or not candidate[field]:
            raise ValueError('nonempty file map required: ' + field)
    if len(candidate['mutants']) < 3:
        raise ValueError('three semantic negative controls required')
    maps = [candidate['seed_files'], candidate['reference_files'], *candidate['mutants']]
    if candidate.get('first_reference_files'):
        maps.append(candidate['first_reference_files'])
    for files in maps:
        canonical=set()
        for path, content in files.items():
            scope_path(path)
            identity=PurePosixPath(path)
            if identity in canonical or identity==PurePosixPath('.'):
                raise ValueError('duplicate or non-file task path')
            canonical.add(identity)
            if not isinstance(content, str):
                raise ValueError('UTF-8 task content required')
    for path in candidate['protected_paths']:
        scope_path(path)
    seed={PurePosixPath(p):c for p,c in candidate['seed_files'].items()}
    reference={**seed,**{PurePosixPath(p):c for p,c in candidate['reference_files'].items()}}
    protected=[PurePosixPath(p) for p in candidate['protected_paths']]
    variants=[(candidate['reference_files'],seed),(candidate.get('first_reference_files',{}),seed)]
    variants.extend((files,reference) for files in candidate['mutants'])
    for files,baseline in variants:
        for name,content in files.items():
            path=PurePosixPath(name)
            if content!=baseline.get(path) and any(path==p or p in path.parents for p in protected):
                raise ValueError('reference or mutant modifies a protected path')
    source = {'kind': 'original_teacher_authored_project', 'assignment': spec,
        'author_model': provider['model'], 'author_provider': provider['id'],
        'author_response_sha256': checksum(response), 'generator_sha256': checksum(Path(__file__).read_text())}
    task = {'id': f'project-{spec["index"]:06d}', 'title': candidate['title'],
        'family': 'project_' + spec['domain'].replace(' ', '_'),
        'workflow': spec['workflow'], 'request': candidate['request'],
        'seed_files': candidate['seed_files'], 'reference_files': candidate['reference_files'],
        'mutants': candidate['mutants'], 'protected_paths': candidate['protected_paths'],
        'acceptance': _checker(candidate['private_checker']), 'seed_must_fail': True,
        'max_calls': None, 'max_seconds': None, 'source': source,
        'admission_status': 'requires_execution'}
    if candidate.get('followup'):
        task['followups'] = [candidate['followup']]
        task['first_acceptance'] = _checker(candidate['first_checker'])
        task['first_reference_files'] = candidate['first_reference_files']
    task['digest'] = checksum(task)
    return task


async def generate(root, provider, *, count, workers=32, start=0, indices=None):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    pool = TeacherPool(provider, root / 'author.sqlite3')
    queue = asyncio.Queue()
    for index in (indices if indices is not None else range(start, start + count)):
        queue.put_nowait(index)
    async def worker():
        while not queue.empty():
            index = queue.get_nowait()
            directory = root / f'project-{index:06d}'
            directory.mkdir(parents=True, exist_ok=True)
            if (directory / 'task.json').exists():
                continue
            spec = assignment(index)
            messages = [{'role': 'system', 'content': AUTHOR},
                        {'role': 'user', 'content': dump(spec)}]
            try:
                response = await pool.complete(messages, key='author:' + checksum(messages),
                    tools=SUBMIT, lane='task_generation', max_output_tokens=24000)
                (directory / 'AUTHOR_RESPONSE.json').write_text(dump(response))
                choice = response['choices'][0]
                if choice.get('finish_reason') == 'length':
                    raise ValueError('task author output truncated; not repaired')
                calls = choice['message'].get('tool_calls') or []
                if len(calls) != 1 or calls[0]['function']['name'] != 'submit_project':
                    raise ValueError('one native submit_project call required')
                candidate = json.loads(calls[0]['function']['arguments'])
                task = make_candidate(candidate, spec, response, provider)
                (directory / 'task.json').write_text(dump(task))
                print(json.dumps({'event': 'authored', 'id': task['id'], 'title': task['title'],
                    'seed_files': len(task['seed_files']), 'reference_files': len(task['reference_files'])}), flush=True)
            except Exception as exc:
                (directory / 'ERROR.json').write_text(dump({'error': type(exc).__name__, 'detail': str(exc)}))
                print(json.dumps({'event': 'author_error', 'id': index, 'error': str(exc)}), flush=True)
    await asyncio.gather(*(worker() for _ in range(workers)))
    (root / 'AUTHOR_STATUS.json').write_text(dump(pool.status()))
