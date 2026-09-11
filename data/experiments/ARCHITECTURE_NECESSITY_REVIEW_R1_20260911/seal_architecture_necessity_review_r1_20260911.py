from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path('/home/chase/GitHub/RWKV-LH')
OUT=ROOT/'data/experiments/ARCHITECTURE_NECESSITY_REVIEW_R1_20260911'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=OUT/'REPORT.zh-CN.md';s=p.read_text()
for a,b in [('stateful_goal_loop.py:1977','stateful_goal_loop.py:1987'),('1998要求','2009要求'),('1919先','1923先'),('1956仅','1970仅'),('model.py:794','model.py:791'),('1756处','1755处'),('1235拒绝','1236拒绝')]:s=s.replace(a,b)
s=s.replace('读取到的R3进度为36/117 worker结束，这不是completed或Strict分数，本轮不将该动态进度当完整评测，也未停止或修改采集。','worker进度不等于completed或Strict分数，本轮不将动态进度当完整评测，也未停止或修改采集。')
p.write_text(s)
files=['rwkv_lh/stateful_goal_loop.py','rwkv_lh/goal_loop_protocol.py','rwkv_lh/model.py','rwkv_lh/operation_contracts.py','rwkv_lh/product_runtime.py','rwkv_lh/goal_state_protocols/__init__.py','rwkv_lh/goal_state_protocols/auditor_step_v7.py','rwkv_lh/goal_state_protocols/auditor_final.py','rwkv_lh/exact_tool_selector/network_protocol.py','scripts/run_rwkv_e2e_benchmark.py','AGENTS.md','docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md','data/experiments/ROLE_INPUT_METHOD_REVIEW_R1_20260911/REPORT.zh-CN.md','data/experiments/R126_CURRENT_REGRESSION_REVIEW_R1_20260911/REPORT.zh-CN.md','data/experiments/FULL_TRACE_CAMPAIGN_R3_FLASH_20260911/REPORT.zh-CN.md']
pins=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files={f:sha(ROOT/f) for f in files})
(OUT/'SOURCE_PINS.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2)+'\n')
old=json.loads((ROOT/'data/experiments/ROLE_INFORMATION_FLOW_REPAIR_R1_20260911/SOURCE_PINS.json').read_text())
checks={f:sha(ROOT/f)==v for f,v in old['files'].items() if f.startswith(('rwkv_lh/','scripts/','tests/','data/test_fixtures/'))}
assert all(checks.values())
(OUT/'VALIDATION.json').write_text(json.dumps(dict(new_tests_run=False,reason='analysis-only; runtime/test/fixture files unchanged from recorded 1502-pass source',unchanged_code_and_test_hashes=checks,new_model_calls=0,new_training=False,new_dataset=False,modified_production_files=[]),indent=2)+'\n')
for name in ['audit_architecture_decision_authority_r1_20260911.py',Path(__file__).name]:shutil.copy2(ROOT/'temp'/name,OUT/name)
(OUT/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print(json.dumps(dict(report_sha256=sha(OUT/'REPORT.zh-CN.md'),checked_unchanged_code_and_tests=len(checks)),indent=2))
