"""Source-bound read and final labels with explicit single-review provenance."""
import json
from pathlib import Path

from . import model_io
from .correction_review import build_review_packet, validate_review, require_source_bound_reviews
from .correction_snapshots import validate_generation_snapshot
from .direct_trace_data import replay_run
from .harness import ActionHarness
from .offline_teacher_api import digest, write_json
from .schema import GoalState, RunState, TaskAction
from .statetune_core import require, read_sealed_json
from .workspace_snapshot import copy_verified_workspace, tree_identity

READ_FUNCTIONS = {'read_file', 'search_text', 'list_directory'}


def validate_observation_correction(*, run_root, checkpoint_id, target_text, model_sha256,
                                    source_files, reviews, judgment, output):
    from .trace_correction_pipeline import sealed_files
    root = sealed_files(run_root, source_files)
    output = Path(output).resolve()
    require(not output.exists() and root not in output.parents and output not in root.parents,
            'validation output exists or overlaps source')
    actual = replay_run(root, model_sha256)[checkpoint_id]
    snapshot = validate_generation_snapshot(root, actual, source_files)
    stop = model_io.JSON_CALL_STOP_SUFFIXES[0]
    require(target_text.endswith(stop), 'exact production stop required')
    raw = target_text[:-len(stop)]
    envelope = json.loads(raw)
    require(set(envelope) == {'function', 'params'}, 'exact target envelope required')
    command = model_io.parse_model_command(raw)
    require(command.name in READ_FUNCTIONS | {'final_answer'}, 'unsupported observation target')
    reviewed = validate_review(build_review_packet(actual_rwkv_input=actual['input_text'], candidate=raw), judgment)
    require(reviewed['accepted'], 'semantic review rejected')
    require_source_bound_reviews(reviews, input_sha256=digest(actual['input_text']),
                                 target_sha256=digest(target_text), execution_backed=True)
    record = dict(run_root=str(root), checkpoint_id=checkpoint_id, model_sha256=model_sha256,
                  source_files=source_files, reviews=reviews, judgment=judgment,
                  target_text=target_text, input_text=actual['input_text'],
                  input_token_ids=actual['input_token_ids'], request_id=actual['request_id'],
                  input_checkpoint_id=actual['input_checkpoint_id'], training_admitted=False,
                  review_scope='single reviewer; grounding anchors are not a proof of semantic truth')
    output.mkdir(parents=True)
    workspace = output / 'workspace'
    record['before_tree'] = copy_verified_workspace(snapshot, workspace)
    if command.name in READ_FUNCTIONS:
        state = json.loads((root / 'state_snapshot.json').read_text())
        goal = GoalState.create(request=state['goal']['request'], constraints=(), workspace_root=str(workspace))
        observation = ActionHarness().execute(TaskAction(command.name, command.arguments), goal).to_dict()
        record['tool_result'] = observation
        valid = observation.get('success') is True
    else:
        # Final is grounded in ACTUAL visible executions, never newly-run checks
        # or a test filename. Semantic entailment remains the named reviewer's job.
        state = RunState.from_dict(json.loads((root / 'state_snapshot.json').read_text()))
        current = state.model_states[actual['input_checkpoint_id']]
        visible = set()
        while current is not None:
            visible.update(current.event_ids)
            current = state.model_states.get(current.parent_checkpoint_id)
        executions = {key: state.model_events[key].payload for key in sorted(visible)
                      if state.model_events[key].event_type == 'action_result'}
        record['visible_execution_events'] = executions
        record['review_evidence_bindings'] = reviewed['evidence_bindings']
        valid = bool(executions) and bool(reviewed['claims'])
    record['after_tree'] = tree_identity(workspace)
    valid = valid and record['before_tree'] == record['after_tree']
    record['status'] = 'validated_candidate' if valid else 'verification_failed'
    write_json(output / 'VALIDATION.json', record)
    return record


def revalidate_training_observation(row, *, run_root, source_files, model_sha256, output):
    ref = row['observation_validation']
    proof = read_sealed_json(ref['path'], ref['sha256'])
    require(proof['status'] == 'validated_candidate' and Path(proof['run_root']).resolve() == Path(run_root).resolve()
            and proof['source_files'] == source_files and proof['model_sha256'] == model_sha256,
            'observation source binding differs')
    for key, other in [('target_text', 'target_text'), ('input_text', 'input_text'),
                       ('input_token_ids', 'input_token_ids'), ('reviews', 'reviews'),
                       ('request_id', 'request_id'), ('input_checkpoint_id', 'input_checkpoint_id'),
                       ('candidate_checkpoint_id', 'checkpoint_id')]:
        require(row[key] == proof[other], 'observation row binding differs: ' + key)
    result = validate_observation_correction(run_root=run_root, checkpoint_id=proof['checkpoint_id'],
        target_text=row['target_text'], model_sha256=model_sha256, source_files=source_files,
        reviews=row['reviews'], judgment=proof['judgment'], output=output)
    require(result['status'] == 'validated_candidate', 'fresh observation verification failed')
    return result
