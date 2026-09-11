"""Cross-role information invariants; fixtures are never training data."""
from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from rwkv_lh import stateful_goal_loop as loop
from rwkv_lh.goal_loop_protocol import GoalPlanStep
from rwkv_lh.goal_state_protocols import selector_intent_v7, auditor_step_v7, auditor_final
from rwkv_lh.goal_state_protocols.feedback import semantic_feedback
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.model_session import ModelSession
from rwkv_lh.schema import ActionStatus
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import SupervisorPolicy
from test_stateful_goal_loop import _QueueClient, _StrongPlanner, _selector, _settings, _goal, _strong_patch, _audit_call


def action(number, *, output='fact', path='source.txt'):
    return SimpleNamespace(action_id=f'A{number:05d}', sequence=number,
        action_type='read_file', status=ActionStatus.SUCCEEDED,
        arguments={'path':path, 'start_byte':number},
        result={'success':True, 'output':output, 'metadata':{'complete':True}},
        artifact_refs=[], workspace_digest_after='workspace', error=None,
        outcome_type='success')


def test_selector_sees_different_results_with_identical_mechanical_progress():
    def progress(text):
        return selector_intent_v7.build_current_progress(
            assigned_actions=[action(1,output=text)], read_roots=['source.txt'], write_roots=[],
            mechanical_evidence=dict(completion_preconditions_satisfied=True), target_descriptors=[], action_observes_root=lambda *_:True,
            action_mutates_root=lambda *_:False)
    assert progress('Use arithmetic') != progress('Use date input')


def test_selector_mechanical_gate_has_no_completion_authority():
    progress = selector_intent_v7.build_current_progress(assigned_actions=[], read_roots=[],
        write_roots=[], mechanical_evidence={}, target_descriptors=[],
        action_observes_root=lambda *_:False, action_mutates_root=lambda *_:False)
    assert 'completion_preconditions_satisfied' not in progress
    assert progress['completion_authority'] is False


def test_step_audit_keeps_same_root_fragments_and_dependency_evidence(monkeypatch):
    import rwkv_lh.goal_loop_protocol as goal
    step = GoalPlanStep(step_id='S2', objective='Compare both source fragments', phase='observe',
        stage=2, depends_on=('S1',), read_roots=('source.txt',), success_evidence=('Both parts agree with the baseline',))
    dependency = GoalPlanStep(step_id='S1',objective='Read baseline',phase='observe',
        read_roots=('baseline.txt',),success_evidence=('Baseline observed',))
    plan = SimpleNamespace(steps={'S1':dependency,'S2':step}, step_revisions={'S1':1,'S2':1},
        completed_evidence={'S1':('A00001',)}, completed_step_ids={'S1'})
    bindings={'A00001':('S1',1),'A00002':('S2',1),'A00003':('S2',1)}
    state=SimpleNamespace(actions={a.action_id:a for a in [action(1,path='baseline.txt'),action(2),action(3)]},
        artifacts={},artifact_revisions={})
    for module in (loop,goal):
        monkeypatch.setattr(module,'rolling_goal_plan',lambda _:plan)
        monkeypatch.setattr(module,'goal_step_action_bindings',lambda _:bindings)
    refs=loop.StatefulGoalLoopController._step_audit_evidence_refs(state,'S2',1)
    assert refs==('A00001','A00002','A00003')


def test_all_required_executor_facts_survive_even_when_more_than_twelve():
    actions=[action(i) for i in range(1,18)]
    state=SimpleNamespace(actions={a.action_id:a for a in actions})
    refs=tuple(state.actions)
    assert LongHorizonModel._bounded_assignment_action_ids(state,recent_limit=None,action_ids=refs)==refs


def test_planner_default_facts_keep_early_repair_evidence():
    actions=[action(i) for i in range(1,18)]
    state=SimpleNamespace(actions={a.action_id:a for a in actions},goal=SimpleNamespace(request='Compare all records'))
    facts=loop.StatefulGoalLoopController._recent_action_facts(state)
    assert [f['action_id'] for f in facts]==list(state.actions)


@pytest.mark.parametrize('final',[False,True])
def test_auditors_can_return_evidence_grounded_diagnosis(final):
    module=auditor_final if final else auditor_step_v7
    command=ModelCommand('audit_decision',dict(verdict='repair',step_id='' if final else 'S1',
        step_complete=False,evidence_refs=['A00001'],gaps=['candidate_unsupported_claim'] if final else ['phase_evidence_unproved:observe'],
        reason='The search returned zero matches and did not provide the requested source content.'))
    assert module.parse_target(command.canonical).arguments['reason']==command.arguments['reason']


