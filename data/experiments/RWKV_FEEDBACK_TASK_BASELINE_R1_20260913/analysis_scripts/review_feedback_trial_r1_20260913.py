from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as r
D=R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913';reg=json.loads((D/'REGISTRATION.json').read_text());raw=json.loads((D/'RESULTS.json').read_text());assert len(raw)==8
manual={
 'smoke-feedback-r1':('c04f73a15898cf6db238cbef9a55507bdc10dcd82d624a50dc7498b7f2a4d49f',{'location':'明确 verify_public.py','purpose':'明确 /health 200 与 JSON ok 为 true','limits':'明确不能认证业务行为；附加接口细节中一处错误另记','readonly':'动作与文件 SHA 证明只读'}),
 'health-feedback-r2':('54f4a88de544a5514cdf58bbc2325f08e9fb8889338a8a94978b1da48979a5c2',{'location':'server.py 第7行定位 Handler 类，紧随的 do_GET 可直接找到','healthy':'正确说明200和ok=true','other':'正确说明501和not_implemented','readonly':'真实动作只搜索和读取，文件未改'}),
 'smoke-feedback-r2':('970815963214a1274261c0d7f7f1a1cb108e5da1e4f147c8e90c7a9ef8103001',{'location':'明确 verify_public.py','purpose':'正确说明健康请求与200/ok断言','limits':'明确不认证业务、并发和持久化；不能证明分页不等于声称存在分页实现，不能因此判编造','readonly':'实际仅目录与读取，复述约束不是虚假完成'})}
assessments=[];jobs=[]
for row in raw:
 p=D/'runs'/row['id'];contract=r.load_contract(D/'contracts'/f"{row['file_id']}.json")
 run=r.capture_diagnostic_run(p,task_id=row['file_id'],arm='feedback',repeat=row['repeat'],protocol_error_policy='feedback',execution_identity=contract['execution_identity'],historical=False,assistance='rwkv_independent')
 ids=[e['id'] for e in run['evidence']]
 judgment=dict(schema=r.REVIEW_SCHEMA,contract_sha256=r.digest(contract),run_sha256=r.digest(run),reviewer='Codex external task review; original sources and trace inspected; not a runtime adviser',validity='valid',validity_reason='固定获准用例与只读工作区匹配；真实输入/State及工具结果已核验。输入结构缺陷是被测系统行为，未据此排除失败。',validity_evidence_ids=ids,requirements=[],findings=[],causes=[])
 if row['final'] is not None:
  expected,notes=manual[row['id']];assert hashlib.sha256(row['final'].encode()).hexdigest()==expected
  judgment['requirements']=[dict(id=key,status='met',reason=note,evidence_ids=ids) for key,note in notes.items()]
  if row['id']=='smoke-feedback-r1':
   judgment['findings']=[dict(kind='contradiction',severity='minor',quote='非法输入、缺字段、坏 JSON、未知路由 → 400',reason='README 将未知路由规定为404；原答案随后也写404，造成局部矛盾',impact='附加接口列表的局部状态码错误；核心健康检查用途和不可认证的业务边界仍正确，不整组归零',evidence_ids=ids)]
 judgment['causes']=[dict(category='model_behavior',certainty='observed',reason='按真实原文、调用和终止记录报告行为；不把结果直接当作输入格式缺陷的因果效果',evidence_ids=['E1','E2'])]
 prefix='reviews/'+row['id'];r.write_once(D/(prefix+'.run.json'),run);r.write_once(D/(prefix+'.judgment.json'),judgment)
 assessment=r.assess(contract,run,judgment,evidence_root=p);assessments.append(assessment);r.write_once(D/(prefix+'.assessment.json'),assessment)
 jobs.append(dict(contract='contracts/'+row['file_id']+'.json',run=prefix+'.run.json',judgment=prefix+'.judgment.json',evidence_root='runs/'+row['id']))
r.write_once(D/'BATCH.json',{'reviews':jobs})
r.write_once(D/'TASK_SUMMARY.json',r.aggregate(assessments))
r.write_once(D/'QUALITY_GATE.json',r.quality_gate(assessments,task_ids=['health','smoke','validation','backup'],repeats=2,arm='feedback'))
print(json.dumps(r.aggregate(assessments),ensure_ascii=False))
