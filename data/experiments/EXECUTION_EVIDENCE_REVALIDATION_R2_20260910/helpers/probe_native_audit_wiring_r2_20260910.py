"""Offline audit wiring diagnostic; no model request and no training evidence."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path('/home/chase/GitHub/RWKV-LH')
spec = importlib.util.spec_from_file_location('r2_driver', ROOT / 'temp/run_execution_revalidation_r2_20260910.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
benchmark, roles, _, _ = driver.configure()
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.native_state import NATIVE_STATE_PROTOCOL_VERSION

trace = []
results = []
capabilities = SimpleNamespace(durable_recurrent_state=True, recurrent_state_protocol=NATIVE_STATE_PROTOCOL_VERSION)
with patch.object(OpenAICompatibleRWKVClient, 'capabilities', return_value=capabilities):
    sessions = benchmark._build_stateful_goal_role_sessions(roles['executor_args'], trace)
    try:
        for role, session in sessions.items():
            original = session.client.audit_hook
            start = len(trace)
            session.client._emit({'type': 'native_request_transport_error', 'probe_only': True})
            missing = len(trace) - start
            session._emit({'type': 'offline_session_control', 'probe_only': True})
            control = len(trace) - start - missing
            session.client.audit_hook = session.audit_hook
            session.client._emit({'type': 'native_request_transport_error', 'probe_only': True})
            wired = len(trace) - start - missing - control
            session.client.audit_hook = original
            results.append({'role': role, 'client_hook_is_none': original is None,
                            'session_hook_present': callable(session.audit_hook),
                            'client_event_received': missing, 'session_control_received': control,
                            'probe_only_manual_wiring_received': wired})
    finally:
        benchmark._close_stateful_goal_role_sessions(sessions)
output = {'diagnostic_only': True, 'network_requests': 0, 'production_modified': False,
          'factory': 'scripts.run_rwkv_e2e_benchmark._build_stateful_goal_role_sessions',
          'results': results, 'offline_control_events': trace,
          'conclusion': 'Native client events are dropped by the actual session factory. A zero event count cannot establish absence of recovered Native transport exceptions.'}
path = driver.ROUND / 'NATIVE_AUDIT_WIRING_OFFLINE_PROBE.json'
with path.open('x') as stream:
    json.dump(output, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(output, ensure_ascii=False))
