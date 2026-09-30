"""Immutable Project role regression using original Native full-prefix token IDs.

This is offline State comparison. Contract/reference agreement never substitutes
for the separate production Native Agent run and independent project acceptance.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import time

from . import statetune_core as core, project_training_freeze as freeze
from .goal_state_protocols.role_trace_dataset_v1 import _source_path
from .harness import ActionHarness
from .model_io import JSON_CALL_STOP_SUFFIXES, ModelIOError, canonical_digest
from .project_contracts import digest
from .project_format_adapter import parse_role_call
from .project_output_validation import normalize_role_output, validate_role_output
from .project_runtime import role_definitions
from .project_decoder import build_role_decoder
from .runtime.structured_output import decoder_receipt, state_output_token_ids
from .project_token_data import _decode_generated_rwkv
from .project_training_labels import load_reviewed_candidates
from .runtime.openai_compat import OpenAICompatibleRWKVClient
from .runtime.protocol import TextCompletionRequest, RWKVOutcomeUnknownError, RWKVTransportError, RWKVProtocolError, RWKVHTTPError
from .runtime.settings import RuntimeSettings
from .statetune_data import sealed, _member, _protocol, normalize_row
from .statetune_native_runtime import verify_project_source
from .token_budget import tokenizer

PLAN_SCHEMA = 'rwkv-lh.statetune-project-evaluation-plan.v2'
RUN_SCHEMA = 'rwkv-lh.statetune-project-evaluation-run.v2'
SPLITS = ('dev', 'confirmation')
METRICS = ['role_contract_validity', 'reference_match', 'transport_failures', 'unknown_outcomes', 'budget_failures', 'not_run']
SAMPLING = {'temperature', 'top_p', 'top_k', 'presence_penalty', 'frequency_penalty', 'penalty_decay', 'seed'}
ROLES = ('project_decision', 'project_executor')


def validate_plan(plan):
    core.require(plan.get('schema_version') == PLAN_SCHEMA and plan.get('role') in ROLES,
                 'current Project evaluation plan required')
    expected_decoder = build_role_decoder(role_definitions(plan['role'].removeprefix('project_'), ActionHarness()))
    core.require(plan.get('decoder_contract_sha256') == expected_decoder['contract_sha256'],
                 'Project evaluation requires the current production constrained decoder')
    core.require((plan.get('input_protocol'), plan.get('protocol_sha256')) == _protocol(plan['role']),
                 'Project evaluation protocol differs')
    fingerprint = plan.get('regression_fingerprint')
    core.require(isinstance(fingerprint, str) and len(fingerprint) == 64
                 and all(c in '0123456789abcdef' for c in fingerprint), 'invalid regression fingerprint')
    core.require(plan.get('metrics') == METRICS
        and plan.get('agent_metrics') == ['strict', 'completed', 'mutation', 'termination_reasons']
        and plan.get('retention_rule') == 'role_qualification_then_separate_agent_acceptance',
        'Project role/Agent metrics and retention rule differ')
    thresholds = plan.get('thresholds', {})
    core.require(set(thresholds) == {'role_contract_validity', 'reference_match', 'max_transport_failures',
                                   'max_regressions', 'max_budget_failures'}, 'Project thresholds differ')
    for key in ('role_contract_validity', 'reference_match'):
        value = thresholds[key]
        core.require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= 1,
                     'invalid Project accuracy threshold')
    core.require(all(type(thresholds[key]) is int and thresholds[key] == 0
        for key in ('max_transport_failures', 'max_regressions', 'max_budget_failures')),
        'qualification requires zero transport/budget failures and regressions')
    core.require(type(plan.get('context_tokens')) is int and type(plan.get('max_output_tokens')) is int
                 and 0 < plan['max_output_tokens'] < plan['context_tokens'], 'invalid Project context/output budget')
    seconds = plan.get('max_seconds_per_arm')
    core.require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0,
                 'invalid Project wall time budget')
    sampling = plan.get('sampling', {})
    core.require(set(sampling) == SAMPLING and type(sampling['seed']) is int
                 and type(sampling['top_k']) is int
                 and all(type(sampling[k]) in (int, float) and math.isfinite(sampling[k])
                         for k in SAMPLING - {'seed', 'top_k'}), 'all Project sampling parameters must be explicit')
    _request([0], plan, 'sampling-validation').payload('validation', sampler_mode='native')


def _request(ids, plan, request_id):
    return TextCompletionRequest(prompt=list(ids), max_tokens=plan['max_output_tokens'],
        **plan['sampling'], stop=(), add_special_tokens=False,
        return_token_ids=True, request_id=request_id)


def validate_arms(arms, plan):
    validate_plan(plan)
    core.require(set(arms) == {'zero', 'candidate'}, 'Project comparison requires both arms')
    zero, candidate = arms['zero'], arms['candidate']
    core.require((zero.state_profile_id, zero.state_profile_sha256) == ('zero', '0' * 64)
        and candidate.state_profile_id not in ('', 'zero') and candidate.state_profile_sha256 != '0' * 64
        and len(candidate.state_profile_sha256) == 64
        and all(c in '0123456789abcdef' for c in candidate.state_profile_sha256), 'explicit zero and exported State required')
    ignored = {'state_profile_id', 'state_profile_sha256'}
    core.require({k: v for k, v in asdict(zero).items() if k not in ignored}
        == {k: v for k, v in asdict(candidate).items() if k not in ignored}, 'Project arms differ beyond State')
    core.require(zero.backend_profile == 'vllm-rwkv-native' and zero.retry_attempts == 1
        and zero.state_profile_delivery == 'request' and zero.max_model_len == plan['context_tokens']
        and zero.return_token_ids is True and len(zero.model_sha256) == 64,
        'Project arms require native backend, token echoes, one attempt and exact model/context')


@dataclass(frozen=True)
class ProjectCase:
    row: dict


def prepare_cases(reference, *, plan, settings):
    """Verify frozen proof and re-extract only dev/confirmation source boundaries."""
    validate_plan(plan)
    manifest = sealed(reference); root = Path(reference['path']).parent
    proof = json.loads(_member(root, manifest['project_freeze']).read_text())
    core.require(proof.get('schema_version') == freeze.PROOF_SCHEMA
                 and proof.get('generator_sha256') == core.sha256_file(freeze.__file__), 'current Project publisher required')
    reg_ref = proof['registration']; registration = sealed(reg_ref)
    freeze._registration(registration, reg_ref)
    core.require(manifest == freeze._manifest(registration, reg_ref, proof, manifest['project_freeze']),
                 'Project evaluation dataset differs from publisher proof')
    core.require((registration['role'], registration['model_sha256'], registration['context_tokens'])
        == (plan['role'], settings.model_sha256, plan['context_tokens'])
        and settings.max_model_len == plan['context_tokens'], 'Project regression model/role/context differs')
    registry = _source_path(freeze.REGRESSION_ROOT / plan['role'])
    core.require(proof['registry_index']['path'] == str(registry / 'index.json'), 'single immutable Project registry required')
    index = sealed(proof['registry_index'])
    core.require(index['schema_version'] == freeze.INDEX_SCHEMA and index['role'] == plan['role']
        and index['fingerprint'] == plan['regression_fingerprint'] == manifest['regression']['fingerprint']
        and index['regression_sha256'] == manifest['regression']['sha256'], 'Project regression identity changed')
    core.verify_file(registry / 'regression.json', index['regression_sha256'])
    path = _member(root, manifest['regression']); regression = json.loads(path.read_text())
    core.require(regression.get('schema_version') == freeze.REGRESSION_SCHEMA
        and digest({k: v for k, v in regression.items() if k != 'fingerprint'}) == index['fingerprint']
        and (regression['input_protocol'], regression['protocol_sha256']) == _protocol(plan['role'])
        and regression['role'] == plan['role'] and regression['model_sha256'] == settings.model_sha256
        and regression['context_tokens'] == plan['context_tokens'], 'Project fixed regression content differs')
    for ref in index['provenance_files']: core.verify_file(_source_path(Path(ref['path'])), ref['sha256'])
    core.require(set(regression['samples_by_split']) == set(SPLITS), 'fixed evaluation splits differ')
    rows = [r for split in SPLITS for r in regression['samples_by_split'][split]]
    core.require(all(len(regression['samples_by_split'][s]) == manifest['counts'][s] > 0 for s in SPLITS),
                 'Project fixed evaluation counts differ')
    core.require(sorted((freeze._member(r) for r in rows), key=lambda m: m['sample_id']) == index['members'],
                 'Project evaluation membership changed')
    rebuilt = load_reviewed_candidates([r['review_reference'] for r in rows])
    core.require(rebuilt == rows, 'Project evaluation differs from original independently reviewed boundaries')
    cases = []
    for row in rows:
        normalize_row(row, role=plan['role'], model_sha256=settings.model_sha256, context_tokens=plan['context_tokens'],
                      vocab_size=65536, bos_token_id=0, expected_split=row['split'])
        core.require(len(row['input_token_ids']) + plan['max_output_tokens'] <= plan['context_tokens'],
                     'complete Project evaluation input/output exceeds context; no truncation or exclusion')
        cases.append(ProjectCase(row))
    validate_cases(cases, plan)
    core.verify_file(path, manifest['regression']['sha256'])
    return manifest, cases


def validate_cases(cases, plan):
    core.require(bool(cases) and len({c.row['sample_id'] for c in cases}) == len(cases)
        and {c.row['split'] for c in cases} == set(SPLITS)
        and all(c.row['role'] == plan['role'] for c in cases), 'empty, duplicate or mismatched Project regression')
    core.require(all(len(c.row['input_token_ids']) + plan['max_output_tokens'] <= plan['context_tokens'] for c in cases),
                 'complete Project regression exceeds context')


def _validated(raw, row):
    role = row['role'].removeprefix('project_'); definitions = role_definitions(role, ActionHarness())
    command, framing = parse_role_call(raw, role=role, payload=row['input'])
    accepted, normalization = normalize_role_output(role, command, definitions)
    validate_role_output(role, row['input'], accepted, definitions)
    return accepted.to_wire_dict()


def _reference_identity(wire, role):
    params = dict(wire['params'])
    if role == 'project_decision': params.pop('reason', None)
    return {'function': wire['function'], 'params': params}


def evaluate_arm(cases, client, *, plan, run_id, arm, record, clock=time.monotonic, halted=False):
    validate_plan(plan); validate_cases(cases, plan)
    decoder = build_role_decoder(role_definitions(plan['role'].removeprefix('project_'), ActionHarness()))
    start = clock()
    results = {s: {'total': 0, 'contract_valid': 0, 'reference_correct': 0, 'transport_failures': 0,
        'unknown_outcomes': 0, 'budget_failures': 0, 'not_run': 0, 'contract_correctness': {},
        'reference_correctness': {}} for s in SPLITS}
    for index, case in enumerate(cases):
        row = case.row; result = results[row['split']]; sample = row['sample_id']
        result['total'] += 1
        result['contract_correctness'][sample] = result['reference_correctness'][sample] = False
        request_id = f'{run_id}:{arm}:{index}:{sample}'
        entry = {'event': 'project_case_evaluated', 'request_id': request_id, 'arm': arm, 'sample_id': sample,
                 'split': row['split'], 'source_operation_id': row['source_operation_id']}
        if halted or clock() - start >= plan['max_seconds_per_arm']:
            result['not_run'] += 1
            entry.update(status='not_run', reason='unknown_outcome' if halted else 'registered_wall_time_budget')
        else:
            request = _request(row['input_token_ids'], plan, request_id)
            # A journal failure must stop before any network generation.
            record({'event': 'project_case_started', 'request_id': request_id, 'arm': arm, 'sample_id': sample})
            try:
                response = client.token_completion(request, record=record, decoder=decoder)
                try:
                    consumed = state_output_token_ids(response.metadata.get('token_ids'), response.finish_reason, decoder)
                except ValueError as exc:
                    raise RWKVProtocolError('invalid Project evaluation EOS boundary') from exc
                if (response.metadata.get('decoder') != decoder_receipt(decoder)
                        or response.metadata.get('state_token_ids') != consumed):
                    raise RWKVProtocolError('Project evaluation decoder attestation mismatch')
            except RWKVOutcomeUnknownError as exc:
                result['transport_failures'] += 1; result['unknown_outcomes'] += 1; halted = True
                entry.update(status='unknown', error_type=type(exc).__name__)
            except (RWKVTransportError, RWKVProtocolError, RWKVHTTPError) as exc:
                result['transport_failures'] += 1
                entry.update(status='transport_failed', error_type=type(exc).__name__)
            else:
                entry.update(raw_output=response.content, generated_token_ids=response.metadata['token_ids'],
                             finish_reason=response.finish_reason)
                if response.finish_reason == 'length':
                    result['budget_failures'] += 1; entry.update(status='output_budget_exhausted')
                elif response.finish_reason != 'stop':
                    result['transport_failures'] += 1; entry.update(status='unrecognized_finish_reason')
                else:
                    try:
                        decoded = _decode_generated_rwkv(tokenizer(), response.metadata['token_ids'], response.finish_reason)
                        core.require(decoded == response.content or any(decoded == response.content + stop
                            for stop in JSON_CALL_STOP_SUFFIXES), 'generated token text differs from original response')
                    except ValueError as exc:
                        result['transport_failures'] += 1
                        entry.update(status='token_response_mismatch', error_type=type(exc).__name__)
                    else:
                        try: command = _validated(response.content, row)
                        except (ValueError, ModelIOError, KeyError, TypeError) as exc:
                            entry.update(status='contract_rejected', error_type=type(exc).__name__, error=str(exc))
                        else:
                            correct = _reference_identity(command, row['role']) == _reference_identity(
                                _validated(row['target_text'][:-len(JSON_CALL_STOP_SUFFIXES[0])], row), row['role'])
                            result['contract_valid'] += 1; result['reference_correct'] += int(correct)
                            result['contract_correctness'][sample] = True; result['reference_correctness'][sample] = correct
                            entry.update(status='contract_valid', command=command, reference_match=correct)
        record(entry)
    elapsed = clock() - start
    for value in results.values():
        value.update(role_contract_validity=value['contract_valid'] / value['total'],
                     reference_match=value['reference_correct'] / value['total'],
                     budget_exceeded=elapsed >= plan['max_seconds_per_arm'])
    return results


def compare_arms(arms, plan):
    validate_plan(plan)
    core.require(set(arms) == {'zero', 'candidate'} and all(set(a) == set(SPLITS) for a in arms.values()),
                 'both complete Project comparison arms required')
    regressions = {s: {} for s in SPLITS}
    for split in SPLITS:
        zero, candidate = arms['zero'][split], arms['candidate'][split]
        core.require(zero['total'] == candidate['total'] > 0, 'Project comparison counts differ')
        for metric in ('contract_correctness', 'reference_correctness'):
            core.require(set(zero[metric]) == set(candidate[metric]) and len(zero[metric]) == zero['total'],
                         'Project comparison sample identities differ')
            regressions[split][metric] = [key for key in zero[metric] if zero[metric][key] and not candidate[metric][key]]
    def qualified(arm):
        return all(not any(v[k] for k in ('transport_failures', 'unknown_outcomes', 'budget_failures', 'not_run', 'budget_exceeded'))
            and all(v[m] >= plan['thresholds'][m] for m in ('role_contract_validity', 'reference_match'))
            for v in arms[arm].values())
    zero_ok = qualified('zero')
    comparison_complete = all(not any(v[k] for k in
        ('transport_failures', 'unknown_outcomes', 'not_run', 'budget_exceeded'))
        for arm in arms.values() for v in arm.values())
    candidate_ok = comparison_complete and qualified('candidate') and not any(v for s in regressions.values() for v in s.values())
    improved = any(arms['candidate'][s][m] > arms['zero'][s][m] for s in SPLITS
                   for m in ('role_contract_validity', 'reference_match'))
    return {'zero_qualified': zero_ok, 'candidate_qualified': candidate_ok, 'regressions': regressions,
        'preferred_state': 'candidate' if candidate_ok and (improved or not zero_ok) else 'zero' if zero_ok else None,
        'comparison_complete': comparison_complete, 'retained': False,
        'agent_evaluation_status': 'not_run', 'evaluation_mode': 'original_full_token_prefix'}


def validate_training_binding(registration, plan, candidate):
    trained = sealed(registration['training_result']); training = sealed(trained['registration'])
    core.require(type(trained['optimizer_steps']) is int and trained['optimizer_steps'] > 0
        and trained.get('serving_loader_verified') is True and trained['run_id'] == candidate.state_profile_id
        and trained['role'] == training['role'] == plan['role'] and training['run_id'] == trained['run_id']
        and trained['output_state']['sha256'] == candidate.state_profile_sha256
        and training['evaluation_registration'] == registration['evaluation_registration']
        and training['dataset'] == registration['dataset'] and training['base_sha256'] == candidate.model_sha256
        and training['context_tokens'] == plan['context_tokens']
        and training['source_manifest_sha256'] == registration['source_manifest']['sha256'],
        'Project candidate model or identity differs from original registered optimizer run')
    core.verify_file(trained['output_state']['path'], trained['output_state']['sha256'])
    profile = sealed(trained['output_profile']); runtime = sealed(training['runtime'])
    core.require(runtime['source_manifest'] == registration['source_manifest'], 'training runtime source differs')
    artifact = Path(runtime['model_artifact']['path'])
    model = sealed({'path': str(artifact / 'manifest.json'), 'sha256': runtime['model_artifact']['manifest_sha256']})
    core.require(model['source']['sha256'] == candidate.model_sha256, 'Project actual model source differs')
    core.verify_file(artifact / 'model.safetensors', model['output']['weights_sha256'])
    core.verify_file(artifact / 'rwkv_vocab_v20230424.txt', model['output']['vocab_sha256'])
    from .inference.vllm_rwkv_state_profiles_v1 import RWKV7_STATE_PROFILE_MANIFEST_SCHEMA
    core.require(profile == {'schema_version': RWKV7_STATE_PROFILE_MANIFEST_SCHEMA,
        'model_artifact': str(artifact), 'model_revision': runtime['engine']['revision'], 'default_profile': 'zero',
        'profiles': [{'id': candidate.state_profile_id, 'format': 'rwkv-peft-time-state.v1', **trained['output_state']}]},
        'Project exported serving profile differs from trained State/model')
    from .statetune_training import validate_compatibility
    from .inference.native_weight_identity import identity_from_validation
    compatibility = sealed(training['compatibility_registration'])
    result = sealed(training['compatibility_result'])
    validate_compatibility(training, compatibility, result,
        registration_sha256=training['compatibility_registration']['sha256'])
    weight_identity = identity_from_validation(result)
    core.require(trained.get('serving_weight_identity') == weight_identity,
                 'Project trained serving weight identity differs from numerical evidence')
    return trained, training, {**runtime, 'serving_weight_identity': weight_identity}


def verify_serving(client, runtime, source, *, record):
    """Bind current resident weights to the sealed numerical run, without generation."""
    identity = {'schema_version': 'rwkv-lh.native-source-identity.v1',
        'engine_manifest_sha256': runtime['engine']['manifest_sha256'], 'project_manifest_sha256': source['sha256']}
    value, _, _ = client._request_json('GET', '/capabilities?verify_loaded_weights=true')
    record({'event': 'serving_capabilities_checked', 'raw_response': value})
    core.require(value.get('server_build', '').endswith('+native.' + canonical_digest(identity))
        and value.get('model') == client.settings.model and value.get('max_model_len') == client.settings.max_model_len
        and value.get('recurrent_state', {}).get('create') is True and not value.get('error'),
        'Project serving source/model/context differs or Native service is not ready')
    from .inference.native_weight_identity import validate_loaded_identity
    expected = validate_loaded_identity(runtime.get('serving_weight_identity'))
    actual = validate_loaded_identity(value.get('loaded_weight_identity'))
    core.require(actual == expected, 'Project serving loaded weights differ from registered numerical weights')
    from .runtime.native_state import EXACT_TOKEN_INPUT_PROTOCOL
    from .runtime.structured_output import DECODER_PROTOCOL, DECODER_BACKEND
    core.require(value.get('recurrent_state', {}).get('exact_token_input_protocol') == EXACT_TOKEN_INPUT_PROTOCOL
        and value.get('structured_output', {}).get('protocol') == DECODER_PROTOCOL
        and value.get('structured_output', {}).get('backend') == DECODER_BACKEND,
        'Project role evaluation requires attested exact tokens and constrained decoding')


def run_evaluation(reference, output, *, source_root):
    from .statetune_training import _atomic_json
    registration = sealed(reference)
    core.require(registration.get('schema_version') == RUN_SCHEMA, 'current Project evaluation run required')
    plan = sealed(registration['evaluation_registration']); validate_plan(plan)
    core.require(registration.get('role') == plan['role'], 'Project evaluation run role differs')
    # Credentials are supplied by environment, never frozen in public artifacts.
    sensitive = {'api_key', 'cf_access_client_id', 'cf_access_client_secret', 'proxy_url'}
    for value in registration['arms'].values():
        core.require(not sensitive.intersection(value), 'evaluation registration must not contain credentials or proxies')
        core.require('://' in value['base_url'] and '@' not in value['base_url']
                     and '?' not in value['base_url'], 'evaluation endpoint must not contain credentials')
    arms = {key: RuntimeSettings(api_key=os.environ.get('RWKV_API_KEY', ''), **value)
            for key, value in registration['arms'].items()}
    validate_arms(arms, plan)
    from .inference.vllm_rwkv_state_profiles_v1 import _PROFILE_ID_PATTERN
    core.require(isinstance(registration['run_id'], str) and _PROFILE_ID_PATTERN.fullmatch(registration['run_id']),
                 'unsafe Project evaluation run id')
    output = _source_path(Path(output).absolute())
    core.require(output == Path(registration['ledger_root']).absolute() / registration['run_id'],
                 'Project evaluation requires registered immutable run directory')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(reference['path'], output / 'REGISTRATION.json')
    core.verify_file(output / 'REGISTRATION.json', reference['sha256'])
    report = {'schema_version': RUN_SCHEMA, 'registration': dict(reference), 'status': 'running',
        'started_at': datetime.now(timezone.utc).isoformat(), 'retained': False, 'agent_evaluation_status': 'not_run'}
    log = output / 'events.jsonl'
    def record(value):
        with log.open('a') as handle:
            handle.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(), **value}, ensure_ascii=False, allow_nan=False) + '\n')
            handle.flush(); os.fsync(handle.fileno())
    record({'event': 'project_evaluation_started'})
    _atomic_json(output / 'RESULT.json', report)
    try:
        verify_project_source(registration['source_manifest'], source_root)
        candidate = arms['candidate']
        trained, training, runtime = validate_training_binding(registration, plan, candidate)
        dataset, cases = prepare_cases(registration['dataset'], plan=plan, settings=arms['zero'])
        report['arms'] = {}; halted = False
        for arm in ('zero', 'candidate'):
            verify_project_source(registration['source_manifest'], source_root)
            client = OpenAICompatibleRWKVClient(arms[arm])
            try:
                verify_serving(client, runtime, registration['source_manifest'], record=record)
                report['arms'][arm] = evaluate_arm(cases, client, plan=plan, run_id=registration['run_id'],
                    arm=arm, record=record, halted=halted)
                verify_serving(client, runtime, registration['source_manifest'], record=record)
            finally: client.close()
            halted = halted or any(v['unknown_outcomes'] for v in report['arms'][arm].values())
            _atomic_json(output / 'RESULT.json', report)
        verify_project_source(registration['source_manifest'], source_root)
        validate_training_binding(registration, plan, candidate)
        _member(Path(registration['dataset']['path']).parent, dataset['regression'])
        report.update(compare_arms(report['arms'], plan), status='evaluated')
        if trained['status'] != 'candidate':
            report.update(candidate_qualified=False, preferred_state='zero' if report['zero_qualified'] else None,
                          candidate_disqualification='optimizer_run_did_not_complete')
    except BaseException as exc:
        report.update(status='interrupted' if isinstance(exc, (KeyboardInterrupt, SystemExit)) else 'failed',
                      error_type=type(exc).__name__, error=str(exc), retained=False)
        record({'event': 'project_evaluation_failed', 'error_type': type(exc).__name__})
        raise
    finally:
        report.update(finished_at=datetime.now(timezone.utc).isoformat(), log_sha256=core.sha256_file(log))
        _atomic_json(output / 'RESULT.json', report)
    return report
