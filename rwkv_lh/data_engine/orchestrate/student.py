"""RWKV-first offline collection; teachers replace one real failed boundary at a time."""
import asyncio
from pathlib import Path

from rwkv_lh.agent_jobs import CodingJob
from rwkv_lh.project_agent import run_project_job, resume_project, continue_project
from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.project_sessions import ProjectSessions
from rwkv_lh.project_trace import agent_boundaries
from rwkv_lh.data_engine.branch import fork_episode, ReplacementThenStudent
from rwkv_lh.data_engine.correct import diagnosis_input, diagnose, replacement
from rwkv_lh.data_engine.records import write_immutable, record_episode
from rwkv_lh.data_engine.tasks import dump
from rwkv_lh.data_engine.verify import admit, verify, turn_facts
from rwkv_lh.data_engine.build import export_episode
from rwkv_lh.evaluation_policy import assert_training_record_allowed, assert_training_source_allowed


def collect_student_episode(root, task, *, settings, pool, student_identity,
                            max_correction_rounds, candidates_per_round,
                            student_factory=ProjectSessions):
    """Called in a worker's main thread; never swaps policies inside the live product.

    The caller freezes correction search limits separately from Agent step budgets.
    Every unsuccessful branch is retained. There is no Qwen takeover fallback.
    """
    import json
    for value in (max_correction_rounds, candidates_per_round):
        if type(value) is not int or value < 1:
            raise ValueError('explicit positive offline correction search limits required')
    assert_training_record_allowed(task)
    assert_training_source_allowed(root)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    registration = {'task_digest': task['digest'], 'student': student_identity,
        'teacher': {k: pool.provider[k] for k in ('id', 'model')},
        'max_correction_rounds': max_correction_rounds, 'candidates_per_round': candidates_per_round,
        'rollout_policy': 'rwkv_then_offline_qwen_correction', 'optimizer_updates': 0}
    write_immutable(root / 'REGISTRATION.json', dump(registration).encode())
    directory = root / 'task'
    if (directory / 'ADMISSION.json').exists():
        admission = json.loads((directory / 'ADMISSION.json').read_text())
        if not admission['admitted'] or admission['task_digest'] != task['digest']:
            raise ValueError('task admission identity differs')
    else:
        admit(task, directory)
    teacher = registration['teacher']

    def finish_attempt(run, port, result):
        with ProjectLedger.read_snapshot(run / 'execution') as db:
            state = db.scan_verified_events()['state']
        if state['pending'] or state['inbox'] or state['status'] == 'running':
            raise ValueError('unconfirmed student attempt requires recovery, not another branch')
        if task.get('followups') and len(state['requests']) == 1 and state['status'] == 'finished':
            first = verify({**task, 'acceptance': task['first_acceptance']}, run / 'workspace', run / 'verify-first')
            if first['passed']:
                result = continue_project(run, task['followups'][0], settings=settings, agent_port=port)
        verdict = verify(task, run / 'workspace', run / 'verify-final')
        with ProjectLedger.read_snapshot(run / 'execution') as db:
            state = db.scan_verified_events()['state']
        strict = bool(verdict['passed'] and state['status'] == 'finished' and not state['pending']
                      and not state['inbox'] and len(state['requests']) == 1 + len(task.get('followups', [])))
        row = {'Strict': strict, 'completed': verdict['passed'], 'mutation': result['mutation_count'],
               'termination_reason': result['termination_reason'], 'model_calls': state['calls'],
               'run': str(run), 'record': record_episode(task, run, verdict=verdict)}
        if strict:
            row['export'] = export_episode(task, run, verdict, root / 'production', root / 'exports',
                teacher=teacher, student=student_identity,
                rollout_policy='rwkv_with_qwen_correction' if state.get('correction_fork') else 'rwkv')
        write_immutable(run / 'ENGINE_RESULT.json', dump(row).encode())
        return row

    run = root / (task['id'] + '-student')
    if (run / 'ENGINE_RESULT.json').exists():
        row = json.loads((run / 'ENGINE_RESULT.json').read_text())
    else:
        port = student_factory(settings, run / 'execution') if run.exists() else None
        if port:
            result = resume_project(run, settings=settings, agent_port=port)
        else:
            # Lazy construction avoids creating the ledger directory before create().
            class LazyStudent:
                current = None
                def get(self):
                    if self.current is None: self.current = student_factory(settings, run / 'execution')
                    return self.current
                def preflight(self, *args):
                    preflight = getattr(self.get(), 'preflight', None)
                    if preflight: return preflight(*args)
                def request(self, *args): return self.get().request(*args)
            port = LazyStudent()
            result = run_project_job(CodingJob(task['id'], task['request'], str(directory / 'seed'), str(run),
                task['max_calls'], task['max_seconds'], protected_paths=tuple(task['protected_paths']),
                record_generation_snapshots=True), settings=settings, agent_port=port)
        row = finish_attempt(run, port, result)
    if row.get('export'):
        return row
    for round_index in range(max_correction_rounds):
        source = run
        labels = turn_facts(source / 'execution')
        if not row['completed']: labels.append('acceptance_failed')
        evidence = diagnosis_input(source / 'execution', failure_labels=labels)
        prefix = root / ('correction-%03d' % round_index)
        write_immutable(prefix / 'VISIBLE_EVIDENCE.json', dump(evidence).encode())
        diagnosis = asyncio.run(diagnose(pool, evidence, key=str(prefix) + ':diagnose'))
        write_immutable(prefix / 'DIAGNOSIS.json', dump(diagnosis).encode())
        boundary = list(agent_boundaries(source / 'execution'))[diagnosis['k']]
        for candidate_index in range(candidates_per_round):
            run = prefix / (task['id'] + '-r%03d-candidate-%03d' % (round_index, candidate_index))
            if (run / 'ENGINE_RESULT.json').exists():
                row = json.loads((run / 'ENGINE_RESULT.json').read_text())
                if row.get('export'): return row
                continue
            message = asyncio.run(replacement(pool, boundary, category=diagnosis['category'], key=str(run) + ':replacement'))
            if not run.exists(): fork_episode(source, run, boundary['operation_id'])
            student = student_factory(settings, run / 'execution')
            port = ReplacementThenStudent(run, message, student, teacher=teacher)
            result = resume_project(run, settings=settings, agent_port=port)
            row = finish_attempt(run, port, result)
            if row.get('export'): return row
        # Deterministic search order; no hidden-test contents go to the teacher.
        # The final tried branch is the next round's genuine student attempt.
    write_immutable(root / 'CORRECTIONS_EXHAUSTED.json', dump(row).encode())
    return row
