import pytest

from rwkv_lh import trace_correction_pipeline as pipeline


def test_diagnosis_handles_real_unknown_arguments_and_parent_counts():
    from pathlib import Path
    from scripts.analyze_rwkv_defects import analyze
    root = Path(__file__).resolve().parents[1]
    model = '559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'
    zero = analyze(root / 'data/experiments/R38/agent-run/execution', model)
    assert zero['agent']['new_protocol_rejections'] == 2
    assert zero['observations']['invalid_tool_call'] == 2


def test_advice_uses_shared_request_and_preserves_teacher_text():
    from scripts.run_bounded_advice import BudgetedAdviceClient
    from rwkv_lh.summary_advice import request_advice, ADVICE_PROTOCOL, ADVICE_SYSTEM
    from rwkv_lh.schema import GoalState
    import json
    class Teacher:
        calls = 0
        def complete(self, system, user):
            self.calls += 1
            assert system == ADVICE_SYSTEM
            assert json.loads(user)['protocol'] == ADVICE_PROTOCOL
            return {'advice': 'Inspect the actual failed check.'}, {'model': 'test-teacher'}
    teacher = Teacher()
    client = BudgetedAdviceClient(teacher)
    goal = GoalState.create(request='Repair the existing code', constraints=(), workspace_root='/workspace')
    assert request_advice(client, goal, {}, '', 'advice-test', 100) == 'Inspect the actual failed check.'
    assert teacher.calls == 1


def test_advice_continuation_cannot_upgrade_evaluation_to_training(tmp_path):
    from scripts import run_bounded_advice as runner
    (tmp_path / 'SOURCE_PURPOSE.json').write_text('{"source_purpose":"development_evaluation"}')
    with pytest.raises(ValueError, match='purpose'):
        runner.continuation_purpose(tmp_path, 'production_training_source')
    assert runner.continuation_purpose(tmp_path, 'development_evaluation') == 'development_evaluation'


def test_focus_requires_visible_evidence_before_generation():
    with pytest.raises(ValueError, match='visible'):
        pipeline.validate_learning_contract({
            'defect_family': 'read_stall', 'objective': 'Choose a useful next action',
            'evidence_quote': 'invented source', 'acceptance_scope': 'local_behavior',
        }, 'actual visible source')


def test_local_contract_does_not_claim_project_completion():
    result = pipeline.validate_learning_contract({
        'defect_family': 'read_stall', 'objective': 'Repair the observed timestamp validation',
        'evidence_quote': 'observed timestamp', 'acceptance_scope': 'local_behavior',
    }, 'An observed timestamp has invalid offset.')
    assert result['acceptance_scope'] == 'local_behavior'
    with pytest.raises(ValueError, match='scope'):
        pipeline.validate_learning_contract(dict(result, acceptance_scope='project_completed'),
                                            'An observed timestamp has invalid offset.')


def test_diagnostic_focus_cannot_be_used_as_edit_proof():
    contract = {'defect_family': 'failure_recovery', 'objective': 'Observe a failing test',
                'evidence_quote': 'test', 'acceptance_scope': 'diagnostic_observation'}
    with pytest.raises(ValueError, match='scope'):
        pipeline.validate_learning_contract(contract, 'test', function='write_file')
