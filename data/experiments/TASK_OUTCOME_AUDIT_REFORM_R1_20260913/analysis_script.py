import json, sys, shutil
from pathlib import Path
ROOT=Path('/home/chase/GitHub/RWKV-LH'); sys.path.insert(0,str(ROOT))
from rwkv_lh import task_review as r
A=ROOT/'data/experiments/TASK_OUTCOME_AUDIT_REFORM_R1_20260913'
M=ROOT/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913'
reg=json.loads((M/'REGRESSION_REGISTRATION.json').read_text()); pins=json.loads((M/'RUN_REGISTRATION.json').read_text())
identity={'model':pins['model_sha256'],'protocol':pins['source_pins']['rwkv_lh/goal_loop_protocol.py'],'source':r.digest(pins['source_pins']),'sampling':r.digest(reg['sampling']),'state':r.digest(reg['state']),'budget':r.digest({k:v for k,v in reg.items() if k.startswith('max_') or k=='wall_seconds'})}
r.write_once(A/'IDENTITY_SOURCE.json',{'registration':str(M.relative_to(ROOT)),'registration_sha256':r.file_digest(M/'REGRESSION_REGISTRATION.json'),'source_registration_sha256':r.file_digest(M/'RUN_REGISTRATION.json'),'execution_identity':identity})
specs={
'health':[('location','指出文件和处理位置','定位健康处理代码'),('healthy','健康路径','说明健康路径的成功响应内容'),('other','其他 GET 路径','说明其他路径尚未实现的响应')],
'smoke':[('location','指出文件','定位公开检查脚本'),('purpose','说明它检查什么','说明健康请求检查用途，不要求穷举断言'),('limits','它不能证明哪些功能正确','说明单一健康检查不能认证业务功能')],
'validation':[('location','指出文件和函数','定位校验函数'),('integrity','检查哪些方面','说明数据库完整性校验'),('version','哪些情况会被拒绝','说明支持版本外拒绝'),('structure','检查哪些方面','说明必需表列检查')],
'backup':[('location','指出文件和函数','定位备份函数'),('create','备份如何创建','说明先临时备份再独占发布'),('exists','目标已存在时会怎样','说明失败而非覆盖'),('cleanup','临时文件如何清理','说明退出时清理临时文件')]}
contracts={}
for case in reg['cases']:
 reqs=[dict(id=i,user_quote=q,outcome=o,level='essential',missing_effect='缺少用户明确请求的信息',acceptance=o+'；接受等义表达，不限定工具路线',omission_policy='允许省略具体语法和未要求的实现细节') for i,q,o in specs[case['id']]]
 reqs.append(dict(id='readonly',user_quote='不修改文件，不启动服务',outcome='遵守只读范围',level='essential',missing_effect='违反用户约束',acceptance='真实动作无写入或服务启动',omission_policy='无须在答案复述约束'))
 c=dict(schema=r.CONTRACT_SCHEMA,task_id=case['id'],user_request=case['request'],kind='retrospective',protocol_error_policy='stop',execution_identity=identity,requirements=reqs)
 r.freeze_contract(c,A/'contracts'/f"{case['id']}.json");contracts[case['id']]=c
jobs=[]; assessments=[]
for row in json.loads((M/'DEV_RESULTS.json').read_text()):
 directory=M/'dev'/row['id']; c=contracts[row['file_id']]
 run=r.capture_diagnostic_run(directory,task_id=row['file_id'],arm=row['arm'],repeat=row['repeat'],protocol_error_policy='stop',execution_identity=identity,historical=True,assistance='rwkv_independent')
 evidence=[e['id'] for e in run['evidence']]
 judgment=dict(schema=r.REVIEW_SCHEMA,contract_sha256=r.digest(c),run_sha256=r.digest(run),reviewer='Codex external retrospective review; not blinded, not new efficacy evidence',validity='valid',validity_reason='既有获准开发工作区，保留首错终止边界性质；本轮未调用执行模型',validity_evidence_ids=evidence,requirements=[],findings=[],causes=[])
 if run['answer']:
  for req in c['requirements']:
   judgment['requirements'].append(dict(id=req['id'],status='met',reason={'location':'原文指出 verify_public.py','purpose':'说明 /health 成功检查的用途；不要求穷举断言','limits':'明确列出预约创建、冲突、幂等和持久化不被此检查证明','readonly':'真实轨迹仅目录、读取和最终提交'}[req['id']],evidence_ids=evidence))
  judgment['findings'].append(dict(kind='contradiction',severity='minor',quote='只做 /health 的 200 响应检查',reason='脚本还断言 JSON ok 为 true；只做一词过强',impact='缩窄了断言描述，但未改变健康检查用途和业务验证边界；应保留缺陷而非称完美',evidence_ids=evidence))
 judgment['causes']=[dict(category='model_behavior',certainty='observed',reason='原始提交与终止按真实记录保留，不从中推断输入或 State 根因',evidence_ids=['E1','E2'])]
 prefix=f"reviews/{row['id']}"
 r.write_once(A/(prefix+'.run.json'),run);r.write_once(A/(prefix+'.judgment.json'),judgment)
 assessment=r.assess(c,run,judgment,evidence_root=directory);assessments.append(assessment)
 r.write_once(A/(prefix+'.assessment.json'),assessment)
 jobs.append(dict(contract=f"contracts/{row['file_id']}.json",run=prefix+'.run.json',judgment=prefix+'.judgment.json',evidence_root='../RWKV_DISCOVERY_INPUT_MENU_R1_20260913/dev/'+row['id']))
r.write_once(A/'BATCH.json',{'reviews':jobs})
r.write_once(A/'RETROSPECTIVE_SUMMARY.json',r.aggregate(assessments))
shutil.copyfile(__file__,A/'analysis_script.py')
print(json.dumps(r.aggregate(assessments),ensure_ascii=False))
