"""Reuse the verified deployment mechanism for frozen 21c0cf45; no remote Git."""
from pathlib import Path
import json
import subprocess
ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/AUDIT_FANOUT_DEPLOYMENT_R1_20260910'
old_remote = '/home/chase/GitHub/RWKV-LH-statetune-driver-r2-20260910'
new_remote = '/home/chase/GitHub/RWKV-LH-audit-fanout-r1-20260910'
script = (ROOT / 'temp/freeze_statetune_driver_deployment_r2_20260910.py').read_text()
script = script.replace('STATETUNE_DRIVER_INTEGRATION_R2_20260910', OUT.name).replace(old_remote, new_remote)
script = script.replace("'working_tree_changes': True", "'working_tree_changes': False")
target = ROOT / 'temp/freeze_audit_fanout_deployment_20260910.py'
with target.open('x') as stream:
    stream.write(script)
subprocess.run([str(ROOT / '.venv/bin/python'), str(target)], cwd=ROOT, check=True)
print(json.dumps({'remote_root': new_remote, 'upload_pending_green_tests': True}))
