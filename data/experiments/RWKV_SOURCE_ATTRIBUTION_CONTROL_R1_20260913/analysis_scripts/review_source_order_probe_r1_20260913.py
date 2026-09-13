from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913/order_probe'
reg=json.loads((D/'REGISTRATION.json').read_text());notes=json.loads((D/'MANUAL_REVIEW_NOTES.json').read_text());assessments=[];jobs=[]
for p in sorted((D/'runs').iterdir()):
 cid,arm,rep=p.name.rsplit('-',2);e=p/'execution';contract=v.load_contract(D/'contracts'/f'{cid}.json')
 run=v.capture_diagnostic_run(e,task_id=cid,arm=arm,repeat=int(rep[1:]),protocol_error_policy='feedback',execution_identity=reg['execution_identity'],historical=False,assistance='rwkv_independent')
 for item in run['evidence']:item['path']=str((e/item['path']).relative_to(D))
 for source in sorted((p/'workspace').rglob('*')):
  if source.is_file():run['evidence'].append(dict(id=f'E{len(run["evidence"])+1}',path=str(source.relative_to(D)),sha256=v.file_digest(source),kind='source'))
 ids=[x['id'] for x in run['evidence']];n=notes[p.name];assert hashlib.sha256(run['answer'].encode()).hexdigest()==n['answer_sha256']
 j=dict(schema=v.REVIEW_SCHEMA,contract_sha256=v.digest(contract),run_sha256=v.digest(run),reviewer='Codex external source and actual tool trace review',validity='valid',validity_reason='冻结任务及原文和完整实际轨迹保留',validity_evidence_ids=ids,requirements=[dict(id=a,status=b,reason=c,evidence_ids=ids) for a,b,c in n['requirements']],findings=[dict(f,evidence_ids=ids) for f in n['findings']],causes=[dict(category='model_behavior',certainty='observed',reason='仅依据实际输出描述事实归属及关系错误，不推断提示或State根因',evidence_ids=ids)])
 prefix='reviews/'+p.name;v.write_once(D/(prefix+'.run.json'),run);v.write_once(D/(prefix+'.judgment.json'),j);a=v.assess(contract,run,j,evidence_root=D);v.write_once(D/(prefix+'.assessment.json'),a);assessments.append(a)
 jobs.append(dict(contract='contracts/'+cid+'.json',run=prefix+'.run.json',judgment=prefix+'.judgment.json',evidence_root='.'))
v.write_once(D/'BATCH.json',dict(reviews=jobs));v.write_once(D/'TASK_SUMMARY.json',v.aggregate(assessments));v.write_once(D/'QUALITY_GATE.json',v.quality_gate(assessments,task_ids=[c['id'] for c in reg['cases']],repeats=2,arm='focused'));print(json.dumps(v.aggregate(assessments),ensure_ascii=False))
