from pathlib import Path
import json, hashlib, importlib
root=Path('/home/chase/GitHub/RWKV-LH')
p=root/'data/test_fixtures/controller_role_closure_v1/role_prompt_wire_baseline.json'
data=json.loads(p.read_text())
data['source_kind']='existing_public_unit_test_inputs_rerendered_for_role_information_flow_r1'
data['source_test_sha256']=hashlib.sha256((root/data['source_test_path']).read_bytes()).hexdigest()
data['capture_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
for record in data['records']:
    module=importlib.import_module('rwkv_lh.goal_state_protocols.'+record['protocol'])
    source=module.build_prompt_source(**record['arguments'])
    record['prompt']=module.render_prompt(source)
    record['source_sha256']=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