def test_semantic_feedback_keeps_diagnosis_without_replacing_criterion():
    from test_goal_state_protocols import _step
    catalog=auditor_step_v7.build_gap_catalog(_step(),[])
    code=catalog[0]['code']
    packet=semantic_feedback(source_role='auditor_step',boundary_id='B1',source_id='AUD1',plan_revision=1,
        step_id='S1',step_revision=1,gap_codes=[code],gap_catalog=catalog,evidence_refs=[],
        diagnosis='A successful search is not the requested full-file observation.')
    assert packet['diagnosis'].startswith('A successful search')
    assert packet['issues'][0]['criterion']==catalog[0]['criterion']


@pytest.mark.parametrize('final',[False,True])
def test_actual_audit_retry_receives_rejected_raw_output(tmp_path,monkeypatch,final):
    store=LongHorizonStore(tmp_path/'state')
    state=store.create_run(_goal(tmp_path),'AUDIT-RAW-RETRY')
    write=ModelCommand('write_file',{'path':'result.txt','content':'verified'}).canonical
    step=json.dumps(_audit_call('continue',step_id='S1',step_complete=True,evidence_refs=['A00001'],gaps=[],reason='Written'))
    answer=ModelCommand('final_answer',{'text':'Created result.txt.'}).canonical
    accepted=json.dumps(_audit_call('ready_for_final',step_id='',step_complete=False,evidence_refs=['A00001'],gaps=[],reason='Proved'))
    rejected='{"function":"audit_decision","params":{"wrong_field":"original diagnostic marker"}}'
    queue=_QueueClient([write,step,answer,rejected,accepted] if final else [write,rejected,step,answer,accepted])
    model=LongHorizonModel(ModelSession(queue,settings=_settings(progressive=True)),tool_selector=_selector(['write_file']))
    monkeypatch.setattr(loop.StatefulGoalLoopController,'_validate_contract_patch_semantics',staticmethod(lambda *a,**k:None))
    result=loop.StatefulGoalLoopController(store,model=model,harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),supervisor_policy=SupervisorPolicy(mode='static'),max_transitions=20).run(state.run_id)
    assert result.state.status.value=='completed'
    rejected_events=[e for e in result.state.causal_records.values() if e.event_type=='protocol_rejection_recorded']
    assert rejected_events[0].payload['feedback']['rejected_output']==rejected
    assert len(result.state.actions)==1


def test_dependency_observation_cannot_remove_current_step_missing_root_gap(tmp_path, monkeypatch):
    import rwkv_lh.model as model_module
    state = LongHorizonStore(tmp_path/'state').create_run(_goal(tmp_path), 'DEPENDENCY-GAP')
    state.actions['A00001'] = action(1)
    monkeypatch.setattr(model_module, 'goal_step_action_bindings', lambda _: {'A00001': ('S1', 1)})
    records = LongHorizonModel._audit_evidence_records(state, ['A00001'])
    step = GoalPlanStep(step_id='S2', objective='Observe the file again after the dependency',
        phase='observe', depends_on=('S1',), read_roots=('source.txt',),
        success_evidence=('The current file contents were observed',))
    catalog = auditor_step_v7.build_gap_catalog(step.to_dict(), records)
    assert 'read_root_unproved:source.txt' in {item['code'] for item in catalog}


@pytest.mark.parametrize('case', ['valid', 'dependency_only', 'unrelated', 'stale_current', 'failed_current'])
def test_dependency_context_preserves_current_step_completion_authority(monkeypatch, case):
    import rwkv_lh.goal_loop_protocol as goal
    dep = GoalPlanStep(step_id='S1', objective='Read baseline', phase='observe',
        read_roots=('source.txt',), success_evidence=('Baseline observed',))
    step = GoalPlanStep(step_id='S2', objective='Read current contents', phase='observe',
        depends_on=('S1',), read_roots=('source.txt',), success_evidence=('Current contents observed',))
    plan = SimpleNamespace(steps={'S1':dep, 'S2':step}, step_revisions={'S1':1, 'S2':2},
        completed_evidence={'S1':('A00001',)})
    bindings = {'A00001':('S1',1), 'A00002':('S2',1 if case == 'stale_current' else 2), 'A00003':('OTHER',1)}
    state = SimpleNamespace(actions={a.action_id:a for a in (action(1), action(2), action(3))},
        artifacts={}, artifact_revisions={})
    monkeypatch.setattr(goal, 'goal_step_action_bindings', lambda _:bindings)
    if case == 'failed_current':
        state.actions['A00002'].status = ActionStatus.FAILED
        state.actions['A00002'].result['success'] = False
    refs = ['A00001'] if case == 'dependency_only' else ['A00001','A00002']
    if case == 'unrelated':
        refs.append('A00003')
    if case == 'valid':
        goal._validate_completed_step_evidence(state, plan, step_id='S2', evidence_refs=refs)
    else:
        with pytest.raises(ValueError, match='current-step|current revision|unsuccessful'):
            goal._validate_completed_step_evidence(state, plan, step_id='S2', evidence_refs=refs)


