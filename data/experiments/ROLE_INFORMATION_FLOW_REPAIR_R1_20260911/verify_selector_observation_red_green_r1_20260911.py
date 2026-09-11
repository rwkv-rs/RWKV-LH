"""Run the same body-sensitivity regression against frozen source in memory."""
from pathlib import Path
import hashlib, json, subprocess, sys, types
ROOT=Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0,str(ROOT/'tests'))
import test_role_information_flow as regression
current=regression.selector_intent_v7
baseline=subprocess.check_output(['git','show','2a54bf46:rwkv_lh/goal_state_protocols/selector_intent_v6.py'],cwd=ROOT,text=True)
module=types.ModuleType('rwkv_lh.goal_state_protocols.baseline_in_memory')
module.__package__='rwkv_lh.goal_state_protocols'
exec(compile(baseline,'frozen-selector-source','exec'),module.__dict__)
regression.selector_intent_v7=module
try:
    regression.test_selector_sees_different_results_with_identical_mechanical_progress()
except AssertionError:
    red='failed_as_expected_body_was_invisible'
else:
    raise AssertionError('Baseline unexpectedly passed')
finally:
    regression.selector_intent_v7=current
regression.test_selector_sees_different_results_with_identical_mechanical_progress()
print(json.dumps(dict(baseline='2a54bf46', source_sha256=hashlib.sha256(baseline.encode()).hexdigest(),red=red,green='passed',old_module_written_to_disk=False),indent=2))
