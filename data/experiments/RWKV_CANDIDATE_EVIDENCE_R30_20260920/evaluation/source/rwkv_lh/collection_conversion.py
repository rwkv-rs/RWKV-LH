"""Convert bound external coding goals into current direct Agent task inputs.

External assistant/tool turns stay private. This is task preparation, never an
adapter that relabels external completions as native StateTune targets.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from . import model_io
from .collection_acceptance import load_contract
from .ultradata import _json
from .workspace_snapshot import tree_identity, copy_verified_workspace

CODING_KINDS = frozenset({'bug_fix', 'feature_implementation', 'test_feedback_repair',
                           'repository_understanding', 'code_verification', 'standalone_implementation'})


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def initial_goal(row, source_kind):
    if source_kind == 'registered_project':
        goal = row.get('request')
    elif source_kind == 'sft_agent':
        messages = row.get('messages')
        if not isinstance(messages, list) or not messages:
            raise ValueError('source messages required')
        if sum(isinstance(message, dict) and message.get('role') == 'user' for message in messages) != 1:
            raise ValueError('multi-turn goals require explicit episode reconstruction')
        users = []
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError('malformed source message')
            role = message.get('role')
            if role in ('assistant', 'tool'):
                break
            if role == 'user':
                users.append(message.get('content'))
            elif role not in ('system', 'developer'):
                raise ValueError('unsupported initial source role')
        if len(users) != 1:
            raise ValueError('one unambiguous initial user goal required')
        goal = users[0]
    else:
        raise ValueError('unsupported source adapter')
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError('complete text goal required; multimodal/partial tasks need reconstruction')
    # Some releases put source-harness instructions inside the user turn.
    # Preserve the original evidence; never regex-strip it into a guessed goal.
    # This is a conservative known-signature guard, not semantic certification.
    external_protocol_markers = (
        'complete_task_and_submit_final_output',
        'every response must contain exactly one action',
        'the action must be enclosed in triple backticks',
    )
    normalized = ' '.join(goal.casefold().split())
    if any(marker in normalized for marker in external_protocol_markers):
        raise ValueError('embedded external harness protocol requires reviewed goal reconstruction')
    return goal


def _verified_bytes(path, expected):
    raw = Path(path).read_bytes()
    if not re.fullmatch('[0-9a-f]{64}', str(expected)) or digest_bytes(raw) != expected:
        raise ValueError('bound source/evidence digest mismatch')
    return raw



def mapped_request(goal, kind, original_root=None):
    request = goal
    mapping = None
    if kind == 'sft_agent':
        path = PurePosixPath(original_root)
        if not path.is_absolute() or '..' in path.parts or str(path) != original_root or '\\' in original_root:
            raise ValueError('unambiguous source workspace root required')
        mapping = {'source_root': original_root, 'destination': 'current workspace root'}
        request += ('\n\n执行环境映射：原任务的目录 ' + json.dumps(original_root, ensure_ascii=False)
                    + ' 对应当前工作区根目录（相对路径 .）。工具调用使用当前提供的工具定义。')
    return request, mapping

def convert_task(source, binding, output):
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    raw = _verified_bytes(source, binding['source_sha256'])
    row = _json(raw)
    if not isinstance(row, dict):
        raise ValueError('source row must be an object')
    kind = binding['source_kind']
    source_id = row.get('uuid') if kind == 'sft_agent' else row.get('id')
    if not isinstance(source_id, str) or not source_id or source_id != binding['source_id']:
        raise ValueError('source task identity differs')
    revision = binding['dataset_revision']
    revision_pattern = '[0-9a-f]{40}' if kind == 'sft_agent' else '[0-9a-f]{64}'
    if not re.fullmatch(revision_pattern, str(revision)):
        raise ValueError('immutable dataset commit or project source manifest digest required')
    if binding['task_kind'] not in CODING_KINDS:
        raise ValueError('explicit coding task kind required')
    goal = initial_goal(row, kind)
    workspace = Path(binding['workspace']).resolve(strict=True)
    if source == workspace or workspace in source.parents:
        raise ValueError('external trajectory is inside visible workspace')
    if workspace == output or workspace in output.parents or output in workspace.parents:
        raise ValueError('conversion output overlaps original workspace')
    before = tree_identity(workspace, exclude_git=True, allow_links=False)
    if before != binding['environment_tree']:
        raise ValueError('initial environment differs from reconstruction binding')
    evidence = binding['reconstruction_evidence']
    evidence_raw = _verified_bytes(evidence['path'], evidence['sha256'])
    acceptance_raw = _verified_bytes(binding['acceptance_path'], binding['acceptance_sha256'])
    for private in (Path(evidence['path']).resolve(), Path(binding['acceptance_path']).resolve()):
        if private == workspace or workspace in private.parents:
            raise ValueError('private reconstruction/acceptance is visible to the model')
    load_contract(binding)
    calls, seconds = binding['max_calls'], binding['max_seconds']
    import math
    if type(calls) is not int or calls < 1 or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('explicit positive task budgets required')
    request, mapping = mapped_request(goal, kind, binding.get('original_workspace_root'))
    output.mkdir(parents=True)
    private = output/'private';private.mkdir()
    (private/'source.json').write_bytes(raw)
    (private/'reconstruction_evidence').write_bytes(evidence_raw)
    (private/'acceptance.json').write_bytes(acceptance_raw)
    converted_workspace = output/'workspace'
    copy_verified_workspace(workspace, converted_workspace, audit_path=output/'ENVIRONMENT_COPY.json')
    copied = tree_identity(converted_workspace, allow_links=False)
    if copied != before:
        raise ValueError('copied initial environment differs')
    task_id = 'CODING-' + binding['source_sha256'][:24]
    item = {'source_id': kind+'@'+revision+'/'+source_id,
            'source_path': str(private/'source.json'), 'source_sha256': binding['source_sha256'],
            'environment_sha256': digest_bytes(json.dumps(copied, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()),
            'acceptance_path': str(private/'acceptance.json'), 'acceptance_sha256': binding['acceptance_sha256'],
            'coding_task_kind': binding['task_kind'],
            'job': {'task_id': task_id, 'request': request, 'workspace': str(converted_workspace),
                    'output_dir': str(output/'run'), 'tool_scope': 'coding', 'max_calls': calls, 'max_seconds': seconds}}
    record = {'source_kind': kind, 'source_id': source_id, 'dataset_revision': revision,
              'revision_kind': 'dataset_commit' if kind == 'sft_agent' else 'source_manifest_sha256',
              'source_sha256': binding['source_sha256'], 'binding': binding,
              'original_goal_sha256': digest_bytes(goal.encode()),
              'converted_goal_sha256': digest_bytes(request.encode()), 'workspace_mapping': mapping,
              'source_assistant_and_tools_in_model_input': False,
              'training_admitted': False, 'protocol': model_io.MODEL_COMMAND_NORMALIZER_VERSION,
              'protocol_module_sha256': digest_bytes(Path(model_io.__file__).read_bytes()),
              'converter_sha256': digest_bytes(Path(__file__).read_bytes()),
              'role': 'task_preparation_not_training', 'complete': True}
    (output/'CONVERSION.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
    item['conversion_path'] = str(output/'CONVERSION.json')
    item['conversion_sha256'] = digest_bytes((output/'CONVERSION.json').read_bytes())
    (output/'item.json').write_text(json.dumps(item, ensure_ascii=False, indent=2))
    return item


def verify_conversion(item):
    if not isinstance(item.get('conversion_path'), str) or not isinstance(item.get('conversion_sha256'), str):
        raise ValueError('formal collection requires a sealed conversion record')
    record = _json(_verified_bytes(item['conversion_path'], item['conversion_sha256']))
    if (record.get('complete') is not True or record.get('training_admitted') is not False
            or record.get('protocol') != model_io.MODEL_COMMAND_NORMALIZER_VERSION
            or record.get('protocol_module_sha256') != digest_bytes(Path(model_io.__file__).read_bytes())
            or record.get('converter_sha256') != digest_bytes(Path(__file__).read_bytes())):
        raise ValueError('conversion protocol/source identity changed or incomplete')
    binding = record['binding']
    _verified_bytes(Path(item['conversion_path']).parent/'private/reconstruction_evidence',
                    binding['reconstruction_evidence']['sha256'])
    expected_environment = digest_bytes(json.dumps(binding['environment_tree'], sort_keys=True,
                                                   ensure_ascii=False, allow_nan=False).encode())
    if item['environment_sha256'] != expected_environment:
        raise ValueError('converted environment differs from reconstruction binding')
    source = _json(_verified_bytes(item['source_path'], record['source_sha256']))
    goal = initial_goal(source, record['source_kind'])
    request, mapping = mapped_request(goal, record['source_kind'], binding.get('original_workspace_root'))
    if (item['job']['request'] != request or record['workspace_mapping'] != mapping
            or digest_bytes(goal.encode()) != record['original_goal_sha256']
            or digest_bytes(request.encode()) != record['converted_goal_sha256']
            or item['source_sha256'] != binding['source_sha256']
            or item['acceptance_sha256'] != binding['acceptance_sha256']
            or item['coding_task_kind'] != binding['task_kind']
            or item['job']['tool_scope'] != 'coding'
            or any(item['job'][key] != binding[key] for key in ('max_calls','max_seconds'))):
        raise ValueError('converted task differs from bound original goal/contract')
    expected_source = record['source_kind']+'@'+record['dataset_revision']+'/'+record['source_id']
    if item['source_id'] != expected_source:
        raise ValueError('converted source identity differs')


def preview_input(item):
    """Use production goal/assignment/bootstrap construction; no inference."""
    from .model import LongHorizonModel
    from .model_session import ModelSession
    from .runtime.settings import RuntimeSettings
    from .harness import ActionHarness
    from .schema import RunState
    from .run_lifecycle import RUN_LIFECYCLE_POLICY_KEY, run_lifecycle_policy_document
    from .token_budget import tokenizer
    job = item['job']
    model = LongHorizonModel(ModelSession(client=object(), settings=RuntimeSettings(
        base_url='http://unused.invalid', api_key='', model='conversion-preview', tool_disclosure_mode='full')),
        harness=ActionHarness())
    goal = model.create_literal_goal(job['request'], job['workspace'], runtime_policy={
        RUN_LIFECYCLE_POLICY_KEY: run_lifecycle_policy_document('goal')})
    state = RunState(run_id=job['task_id'], goal=goal)
    text = model_io.render_bootstrap(model.direct_definitions(), model._assignment(state, recent_limit=None))
    return {'input_text': text, 'input_token_ids': [0, *tokenizer().encode(text)],
            'protocol': model_io.MODEL_COMMAND_NORMALIZER_VERSION,
            'preview_only': True, 'model_calls': 0, 'training_admitted': False}


def export_boundaries(run_root, model_sha256, output, *, expected_state_profile=None):
    """Export native evidence only; do not create labels from unreviewed output."""
    from .direct_trace_data import replay_run, protocol_identity
    from .correction_snapshots import validate_generation_snapshot
    root, output = Path(run_root).resolve(strict=True), Path(output).resolve()
    if output.exists() or root == output or root in output.parents or output in root.parents:
        raise ValueError('boundary export must be new and outside original trace')
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('symlink evidence requires a supported explicit snapshot contract')
    files = {str(p.relative_to(root)): digest_bytes(p.read_bytes())
             for p in sorted(root.rglob('*')) if p.is_file()}
    boundaries = (replay_run(root, model_sha256) if expected_state_profile is None else
                  replay_run(root, model_sha256, expected_state_profile=expected_state_profile))
    for row in boundaries.values():
        validate_generation_snapshot(root, row, files)
    # A writer changing the evidence during replay invalidates this export.
    if files != {str(p.relative_to(root)): digest_bytes(p.read_bytes())
                 for p in sorted(root.rglob('*')) if p.is_file()}:
        raise ValueError('production evidence changed during export')
    output.mkdir(parents=True)
    with (output/'boundaries.jsonl').open('x') as stream:
        for row in boundaries.values():
            stream.write(json.dumps({'document_kind': 'native_boundary_evidence',
                'training_admitted': False, **row}, ensure_ascii=False)+'\n')
    version, protocol_sha = protocol_identity()
    manifest = {'run_root': str(root), 'source_files': files, 'model_sha256': model_sha256,
                'state_profile': next(iter(boundaries.values()))['source_state_profile'],
                'protocol': version, 'protocol_module_sha256': protocol_sha,
                'converter_sha256': digest_bytes(Path(__file__).read_bytes()),
                'boundaries': len(boundaries), 'training_rows': 0,
                'target_policy': 'Original outputs are evidence only; no labels or corrected targets generated',
                'boundaries_sha256': digest_bytes((output/'boundaries.jsonl').read_bytes())}
    (output/'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest
