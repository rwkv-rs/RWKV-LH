from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913';reg=json.loads((D/'REGISTRATION.json').read_text());notes={};assessments=[];jobs=[]
for p in sorted((D/'runs').iterdir()):
 cid,arm,rep=p.name.rsplit('-',2);e=p/'execution';a=json.loads((e/'RESULT.json').read_text())['final'];findings=[]
 def f(kind,severity,quote,reason,impact):
  assert quote in a;findings.append(dict(kind=kind,severity=severity,quote=quote,reason=reason,impact=impact))
 if cid=='numeric_relation':
  req=[('numbers','met','标签及原分数与对象仍正确；等价百分比不算改写成绩'),('limits','partial','受控边界正确，但第一遍采纳无依据换算禁令，第二遍保留旧比较关系错误')]
  if rep=='r1':f('unsupported','minor','不能将 Reader 结果称为“准确率”并换算百分数','原任务保留原值、不推算未报告成绩，不等于禁止等价百分比；旧契约允许等义表达，不能因建议改变评分','关系错误已删，但增加了原文不支持的解释限制，保留部分满足')
  else:f('contradiction','minor','从约 47.2% 提升到约 47.2%','原文为候选与zero的横向成绩，没有该相同数值间的前后提升','纠正关系未采用；原始成绩仍准确，不与编造分数等同')
 elif cid=='requirements_as_implementation':
  req=[('http','met','健康200、其他GET501及业务未实现均已纠正'),('db','met','必填解析但未使用、无数据库持久化明确'),('sources','met','已读取与无实测分开；结合已列HTTP状态及检查stub/数据库无生成的建议，足以复核核心差距，不要求固定模板或命令')]
  if rep=='r1':f('contradiction','minor','未列实际工具操作','被复制的建议误评原候选；原候选首句已说读取两文件，本次也如实报告','不影响修订的源码核心结论，保留建议复述造成的瑕疵')
  else:f('contradiction','minor','其他路由和参数均未实现','其他业务接口未实现，但host/port解析及使用存在、db也已解析；该概括过宽','核心db未使用与业务缺失正确，末尾泛称参数均未实现仍需收敛')
 else:
  req=[('http','partial','健康200与业务未实现正确，但非health的404错误未改'),('db','met','未使用和无数据库操作仍正确'),('sources','partial','读取与未运行区分且新增验证建议，但来源泛化错误残留，第二遍验证预期也错误')]
  f('contradiction','material','其他路由返回 404','源码其他GET返回501；建议也明确指出了这一点','核心实际HTTP状态码未纠正，第二遍还传播到验证预期')
  f('contradiction','minor','JSON 响应、路由规则等均未在 server.py 中实现','健康和其他GET都有JSON响应，不能将业务缺失泛化为全部JSON缺失','末尾自相矛盾仍保留')
 notes[p.name]=dict(answer_sha256=hashlib.sha256(a.encode()).hexdigest(),requirements=req,findings=findings)
 contract=v.load_contract(D/'contracts'/f'{cid}.json');run=v.capture_diagnostic_run(e,task_id=cid,arm=arm,repeat=int(rep[1:]),protocol_error_policy='feedback',execution_identity=reg['execution_identity'],historical=False,assistance='strong_advised')
 for item in run['evidence']:item['path']=str((e/item['path']).relative_to(R))
 workspace=Path(json.loads((e/'state_snapshot.json').read_text())['goal']['workspace_root'])
 for source in sorted(workspace.rglob('*')):
  if source.is_file():run['evidence'].append(dict(id=f'E{len(run["evidence"])+1}',path=str(source.relative_to(R)),sha256=v.file_digest(source),kind='source'))
 ids=[x['id'] for x in run['evidence']]
 j=dict(schema=v.REVIEW_SCHEMA,contract_sha256=v.digest(contract),run_sha256=v.digest(run),reviewer='Codex external original source, parent and actual continuation review',validity='valid',validity_reason='冻结输入/任务、父State、真实观察与原始答案可复核',validity_evidence_ids=ids,requirements=[dict(id=x,status=y,reason=z,evidence_ids=ids) for x,y,z in req],findings=[dict(x,evidence_ids=ids) for x in findings],causes=[dict(category='model_behavior',certainty='observed',reason='评价实际修订；不以建议正确或提交动作替代任务验收',evidence_ids=ids)])
 prefix='reviews/'+p.name;v.write_once(D/(prefix+'.run.json'),run);v.write_once(D/(prefix+'.judgment.json'),j);assessment=v.assess(contract,run,j,evidence_root=R);v.write_once(D/(prefix+'.assessment.json'),assessment);assessments.append(assessment)
 jobs.append(dict(contract='contracts/'+cid+'.json',run=prefix+'.run.json',judgment=prefix+'.judgment.json',evidence_root='../../..'))
v.write_once(D/'MANUAL_REVIEW_NOTES.json',notes);v.write_once(D/'BATCH.json',dict(reviews=jobs));v.write_once(D/'TASK_SUMMARY.json',v.aggregate(assessments));v.write_once(D/'QUALITY_GATE.json',v.quality_gate(assessments,task_ids=[x['id'] for x in reg['cases']],repeats=2,arm='advised'));print(json.dumps(v.aggregate(assessments),ensure_ascii=False))
