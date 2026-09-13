from dataclasses import replace
import pytest
from rwkv_lh.read_only_agent import ReadOnlyJob, _run_job
from rwkv_lh.coding_agent import _RecordedHarness
from rwkv_lh.controller import LongHorizonController
from test_read_only_agent import factory
from test_unified_controller import call, settings


def test_explicit_takeover_keeps_raw_answer_and_separate_attribution(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    output = tmp_path / 'execution'
    result = _run_job(ReadOnlyJob('takeover', 'Answer', str(workspace), str(output)),
        settings=replace(settings(), model='strong-test'),
        session_factory=factory([call('final_answer', text='Original strong answer')]),
        harness_factory=lambda: _RecordedHarness(output),
        controller_type=LongHorizonController, allowed_scopes=('files',),
        execution_authority='strong_takeover')
    assert result['final'] == 'Original strong answer'
    assert result['assistance'] == 'strong_takeover'
    assert result['execution_model'] == 'strong-test'
    assert result['acceptance'] == 'not_evaluated'


def test_unknown_authority_rejected_before_creating_run(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    output = tmp_path / 'execution'
    with pytest.raises(ValueError, match='execution authority'):
        _run_job(ReadOnlyJob('bad', 'Answer', str(workspace), str(output)),
            settings=settings(), session_factory=factory([]),
            harness_factory=lambda: _RecordedHarness(output),
            controller_type=LongHorizonController, allowed_scopes=('files',),
            execution_authority='auto')
    assert not output.exists()
