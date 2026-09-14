import json
import pytest

from rwkv_lh.read_only_agent import (
    ReadOnlyJob, ReadOnlyHarness, _ReadOnlyController, _run_job, run_read_only_job,
)
from rwkv_lh.coding_agent import CodingJob, run_coding_job
from test_read_only_agent import factory
from test_unified_controller import call, settings


@pytest.mark.parametrize('authority', ['rwkv', 'strong_takeover'])
def test_execution_exception_is_terminal_delivery_not_running_state(tmp_path, authority):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    output = tmp_path / 'run'
    result = _run_job(
        ReadOnlyJob('failed', 'Read workspace', str(workspace), str(output)),
        settings=settings(), session_factory=factory([]),
        execution_authority=authority, harness_factory=ReadOnlyHarness,
        controller_type=_ReadOnlyController, allowed_scopes=('files', 'inspect'),
    )
    assert result['termination'] == 'error' and result['final'] is None
    assert result['status'] == 'failed'
    snapshot = json.loads((output / 'state_snapshot.json').read_text())
    assert result['state_status'] == snapshot['status'] == 'running'
    assert json.loads((output / 'RESULT.json').read_text()) == result


def test_startup_failure_has_no_started_state_but_failed_delivery(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    def unavailable(**kwargs):
        raise ConnectionError('provider unavailable')

    result = run_read_only_job(
        ReadOnlyJob('startup', 'Read', str(workspace), str(tmp_path / 'run')),
        settings=settings(), session_factory=unavailable,
    )
    assert result['status'] == 'failed' and result['state_status'] == 'not_started'
    assert result['termination'] == 'error' and result['generation_started'] == 0


def test_budget_delivery_is_interrupted_without_changing_resumable_state(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (workspace / 'a.txt').write_text('actual content')
    output = tmp_path / 'run'
    result = run_read_only_job(
        ReadOnlyJob('budget', 'Read and summarize', str(workspace), str(output), max_calls=1),
        settings=settings(), session_factory=factory([call('read_file', path='a.txt')]),
    )
    assert result['status'] == 'interrupted' and result['termination'] == 'budget'
    assert result['final'] is None
    assert result['state_status'] == json.loads((output / 'state_snapshot.json').read_text())['status']
    assert result['actions'][0]['result']['output'] == 'actual content'


def test_coding_delivery_inherits_terminal_status_without_acceptance(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    output = tmp_path / 'run'
    result = run_coding_job(
        CodingJob('coding', 'Report current state', str(workspace), str(output)),
        settings=settings(), session_factory=factory([call('final_answer', text='Original answer.')]),
    )
    assert result['status'] == 'completed' and result['state_status'] == 'completed'
    assert result['termination'] == 'submitted' and result['acceptance'] == 'not_evaluated'
    assert result['final'] == 'Original answer.' and result['changed_files'] == []
    assert json.loads((output / 'DELIVERY.json').read_text())['status'] == 'completed'
