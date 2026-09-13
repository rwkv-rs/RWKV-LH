from pathlib import Path
import json,hashlib,shutil,tarfile
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reg=json.loads((D/'RUN_REGISTRATION.json').read_text());assert all(sha(R/f)==h for f,h in reg['source_pins'].items());assert all(sha(R/f)==h for f,h in json.loads((D/'PREEXISTING.json').read_text()).items());assert '1530 passed' in (D/'PYTEST_FULL.log').read_text()
status={'legacy_scoring_preserved':True,'quality_review_status':'preliminary: useful-summary versus assertion-detail omission not sufficiently explicit in prior registration','eligible_for_improvement_claim':False,'verified_delivery':{'full':0,'readonly':1},'owner_steering':'Complete audit-system reform before further interpretation or new inference; no rescoring historical results as gains','production_source_unchanged':True};(D/'ASSESSMENT_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
adir=D/'analysis_scripts';adir.mkdir(exist_ok=False)
names=['prepare_input_menu_r1_20260913.py','freeze_input_menu_r1_20260913.py','run_input_menu_r1_20260913.py','audit_input_menu_r1_20260913.py','audit_direct_candidate_tasks_r2_20260913.py','inspect_discovery_inputs_r1_20260913.py','measure_observation_wire_r1_20260913.py','check_input_boundaries_r1_20260913.py','check_menu_observations_r1_20260913.py','audit_menu_terminal_states_r1_20260913.py','score_input_menu_r1_20260913.py','prepare_input_review_r1_20260913.py','score_input_menu_final_r1_20260913.py','verify_input_menu_r1_20260913.py','verify_input_inventory_r1_20260913.py','seal_input_menu_r1_20260913.py']
for n in names:shutil.copy2(R/'temp'/n,adir/n)
files=[p for p in D.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('-wal','-shm'))];pins={str(p.relative_to(D)):sha(p) for p in files};(D/'EVIDENCE_FILES.json').write_text(json.dumps(pins,indent=2)+'\n')
with tarfile.open(D/'EVIDENCE.tar.gz','w:gz') as t:
 for p in files:t.add(p,arcname=str(p.relative_to(D)),recursive=False)
seal=dict(files=len(files),archive_sha256=sha(D/'EVIDENCE.tar.gz'),manifest_sha256=sha(D/'EVIDENCE_FILES.json'));(D/'SEAL.json').write_text(json.dumps(seal,indent=2)+'\n')
report='''# 输入菜单对照R1：原记录封存，审核规则整改中

任务交付：完整菜单组0/8提交，只读菜单组1/8提交；两组mutation与虚假完成声明均0。full为6协议中断/2预算中断，readonly为6协议中断/1预算中断/1提交。原临时质量判读0/8与1/8保留在SUMMARY与SUBMITTED_ANSWER_REVIEW；后者省略JSON ok断言，是否属于必要细节的规则没有充分明确。按owner最新要求先整改审核体系，旧判读标preliminary，不据此宣布收益或普遍稳定。

唯一输入变量：同四题两遍、同zero 13.3B与采样/State/预算，将19个菜单工具筛为权限允许的8个。注册表说明/schema原样复用，R4读取说明不变，真实工具/观察/参数选择不变。菜单2633→1384 token；无新生产协议/角色/自动参数修正。初始输入除菜单首行外SHA完全相同。

原健康问题78 token，初始输入3205 token。第一次搜索5条命中行合计约90 token，实际观察2075 token；空搜索观察731 token。确有封装负担，但不是它造成错误的因果证明。已排查代码块边界：实际raw token包含闭合围栏；原21份实际输入单独保存，没有截取显示代替真实输入。

本轮41生成、28工具观察、73持久checkpoint核验；字段混用/搜索重复仍存在，未发现观察遗漏或父State接错。完整菜单组21生成、101598逻辑输入/5073输出token、593.86秒；只读组20生成、75644输入/6628输出token、587.02秒。只是小组串行数字，无账单、峰值或合格项目成本/吞吐证据。强模型0、训练0。

重要限制：诊断运行器按冻结规则协议错误即停；生产Controller.run已有protocol_rejection反馈路径。这些实验不覆盖收到真实拒绝原因后的自纠能力，不能直接代表完整Code Agent能力；也不能把真实错误反馈与程序代改参数混为一谈。只读菜单缩减结果不排除参数措辞/排列、观察重点和跨工具合同保持的输入问题。

全测1530 passed/0 skipped，原五文件SHA保持，生产未改、GitHub未更新、无新datasets。原数据/原分/失败均保留，当前转入统一结果验收、审核证据绑定与归因规则整改，暂停新推理实验。审核改动不得回填本轮输入或重算为收益。

'''
report+=f"运行登记SHA `{sha(D/'RUN_REGISTRATION.json')}`；证据包SHA `{seal['archive_sha256']}`；文件清单SHA `{seal['manifest_sha256']}`。\n"
(D/'REPORT.zh-CN.md').write_text(report);print(sha(D/'REPORT.zh-CN.md'))
