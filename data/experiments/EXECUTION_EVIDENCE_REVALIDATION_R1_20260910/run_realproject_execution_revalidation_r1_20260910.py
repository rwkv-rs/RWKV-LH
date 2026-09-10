"""Collect all twelve authorized development tasks through the production runner.

Local WSL driver only. No role prompts, labels, reference solutions or tools are
constructed here. Private acceptance is consumed only by the existing runner.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(ROOT))
ROUND = ROOT / 'data/experiments/REALPROJECT_EXECUTION_REVALIDATION_R1_20260910'
BUNDLE = ROOT / 'benchmarks/rwkv_e2e/rwkv_real_project_dev_v1'
OUTPUT = ROUND / 'all_zero'
SUITE = 'realprojectdevv1'
ZERO = '0' * 64
PUBLIC_CATALOGS = (
    'benchmarks/architecture_regression/lh_control_30/tasks.json',
    'benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1/tasks.json',
    'benchmarks/rwkv_e2e/rwkv_agent_v1/tasks.json',
    'benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json',
    'benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json',
    'benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json',
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def write(path: Path, value) -> None:
    with path.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def configure():
    from rwkv_lh.runtime.settings import load_local_env, reset_runtime_settings
    from rwkv_lh.supervisor_openai import SupervisorAPISettings
    from rwkv_lh.exact_tool_selector.native_network_client import NativeNetworkSelectorSettings
    from scripts import run_rwkv_e2e_benchmark as benchmark
    assert os.environ.get('WSL_DISTRO_NAME') == 'UbuntuRecovered'
    load_local_env()
    # Every role State is explicit. Ordinary deployment fields use the same
    # canonical local configuration; never override the strong Planner route.
    for role in ('EXECUTOR', 'AUDITOR_STEP', 'FINALIZER', 'AUDITOR_FINAL'):
        os.environ[f'RWKV_LH_{role}_STATE_PROFILE_ID'] = 'zero'
        os.environ[f'RWKV_LH_{role}_STATE_PROFILE_SHA256'] = ZERO
        os.environ[f'RWKV_LH_{role}_STATE_PROFILE_DELIVERY'] = 'request'
        os.environ[f'RWKV_LH_{role}_RETURN_TOKEN_IDS'] = 'true'
        os.environ[f'RWKV_LH_{role}_READ_TIMEOUT'] = '300'
    os.environ['RWKV_RUNTIME_MODE'] = 'external'
    os.environ['RWKV_EXECUTOR_PROFILE_ROUTING'] = 'disabled'
    reset_runtime_settings()
    roles = benchmark._goal_role_settings(benchmark.get_runtime_settings())
    planner = SupervisorAPISettings.from_env()
    selector = NativeNetworkSelectorSettings.from_env()
    assert planner.model == 'deepseek-v4-pro' and planner.stream_responses
    assert planner.base_url.rstrip('/') == 'https://api.deepseek.com'
    expected_options = {'thinking': {'type': 'enabled'}, 'reasoning_effort': 'low'}
    assert planner.planner_request_options == planner.stage_checker_request_options == expected_options
    assert planner.backend_profile == 'openai-compatible' and not planner.fallback_models
    assert selector is not None and selector.state_profile_id == 'zero'
    assert all(s.state_profile_id == 'zero' and s.state_profile_sha256 == ZERO for s in roles.values())
    return benchmark, roles, planner, selector


def verify_bundle():
    tasks = json.loads((BUNDLE / 'tasks.json').read_text())['tasks']
    assert len(tasks) == 12 and len({t['task_id'] for t in tasks}) == 12
    assert all(t['task_id'].startswith('RP-') for t in tasks)
    return {'public_task_sha256': digest(BUNDLE / 'tasks.json')}, tasks


def prepare():
    from rwkv_lh.role_trace_artifacts import byte_5gram_cosine, split_project_family
    from rwkv_lh.role_trace_stages import validate_collection_contract
    from rwkv_lh.stateful_goal_loop import STATEFUL_GOAL_LOOP_ARCHITECTURE
    from rwkv_lh.supervisor_openai import OpenAICompatibleSupervisorClient
    import requests
    benchmark, roles, planner, selector = configure()
    manifest, tasks = verify_bundle()
    ROUND.mkdir(exist_ok=True)
    OUTPUT.mkdir()
    families = {t['task_id']: 'realprojectdevv1:' + t['task_id'] for t in tasks}
    scope = {'schema_version': 'rwkv-lh.role-trace-coverage-scope.v1',
        'objective': 'Selector tool choice during implementation and public checks across the three authorized UltraData Code tasks and twelve owner-authorized realprojectdevv1 development tasks; current-role phase coverage, not final Agent acceptance',
        'requirements': {'selector_intent': ['py_root', 'mutate', 'execute', 'missing_target']}}
    write(ROUND / 'COVERAGE_SCOPE.json', scope)
    registration = {
        'round_id': ROUND.name, 'created_at': datetime.now(timezone.utc).isoformat(),
        'owner_authorization': '2026-09-10 current owner explicitly requests rerunning all fixed 15 tasks after execution and transport repair. Prior scope: 2026-09-10 owner explicitly authorized replacement of the faulty handoff architecture, complete tests, then defect-driven stagewise StateTune; full 12-task development collection previously authorized on 2026-09-07, after OFFICIAL_PLANNER_TRACE_REPAIR_R1, using explicit low thinking and the complete production tool registry, preserving all prior results',
        'purpose': 'Owner requested 15-task evaluation after b3e89de6; preserve historical scores and record first transport errors',
        'source_kind': 'owner-authorized authored development benchmark; actual current production Harness traces',
        'source_public_task_sha256': digest(BUNDLE / 'tasks.json'),
        'driver_path': str(Path(__file__)), 'driver_sha256': digest(Path(__file__)),
        'task_ids': [t['task_id'] for t in tasks], 'project_families': families,
        'public_catalog_paths': list(PUBLIC_CATALOGS),
        'contamination_audit': {'algorithm': 'UTF-8 byte 5-gram count-vector cosine',
            'threshold': 0.95, 'input': 'complete public user_request (goal or description for catalogs using those fields)',
            'on_violation': 'exclude related source from role data and report before generation; no replacement or score-driven selection',
            'upstream': 'owner-authorized realprojectdevv1 task identities preserved; authorship does not itself make role training labels'},
        'budgets': {'case_concurrency': 1, 'max_transitions_per_case': 200,
            'case_wall_seconds': 1800, 'total_wall_seconds': 21600,
            'supervisor_pending_resume_attempts': 0, 'native_transport_resume_attempts': 1, 'per_case_reruns': 0,
            'strong_generation': planner.public_dict(), 'rwkv_read_timeout_seconds': 300,
            'exhaustion': 'interrupt owned worker process group, preserve incomplete evidence; never completed',
            'wall_budget_basis': 'fresh run: official thinking Planner probe used 200.37 seconds; allow 1800 seconds per task for planning, stage reviews and RWKV execution; no stage or step count cap'},
        'role_data': {'target_role': 'selector_intent', 'other_roles_required': False,
            'coverage_scope_sha256': digest(ROUND / 'COVERAGE_SCOPE.json'),
            'all_nine_flags_reported': True, 'minimum_verified_menu_rows_for_training': 30,
            'minimum_distinct_selection_boundaries_for_training': 10,
            'fixed_split': 'existing sha256 project-family 80/10/10; nonempty train/dev/confirmation; no family renaming',
            'token_ids_complete_required': True,
            'label_authority': 'existing production extractor only; failed selections may enter independent review queue',
            'training_optimizer_steps_in_collection': 0,
            'next_training': 'only after current-role evidence gates; register exact admitted data/regression, trainer, initialization, optimizer, evaluation and resource budgets before optimizer execution'},
        'metrics': ['Strict / 12', 'completed / 12', 'mutation action count', 'termination per task',
            'action count', 'role boundaries', 'Selector qualified and review candidates', 'evidence gate gaps'],
        'source_policy': 'freeze throughout collection; no reference or private verifier feedback to model; no source changes or result-driven rescore',
        'holdout_accessed': False,
    }
    write(ROUND / 'REGISTRATION.json', registration)
    # Registration precedes the cross-catalog audit and every model request.
    pairs, catalog_meta = [], []
    for name in PUBLIC_CATALOGS:
        path = ROOT / name
        entries = json.loads(path.read_text())['tasks']
        catalog_meta.append({'path': name, 'sha256': digest(path), 'tasks': len(entries)})
        for task in tasks:
            for other in entries:
                request = next((other[k] for k in ('user_request', 'goal', 'description')
                    if isinstance(other.get(k), str) and other[k]), '')
                if not isinstance(request, str) or not request:
                    raise ValueError(f'public task missing request in {name}')
                pairs.append({'pilot': task['task_id'], 'catalog': name,
                    'task_id': other.get('task_id', other.get('id')),
                    'cosine': byte_5gram_cosine(task['user_request'], request)})
    audit = {'registration_sha256': digest(ROUND / 'REGISTRATION.json'),
        'catalogs': catalog_meta, 'comparisons': len(pairs),
        'pairs': pairs, 'violations': [p for p in pairs if p['cosine'] >= 0.95],
        'project_family_splits': {key: split_project_family(value) for key, value in families.items()},
        'source_locators': [{'public_task_path': str(BUNDLE / 'tasks.json'), 'task_id': t['task_id']} for t in tasks], 'holdout_accessed': False,
        'limitation': 'visible public catalogs only; no claim about hidden/model-pretraining contamination'}
    write(ROUND / 'PUBLIC_SOURCE_AUDIT.json', audit)
    assert not audit['violations'], 'cross-catalog overlap requires exclusion before collection'
    role_health = benchmark._preflight_goal_role_runtimes(roles)
    with requests.Session() as session:
        session.trust_env = False
        response = session.get(selector.base_url.rstrip('/') + '/healthz', timeout=(5, 20))
        response.raise_for_status()
        selector_health = response.json()
    assert selector_health['runtime_identity'] == selector.runtime_identity()
    client = OpenAICompatibleSupervisorClient(settings=planner)
    try:
        planner_health = client.health()
    finally:
        client.close()
    write(OUTPUT / 'runtime_doctor.json', {'roles': role_health, 'selector': selector_health,
        'planner': planner_health, 'planner_settings': planner.public_dict()})
    assert planner_health['available'] and planner_health['model_present'], planner_health
    source = benchmark._source_tree_manifest(ROOT)
    write(OUTPUT / 'source_tree_manifest.json', source)
    profiles = {name: {'profile_id': value.state_profile_id, 'profile_sha256': value.state_profile_sha256,
        'model_sha256': value.model_sha256} for name, value in roles.items()}
    profiles['selector_intent'] = {'profile_id': selector.state_profile_id,
        'profile_sha256': selector.state_profile_sha256, 'model_sha256': selector.model_sha256}
    contract = validate_collection_contract({'mode': 'role_stage', 'stage_id': 'selector_handoff_r1',
        'target_role': 'selector_intent', 'profiles': profiles})
    write(OUTPUT / 'RUN_PROTOCOL.json', {
        'schema_version': 'rwkv-lh.round-run-protocol.v1', 'round': ROUND.name + '-all_zero',
        'architecture': STATEFUL_GOAL_LOOP_ARCHITECTURE, 'suite': SUITE,
        'selected_case_count': len(tasks), 'selected_case_ids': registration['task_ids'],
        'source_resources': [dict(suite=SUITE, role=role, path=str(BUNDLE / path), sha256=digest(BUNDLE / path))
            for role, path in (('visible_tasks', 'tasks.json'), ('hidden_acceptance', 'acceptance.json'))],
        'code': {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'source_tree_manifest_sha256': canonical_sha(source), 'source_tree_file_count': len(source),
            'runner_sha256': digest(Path(benchmark.__file__))},
        'registration_sha256': digest(ROUND / 'REGISTRATION.json'),
        'role_data_scope_sha256': digest(ROUND / 'COVERAGE_SCOPE.json'),
        'role_data_collection': contract, 'budgets': registration['budgets'],
        'goal_role_runtimes': benchmark._goal_role_runtime_identities(roles),
        'independent_selector': {'enabled': True, 'runtime_identity': selector.runtime_identity()},
        'supervisor': {'enabled': True, 'settings': planner.public_dict(), 'health': planner_health},
        'sampling': benchmark.LongHorizonModel._SAMPLING.to_dict(),
        'stateful_goal': benchmark.stateful_goal_protocol_metadata(enabled=True, strong_planner_available=True),
        'tokenizer': {'path': str(benchmark.VOCAB_PATH), 'sha256': digest(benchmark.VOCAB_PATH)},
        'non_intervention': {'hidden_acceptance_available_during_generation': False, 'final_output': 'byte-exact raw RWKV response'},
    })
    print(json.dumps({'prepared': True, 'comparisons': len(pairs), 'max_similarity': max(p['cosine'] for p in pairs),
        'family_splits': audit['project_family_splits'], 'planner': planner.model, 'selector': selector.model}), flush=True)


def assert_frozen(benchmark, roles, planner, selector):
    registration = json.loads((ROUND / 'REGISTRATION.json').read_text())
    protocol = json.loads((OUTPUT / 'RUN_PROTOCOL.json').read_text())
    assert digest(Path(__file__)) == registration['driver_sha256']
    assert digest(ROUND / 'REGISTRATION.json') == protocol['registration_sha256']
    assert benchmark._source_tree_manifest(ROOT) == json.loads((OUTPUT / 'source_tree_manifest.json').read_text())
    assert benchmark._goal_role_runtime_identities(roles) == protocol['goal_role_runtimes']
    assert planner.public_dict() == protocol['supervisor']['settings']
    assert selector.runtime_identity() == protocol['independent_selector']['runtime_identity']
    verify_bundle()


def case(task_id):
    benchmark, roles, planner, selector = configure()
    assert_frozen(benchmark, roles, planner, selector)
    _, tasks = verify_bundle()
    task = next(t for t in tasks if t['task_id'] == task_id)
    acceptance = json.loads((BUNDLE / 'acceptance.json').read_text())['cases'][task_id]
    print(json.dumps({'case_started': task_id, 'at': datetime.now(timezone.utc).isoformat()}), flush=True)
    result = benchmark.run_case(task, acceptance, OUTPUT, max_transitions=200,
        supervisor_mode='openai', supervisor_strategy='goal_stages', independent_selector=True,
        supervisor_pending_resume_attempts=0, native_transport_resume_attempts=1, stateful_goal=True)
    write(OUTPUT / f'{task_id}.result.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def collect():
    benchmark, roles, planner, selector = configure()
    assert_frozen(benchmark, roles, planner, selector)
    registration = json.loads((ROUND / 'REGISTRATION.json').read_text())
    started = time.monotonic()
    completions = []
    write(ROUND / 'STARTED.json', {'at': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
        'registration_sha256': digest(ROUND / 'REGISTRATION.json')})
    for task_id in registration['task_ids']:
        budget = min(1800, 21600 - (time.monotonic() - started))
        if budget <= 0:
            completions.append({'task_id': task_id, 'started': False, 'reason': 'preregistered_total_wall_budget_exhausted'})
            continue
        case_started = time.monotonic()
        with (ROUND / f'{task_id}.log').open('x') as log:
            child = subprocess.Popen([sys.executable, str(Path(__file__)), 'case', '--task-id', task_id],
                cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            error = None
            try:
                code = child.wait(timeout=budget)
            except subprocess.TimeoutExpired:
                error = 'preregistered_wall_budget_exhausted'
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
                code = child.returncode
        record = {'task_id': task_id, 'exit_code': code, 'error': error, 'wall_seconds': time.monotonic()-case_started,
            'result_recorded': (OUTPUT / f'{task_id}.result.json').exists()}
        completions.append(record)
        write(ROUND / f'{task_id}.completion.json', record)
        print(json.dumps(record), flush=True)
    write(ROUND / 'COMPLETION.json', {'cases': completions, 'wall_seconds': time.monotonic()-started,
        'source_unchanged': benchmark._source_tree_manifest(ROOT) == json.loads((OUTPUT / 'source_tree_manifest.json').read_text()),
        'optimizer_steps': 0, 'ended_at': datetime.now(timezone.utc).isoformat()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'collect', 'case'))
    parser.add_argument('--task-id')
    args = parser.parse_args()
    {'prepare': prepare, 'collect': collect, 'case': lambda: case(args.task_id)}[args.phase]()
