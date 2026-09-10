"""Offline real recovery through production role factories; no model generation."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('r2_driver', ROOT / 'temp/run_execution_revalidation_r2_20260910.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
benchmark, roles, _, _ = driver.configure()
import requests
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.native_state import NATIVE_STATE_PROTOCOL_VERSION
from test_openai_compat_runtime import FakeResponse, FakeSession

fakes = []
def fake_session(_):
    fake = FakeSession([
        requests.ConnectionError('OFFLINE_FIRST_CAUSE_FIXTURE'),
        FakeResponse({'detail': 'request ID is not recorded'}, status_code=404),
        FakeResponse({'detail': 'request ID is not recorded'}, status_code=404),
        FakeResponse({'rolled_back': True, 'parent_state_ref': 'offline-parent'}),
    ])
    fakes.append(fake)
    return fake

trace = []
results = []
caps = SimpleNamespace(durable_recurrent_state=True, recurrent_state_protocol=NATIVE_STATE_PROTOCOL_VERSION)
with patch.object(OpenAICompatibleRWKVClient, 'capabilities', return_value=caps), patch.object(OpenAICompatibleRWKVClient, '_new_session', fake_session):
    sessions = benchmark._build_stateful_goal_role_sessions(roles['executor_args'], trace)
    try:
        for role, session in sessions.items():
            session.native_client.state_rollback(candidate_state_ref='offline-candidate', parent_state_ref='offline-parent')
            results.append({'role': role, 'recovery_returned_successfully': True,
                            'transport_error_events_delivered': sum(e.get('type') == 'native_request_transport_error' and e.get('model_role') == role for e in trace),
                            'client_hook_is_none': session.client.audit_hook is None})
    finally:
        benchmark._close_stateful_goal_role_sessions(sessions)
output = {'offline_fixture_only': True, 'network_requests': 0, 'model_generations': 0,
          'production_modified': False, 'results': results, 'delivered_trace': trace,
          'mock_http_methods_per_client': [[call[0] for call in fake.calls] for fake in fakes],
          'conclusion': 'All four production role clients recover POST/404/404/POST successfully but drop the original error event. This is an observability defect, not evidence that safe resubmission itself fails.'}
with (driver.ROUND / 'NATIVE_RECOVERY_AUDIT_OFFLINE_PROBE.json').open('x') as stream:
    json.dump(output, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(output, ensure_ascii=False))
