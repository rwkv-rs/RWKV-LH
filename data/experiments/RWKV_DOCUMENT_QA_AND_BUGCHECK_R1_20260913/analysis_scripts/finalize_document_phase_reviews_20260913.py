from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
for phase in ['budget_probe','file_scope_probe','requested_advice_probe','advice_label_probe']:
 P=D/phase;reg=json.loads((P/'REGISTRATION.json').read_text());allnotes={};assessments=[];jobs=[]
 for p in sorted((P/'runs').iterdir()):
  cid,arm,rep=p.name.rsplit('-',2);e=p/'execution';result=json.loads((e/'RESULT.json').read_text());answer=result['final'];req=[];findings=[]
  def finding(kind,severity,quote,reason,impact):
   assert quote in answer
   findings.append(dict(kind=kind,severity=severity,quote=quote,reason=reason,impact=impact))
  contract=v.load_contract(P/'contracts'/f'{cid}.json')
  if answer is not None:
   if cid=='rag_rules':req=[(x['id'],'met','逐字来源、语义决定与原始输出审计均正确；非必要切片细节允许省略') for x in contract['requirements']]
   elif cid=='rag_overview':
    req=[('stack','met','模型、BM25与无embedding正确'),('limits','partial','受控实验边界基本正确，但Writer实验分数错误')]
    quote='300/1000' if '300/1000' in answer else '30/36'
    finding('contradiction','material',quote,'Writer300是候选标签；原文实际17/36，对照zero10/36','改变所询问实验的实际结果')
   elif cid=='api_bug':
    if phase=='budget_probe':req=[('bug','met','未实现文档化业务接口是真实缺陷；不要求只报告--db'),('evidence','met','文件和接口定位、请求触发与无法符合契约的后果明确，给出HTTP请求检查状态字段的可复核方法；未声称运行')]
    else:
     fabricated=rep=='r2' and phase!='advice_label_probe'
     req=[('bug','unmet' if fabricated else 'met','编造已存在的参数校验和数据库写入' if fabricated else '缺失业务接口为真实缺陷'),('evidence','partial','给出检查步骤，但将未执行的验证描述为已运行')]
     line=next(x for x in answer.splitlines() if '已运行验证：' in x)
     finding('false_work_claim','material',line,'本任务及父任务实际工具只有文件读取，没有执行所称HTTP验证','用户无法信赖已执行验证的报告；外部验证不能追认成模型执行')
     if fabricated:finding('unsupported','material','负整数','当前服务没有业务接口、校验或数据库写入实现','缺陷、触发与结果建立在虚构实现上')
     elif phase=='file_scope_probe':finding('contradiction','material','实际 404','实际GET /bookings返回501 not_implemented','错误描述可复现观察')
     elif phase=='requested_advice_probe':finding('contradiction','material','README 契约中的 404','该业务路由文档预期200，404对应未知路由；建议者也误读','混淆契约与实现，无法按错误预期验收')
   elif cid=='backup_check':
    if phase=='budget_probe':
     req=[('behavior','partial','不覆盖结论正确但机制编造'),('proof','unmet','验证对象变成源数据库，未验证已存在目标')]
     finding('unsupported','material','sqlite_backup_{timestamp}.db','源码无该路径模板或先读目标再写新文件逻辑，实际os.link排他创建','回答没有真实代码依据')
    else:
     req=[('behavior','met','正确说明os.link不会覆盖与暂存清理'),('proof','partial' if rep=='r1' else 'met','只建议再次看代码，未给已存在目标的实验步骤' if rep=='r1' else '给出已存在目标内容保持不变的验证方法；不要求完整可直接运行脚本')]
     if '确保文件不存在' in answer:finding('contradiction','minor','确保文件不存在','mkstemp创建唯一暂存文件，并非保持不存在；排他发布核心说明正确','不改变目标文件不覆盖结论')
   allnotes[p.name]=dict(answer_sha256=hashlib.sha256(answer.encode()).hexdigest(),requirements=req,findings=findings)
  assistance='strong_advised' if (e/'PARENT_TRACE.jsonl').exists() else 'rwkv_independent'
  run=v.capture_diagnostic_run(e,task_id=cid,arm=arm,repeat=int(rep[1:]),protocol_error_policy='feedback',execution_identity=reg['execution_identity'],historical=False,assistance=assistance)
  for item in run['evidence']:item['path']=str((e/item['path']).relative_to(D))
  state=json.loads((e/'state_snapshot.json').read_text());workspace=Path(state['goal']['workspace_root'])
  for source in sorted(workspace.rglob('*')):
   if source.is_file():run['evidence'].append(dict(id=f'E{len(run["evidence"])+1}',path=str(source.relative_to(D)),sha256=v.file_digest(source),kind='source'))
  ids=[x['id'] for x in run['evidence']]
  j=dict(schema=v.REVIEW_SCHEMA,contract_sha256=v.digest(contract),run_sha256=v.digest(run),reviewer='Codex external source and actual trace review',validity='valid',validity_reason='冻结任务、实际来源与输入输出齐全；失败保留分母',validity_evidence_ids=ids,requirements=[dict(id=a,status=b,reason=c,evidence_ids=ids) for a,b,c in req],findings=[dict(f,evidence_ids=ids) for f in findings],causes=[dict(category='model_behavior',certainty='observed',reason='描述实际回答及工具记录，不断言提示词或State内部数值是根因',evidence_ids=ids)])
  prefix=f'{phase}/reviews/{p.name}';v.write_once(D/(prefix+'.run.json'),run);v.write_once(D/(prefix+'.judgment.json'),j)
  a=v.assess(contract,run,j,evidence_root=D);v.write_once(D/(prefix+'.assessment.json'),a);assessments.append(a)
  jobs.append(dict(contract=f'{phase}/contracts/{cid}.json',run=prefix+'.run.json',judgment=prefix+'.judgment.json',evidence_root='.'))
 v.write_once(P/'MANUAL_REVIEW_NOTES.json',allnotes);v.write_once(P/'BATCH.json',dict(reviews=jobs));v.write_once(P/'TASK_SUMMARY.json',v.aggregate(assessments))
 v.write_once(P/'QUALITY_GATE.json',v.quality_gate(assessments,task_ids=[x['id'] for x in reg['cases']],repeats=2,arm=arm))
 print(phase,json.dumps(v.aggregate(assessments),ensure_ascii=False))
