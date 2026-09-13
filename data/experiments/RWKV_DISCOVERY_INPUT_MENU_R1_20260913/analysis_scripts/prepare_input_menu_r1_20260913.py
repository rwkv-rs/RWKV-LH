from pathlib import Path
import json,hashlib,shutil,sys
R=Path('/home/chase/GitHub/RWKV-LH');B=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913';D.mkdir(exist_ok=False);shutil.copytree(B/'source',D/'source',ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(B/'PREEXISTING.json',D/'PREEXISTING.json')
s=(R/'temp/run_discovery_r1_20260913.py').read_text().replace('RWKV_FILE_DISCOVERY_BASELINE_R1_20260913','RWKV_DISCOVERY_INPUT_MENU_R1_20260913').replace("for arm in ['zero']:","for arm in (['full','readonly'] if repeat==1 else ['readonly','full']):").replace('used_calls()>=48','used_calls()>=96').replace('time.time()-started<3600','time.time()-started<7200')
anchor="load_local_env(R/'.env.local')"
helper='''class ReadOnlyMenuHarness(ActionHarness):
 def g1i_tool_definitions(self, *args, **kwargs):
  return [d for d in super().g1i_tool_definitions(*args, **kwargs) if self.definition(d['name']).read_only and not self.definition(d['name']).side_effect]
'''
s=s.replace(anchor,helper+'\n'+anchor).replace('harness=ActionHarness());store=',"harness=(ReadOnlyMenuHarness() if arm=='readonly' else ActionHarness()));store=")
(R/'temp/run_input_menu_r1_20260913.py').write_text(s)
v=(R/'temp/verify_discovery_server_r1_20260913.py').read_text().replace('RWKV_FILE_DISCOVERY_BASELINE_R1_20260913','RWKV_DISCOVERY_INPUT_MENU_R1_20260913');(R/'temp/verify_input_menu_r1_20260913.py').write_text(v)
print(D)
