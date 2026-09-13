from rwkv_lh.run_lifecycle import RUN_LIFECYCLE_POLICY_KEY, run_lifecycle_policy_document
from rwkv_lh.schema import RunStatus
from test_unified_controller import build, call


def goal_policy():
    return {RUN_LIFECYCLE_POLICY_KEY: run_lifecycle_policy_document('goal')}


def test_resume_can_recover_after_old_failure_without_erasing_history(tmp_path):
    controller,store,workspace,client,_=build(tmp_path,
        [call('read_file',path='missing.txt') for _ in range(6)]+
        [call('read_file',path='exists.txt'),call('final_answer',text='Recovered by reading the existing file.')],
        max_transitions=12,runtime_policy=goal_policy())
    (workspace/'exists.txt').write_text('content')
    first=controller.run('RUN')
    assert len(first.state.actions)==5 and first.final_output==''
    old_states=set(first.state.model_states)
    second=controller.resume('RUN')
    assert second.state.status==RunStatus.COMPLETED
    assert len(second.state.actions)==7 and len(client.prompts)==8
    assert next(iter(second.state.failure_budgets.values()))==6
    assert old_states <= set(second.state.model_states)
    assert store.load('RUN').failure_budgets==second.state.failure_budgets


def test_each_continuation_still_bounds_repeated_failures_and_preserves_totals(tmp_path):
    controller,store,_,client,_=build(tmp_path,
        [call('read_file',path='missing.txt') for _ in range(10)],
        max_transitions=12,runtime_policy=goal_policy())
    first=controller.run('RUN')
    assert len(first.state.actions)==5
    second=controller.resume('RUN')
    assert len(second.state.actions)==10 and len(client.prompts)==10
    assert next(iter(second.state.failure_budgets.values()))==10
    reasons=[e.payload.get('reason') for e in second.state.causal_records.values() if e.event_type=='run_yielded']
    assert reasons==['identical_failure_budget_exhausted']*2
    assert second.final_output==''
