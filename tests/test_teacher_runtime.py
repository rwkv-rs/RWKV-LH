from types import SimpleNamespace
from unittest.mock import patch

from rwkv_lh.strong_session import StrongCompletion
from rwkv_lh.supervisor_openai import SupervisorAPISettings
from rwkv_lh.teacher_runtime import DeadlineStrongCompletion


def test_teacher_request_uses_remaining_task_budget_not_legacy_240(tmp_path):
    settings = SupervisorAPISettings(base_url='http://localhost:18243/v1', api_key='',
                                    model='test', stage_checker_model='test', read_timeout_seconds=240)
    with patch('rwkv_lh.teacher_runtime.time.monotonic', return_value=100):
        client = DeadlineStrongCompletion(settings, tmp_path, 12, max_seconds=1200,
                                          require_exact_tokens=False)
    captured = []
    def request(self, prompt, max_tokens, stop):
        captured.append(self.client.settings.read_timeout_seconds)
        return SimpleNamespace(content='unchanged')
    with patch('rwkv_lh.teacher_runtime.time.monotonic', side_effect=[400, 1250]), \
         patch.object(StrongCompletion, 'text_completion', request):
        assert client.text_completion('original').content == 'unchanged'
        client.text_completion('next')
    assert captured == [900, 50]
    assert settings.read_timeout_seconds == 240
    client.client.close()


def test_teacher_deadline_stops_before_network_call(tmp_path):
    from rwkv_lh.read_only_agent import ReadOnlyBudgetExpired
    import pytest
    settings = SupervisorAPISettings(base_url='http://localhost:18243/v1', api_key='',
                                    model='test', stage_checker_model='test')
    with patch('rwkv_lh.teacher_runtime.time.monotonic', return_value=0):
        client = DeadlineStrongCompletion(settings, tmp_path, 12, max_seconds=10,
                                          require_exact_tokens=False)
    with patch('rwkv_lh.teacher_runtime.time.monotonic', return_value=11), \
         patch.object(StrongCompletion, 'text_completion') as network:
        with pytest.raises(ReadOnlyBudgetExpired):
            client.text_completion('original')
        network.assert_not_called()
    client.client.close()