def test_transitive_dependency_artifacts_and_revisions_resolve_once(monkeypatch):
    import rwkv_lh.goal_loop_protocol as goal
    steps = {name: GoalPlanStep(step_id=name, objective='Observe a dependency', phase='observe',
        depends_on=deps, success_evidence=('Observation recorded',))
        for name, deps in [('S1',()),('S2',('S1',)),('S3',('S1','S2'))]}
    plan = SimpleNamespace(steps=steps, step_revisions={name:1 for name in steps},
        completed_evidence={'S1':('ART1',), 'S2':('REV2','A00001')})
    state = SimpleNamespace(actions={a.action_id:a for a in (action(1),action(2),action(3))},
        artifacts={'ART1':SimpleNamespace(action_id='A00001')},
        artifact_revisions={'ART2':[SimpleNamespace(revision_id='REV2', action_id='A00002')]})
    monkeypatch.setattr(goal, 'goal_step_action_bindings', lambda _: {f'A{i:05d}':(f'S{i}',1) for i in range(1,4)})
    assert goal.goal_step_evidence_action_ids(state, 'S3', 1, plan=plan) == tuple(state.actions)
    with pytest.raises(ValueError, match='current committed step revision'):
        goal.goal_step_evidence_action_ids(state, 'S3', 2, plan=plan)
    del plan.completed_evidence['S1']
    with pytest.raises(ValueError, match='completed declared dependencies'):
        goal.goal_step_evidence_action_ids(state, 'S3', 1, plan=plan)


def test_prompt_replay_budget_cannot_erase_frontier_and_fact_binding(tmp_path):
    from dataclasses import replace
    from rwkv_lh.model_session import InputBudgetError
    from rwkv_lh.schema import ModelLaneKind
    store = LongHorizonStore(tmp_path/'state')
    state = store.create_run(_goal(tmp_path), 'REPLAY-REQUIRED-INPUT')
    session = ModelSession(_QueueClient([]), settings=_settings(progressive=True))
    model = LongHorizonModel(session, tool_selector=_selector([]))
    checkpoint = session.bootstrap(ModelLaneKind.ACTION,
        model._assignment(state, recent_limit=None, executor_only=True),
        model._menu_definitions, lane_id=model.ACTION_LANE_ID,
        progressive_tool_disclosure=True, independent_tool_selector=True)
    checkpoint = model._bind_executor_fact_scope(state, checkpoint, (), focus_text='Current step')
    checkpoint = replace(checkpoint, token_count=session.settings.max_prompt_tokens(768)+1)
    state.model_states[checkpoint.checkpoint_id] = checkpoint
    state.set_lane_head('executor', checkpoint.checkpoint_id)
    persisted = []
    with pytest.raises(InputBudgetError, match='required|frontier'):
        model._rollover_if_needed(state, checkpoint,
            lambda *args:persisted.append(args), max_output_tokens=768,
            definitions=model._menu_definitions)
    assert state.lane_head('executor') == checkpoint.checkpoint_id
    assert persisted == []


def test_native_cache_rebuild_keeps_early_required_facts(tmp_path):
    from test_model_session import FakeNativeStateClient, settings
    from rwkv_lh.model_session import NativeRWKVModelSession
    from rwkv_lh.schema import ActionRecord, GoalState, RunState
    client = FakeNativeStateClient([])
    model = LongHorizonModel(NativeRWKVModelSession(client, settings=settings()))
    state = RunState(run_id='NATIVE-ALL-FACTS', goal=GoalState.create(
        request='Compare the full observation history', constraints=[], workspace_root=tmp_path))
    previous = model._checkpoint(state, lambda *args:None)
    for number in range(1,18):
        record = ActionRecord.from_dict(dict(action_id=f'A{number:05d}', sequence=number,
            status='succeeded', action_type='read_file', arguments={'path':f'input-{number}.txt'},
            result={'success':True, 'output':f'unique fact {number}'}))
        state.actions[record.action_id] = record
    model._rebuild_native_executor_cache(state, previous, lambda *args:None, cause=RuntimeError('missing cache'))
    assert [name for name,_ in client.calls] == ['create','create']
    rebuilt_input = client.calls[-1][1]
    assert all(f'input-{number}.txt' in rebuilt_input for number in range(1,18))
