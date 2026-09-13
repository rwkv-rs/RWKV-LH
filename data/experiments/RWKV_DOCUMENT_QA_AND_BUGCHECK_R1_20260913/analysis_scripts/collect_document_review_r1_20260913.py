from pathlib import Path
import json,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
reg=json.loads((D/'REGISTRATION.json').read_text())
notes=json.loads((D/'MANUAL_REVIEW_NOTES.json').read_text());assessments=[];jobs=[]
for p in sorted((D/'runs').iterdir()):
    cid,arm,rep=p.name.rsplit('-',2);repeat=int(rep[1:]);e=p/'execution'
    contract=v.load_contract(D/'contracts'/f'{cid}.json')
    run=v.capture_diagnostic_run(e,task_id=cid,arm=arm,repeat=repeat,protocol_error_policy='feedback',execution_identity=reg['execution_identity'],historical=False,assistance='rwkv_independent')
    for item in run['evidence']:item['path']=str((e/item['path']).relative_to(D))
    for source in sorted((p/'workspace').rglob('*')):
        if source.is_file():run['evidence'].append({'id':f'E{len(run["evidence"])+1}','path':str(source.relative_to(D)),'sha256':v.file_digest(source),'kind':'source'})
    ids=[x['id'] for x in run['evidence']]
    j=dict(schema=v.REVIEW_SCHEMA,contract_sha256=v.digest(contract),run_sha256=v.digest(run),reviewer='Codex external original-source and trace review; no runtime answer assistance',validity='valid',validity_reason='冻结任务、原文及实际调用保留；系统或模型失败不排除分母',validity_evidence_ids=ids,requirements=[],findings=[],causes=[])
    if run['answer'] is not None:
        n=notes[p.name];import hashlib
        assert hashlib.sha256(run['answer'].encode()).hexdigest()==n['answer_sha256']
        j['requirements']=[dict(id=rid,status=status,reason=reason,evidence_ids=ids) for rid,status,reason in n['requirements']]
        j['findings']=[dict(f,evidence_ids=ids) for f in n.get('findings',[])]
    j['causes']=[dict(category='model_behavior',certainty='observed',reason='按实际输出与终止记录描述，不推断输入复杂度的因果效果',evidence_ids=ids)]
    prefix='reviews/'+p.name;v.write_once(D/(prefix+'.run.json'),run);v.write_once(D/(prefix+'.judgment.json'),j)
    a=v.assess(contract,run,j,evidence_root=D);v.write_once(D/(prefix+'.assessment.json'),a);assessments.append(a)
    jobs.append(dict(contract='contracts/'+cid+'.json',run=prefix+'.run.json',judgment=prefix+'.judgment.json',evidence_root='.'))
v.write_once(D/'BATCH.json',{'reviews':jobs});v.write_once(D/'TASK_SUMMARY.json',v.aggregate(assessments))
for arm in ('serial','parallel'):v.write_once(D/f'QUALITY_GATE_{arm}.json',v.quality_gate(assessments,task_ids=[x['id'] for x in reg['cases']],repeats=2,arm=arm))
print(json.dumps(v.aggregate(assessments),ensure_ascii=False))
